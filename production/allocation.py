"""Single-attempt allocation journal. Unknown POST outcomes never cause a repeat.

The pre-armed watcher owns reconciliation and cleanup independently of the caller.
No queues, persistent volumes, public web ports or automatic hardware fallback.
"""
import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.request
from urllib.parse import urlencode

from .core import ProductionError, Runtime, number, object_digest, read_json, write_json
from .rental import RunpodControl, validate_lease, enforce
from .rental_guard import private_token, start_token, watch, guard_status


def validate_intent(intent):
    if intent.get('schema_version')!=1 or intent.get('approved') is not True:
        raise ProductionError('Explicit allocation authorization required')
    body=intent['body']
    allowed={'name','image','gpu','cpu','disk','cloud','dataCenterIds','startSsh','startJupyter','ports','env','cmd'}
    if set(body)-allowed or not re.fullmatch(r'zina-video-[a-f0-9]{32}',body.get('name','')):
        raise ProductionError('Unsupported allocation fields or resource name')
    if not re.fullmatch(r'[^\s]+@sha256:[a-f0-9]{64}',body.get('image','')):
        raise ProductionError('Pinned container digest required')
    if ('gpu' in body)==('cpu' in body):raise ProductionError('Exactly one compute type required')
    if 'gpu' in body and body['gpu'].get('count')!=1:raise ProductionError('One GPU per trial')
    if body.get('ports',[]) not in ([],['22/tcp']) or body.get('startJupyter',False):
        raise ProductionError('Only SSH may be exposed by this allocator')
    if set(body.get('env',{}))-{'PUBLIC_KEY'}:raise ProductionError('Only an SSH public key may enter allocation metadata')
    if 'cmd' in body and body['cmd']!=['sleep','300']:raise ProductionError('Unsupported probe command')
    number(body.get('disk'),'temporary disk',1,150)
    number(intent['budget_usd'],'allocation budget',.001,50)
    number(intent['hourly_total_usd'],'total hourly bound',.001,20)
    number(intent['created_at_epoch'],'intent time',1)
    duration=intent['terminate_at_epoch']-intent['created_at_epoch']
    number(duration,'original allocation lifetime',30,3600)
    if (duration+120)*intent['hourly_total_usd']/3600>intent['budget_usd']:
        raise ProductionError('Allocation lifetime and cleanup exceed budget')


class AllocationControl(RunpodControl):
    def collection(self,method,runtime,body=None,cursor=None):
        suffix='/pods'+('?' + urlencode({'cursor':cursor}) if cursor else '')
        request=urllib.request.Request(self.base_url+suffix,method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json','Accept':'application/json'})
        runtime.check()
        try:
            with self.opener.open(request,timeout=min(10,max(.1,runtime.deadline-time.monotonic()))) as response:
                raw=b''
                while True:
                    runtime.check();chunk=response.read1(min(65536,4*1024*1024+1-len(raw)))
                    if not chunk:break
                    raw+=chunk
                    if len(raw)>4*1024*1024:raise ProductionError('Oversized allocation response')
                if method=='POST' and response.status!=201:
                    raise ProductionError('Unexpected allocation outcome; reconcile without retry')
                return json.loads(raw)
        except (OSError,ValueError):
            raise ProductionError('Allocation response unavailable; reconcile without retry') from None

    def create(self,body,runtime):return self.collection('POST',runtime,body)
    def matching(self,name,runtime):
        found=[];cursor=None;seen=set()
        for _ in range(20):
            result=self.collection('GET',runtime,cursor=cursor)
            found.extend(p for p in result['pods'] if p.get('name')==name)
            page=result['pagination']
            if not page['hasNextPage']:return found
            cursor=page['nextCursor']
            if not cursor or cursor in seen:raise ProductionError('Invalid allocation pagination')
            seen.add(cursor)
        raise ProductionError('Allocation pagination bound reached')


def bind_lease(intent,pod):
    validate_intent(intent)
    if pod.get('name')!=intent['body']['name'] or pod.get('cluster'):
        raise ProductionError('Allocation ownership mismatch')
    created=datetime.fromisoformat(pod['createdAt'].replace('Z','+00:00')).timestamp()
    if created<intent['created_at_epoch']-1:
        raise ProductionError('Resource predates allocation intent')
    # Use the original absolute deadline. A late response never renews it.
    lease={'schema_version':1,'provider':'runpod','resource':{k:pod[k] for k in ('id','name','createdAt')},
        'created_at_epoch':created,'terminate_at_epoch':max(created+1,intent['terminate_at_epoch']),
        'budget_usd':intent['budget_usd'],'hourly_total_usd':intent['hourly_total_usd'],
        'fixed_cost_usd':0,'cleanup_allowance_seconds':120,'termination_authorized':True,'shared_resource':False}
    validate_lease(lease)
    return lease


def watcher_ready(root,intent):
    try:r=read_json(root/'allocation-guard.json')
    except OSError:return False
    return (r.get('intent_sha256')==object_digest(intent) and r.get('phase')=='armed' and
        0<=time.time()-r.get('heartbeat_at',0)<5 and r.get('process_start') is not None and
        start_token(r.get('pid'))==r.get('process_start'))


def allocate_once(root,control):
    root=Path(root);intent=read_json(root/'allocation.json');validate_intent(intent)
    with (root/'allocation.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ProductionError('Allocation caller already active') from None
        marker=root/'create-intent.json'
        if marker.exists():
            if read_json(marker)['intent_sha256']!=object_digest(intent):raise ProductionError('Allocation intent changed')
            return {'status':'reconciliation_required','create_repeated':False}
        if (root/'allocation-cancel').exists():raise ProductionError('Allocation was cancelled')
        if time.time()>=intent['terminate_at_epoch']-15:raise ProductionError('Allocation deadline exhausted')
        if not watcher_ready(root,intent):raise ProductionError('Pre-armed independent allocation watcher required')
        # Commit once before the network call. Even a process crash here must not
        # cause a second POST; conservative unresolved is safer than double rent.
        write_json(marker,{'intent_sha256':object_digest(intent),'at_epoch':time.time()})
        try:
            pod=control.create(intent['body'],Runtime(15))
            write_json(root/'provider-create.json',pod)
            return {'status':'created_pending_guard','pod_id':pod['id'],'create_repeated':False}
        except BaseException as exc:
            write_json(root/'create-unknown.json',{'error_type':type(exc).__name__,'intent_sha256':object_digest(intent)})
            raise


def watch_allocation(root,control):
    root=Path(root);intent=read_json(root/'allocation.json');validate_intent(intent)
    with (root/'allocation-watch.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ProductionError('Allocation watcher already active') from None
        if (root/'lease.json').exists():
            if (root/'allocation-cancel').exists():
                return enforce(read_json(root/'lease.json'),control,root/'allocation-rejected-cleanup.json',
                    Runtime(120),execute_authorized=True,force_due=True)
            return watch(root/'lease.json',root,control,cancel_file=root/'allocation-cancel')
        control.matching(intent['body']['name'],Runtime(15))  # Verify read access before arming.
        status={'intent_sha256':object_digest(intent),'pid':os.getpid(),'process_start':start_token(os.getpid()),
            'phase':'armed','heartbeat_at':time.time()}
        until=time.monotonic()+max(1,intent['terminate_at_epoch']-time.time())+120
        while time.monotonic()<until:
            if object_digest(read_json(root/'allocation.json'))!=status['intent_sha256']:
                status['phase']='intent_changed' # Keep reconciling original ownership, prohibit POST.
            status['heartbeat_at']=time.time();write_json(root/'allocation-guard.json',status)
            try:
                matches=control.matching(intent['body']['name'],Runtime(15))
                if len(matches)>1:raise ProductionError('Duplicate resources require explicit reconciliation')
                if matches:
                    pod=matches[0];lease=bind_lease(intent,pod)
                    write_json(root/'lease.json',lease)
                    status.update(phase='bound',pod_id=pod['id']);write_json(root/'allocation-guard.json',status)
                    # Over-price allocation is torn down immediately. Guard uses
                    # original signed ownership; no new resource can be selected.
                    cancel=root/'allocation-cancel'
                    wrong=(pod.get('image')!=intent['body']['image'] or
                           any(pod.get(key,{}).get('id')!=intent['body'][key]['id'] for key in ('cpu','gpu') if key in intent['body']) or
                           pod.get('dataCenterId') not in intent['body'].get('dataCenterIds',[pod.get('dataCenterId')]))
                    try:overpriced=number(pod.get('cost'),'provider hourly cost',0)>intent['hourly_total_usd']
                    except ProductionError:overpriced=True
                    if wrong or overpriced:
                        cancel.touch()
                        return enforce(lease,control,root/'allocation-rejected-cleanup.json',Runtime(120),
                            execute_authorized=True,force_due=True)
                    return watch(root/'lease.json',root,control,cancel_file=cancel)
            except ProductionError as exc:
                write_json(root/'allocation-reconcile-error.json',{'error_type':type(exc).__name__,'at_epoch':time.time()})
            time.sleep(1)
        status.update(phase='unresolved' if (root/'create-intent.json').exists() else 'expired_without_submission',
            heartbeat_at=time.time())
        write_json(root/'allocation-guard.json',status)
        return status


def wait_allocated(root,*,timeout=30):
    """Wait for the original resource; never creates or renews a rental."""
    root=Path(root);intent=read_json(root/'allocation.json');validate_intent(intent)
    runtime=Runtime(timeout)
    while True:
        runtime.check()
        if (root/'allocation-cancel').exists():raise ProductionError('Allocated resource rejected')
        if (root/'lease.json').exists():
            lease=read_json(root/'lease.json')
            if guard_status(root,lease)['ready']:
                if time.time()>=intent['terminate_at_epoch']:raise ProductionError('Original allocation expired')
                return lease
        if (root/'allocation-guard.json').exists():
            status=read_json(root/'allocation-guard.json')
            if status.get('phase') in {'unresolved','expired_without_submission','intent_changed'}:
                raise ProductionError('Allocation needs reconciliation; no repeat permitted')
        time.sleep(.1)


def launch_allocation(root,credential,python):
    import subprocess
    import math
    root=Path(root).resolve();intent=read_json(root/'allocation.json');validate_intent(intent)
    private_token(credential)
    remaining=intent['terminate_at_epoch']-time.time()
    if remaining<20:raise ProductionError('Allocation lifetime already exhausted')
    unit='zina-allocation-'+intent['body']['name'][11:]
    args=['systemd-run','--unit='+unit,'--collect','--property=Type=simple',
        '--property=Restart=on-failure','--property=RestartSec=1','--property=StartLimitBurst=3',
        '--property=StartLimitIntervalSec=3600','--property=RuntimeMaxSec='+str(math.ceil(remaining+150)),
        '--property=TimeoutStopSec=122','--property=WorkingDirectory='+str(Path(__file__).resolve().parents[1]),
        str(python),'-m','production.allocation','watch','--root',str(root),
        '--credential-file',str(Path(credential).resolve())]
    r=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    if r.returncode:raise ProductionError('Allocation supervisor launch failed')
    return {'unit':unit+'.service','ready':False}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['watch','create'])
    p.add_argument('--root',type=Path,required=True);p.add_argument('--credential-file',type=Path,required=True)
    a=p.parse_args();control=AllocationControl(private_token(a.credential_file))
    result=watch_allocation(a.root,control) if a.command=='watch' else allocate_once(a.root,control)
    print(json.dumps(result))
