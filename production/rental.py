"""Guard caller-created disposable Runpod resources. Never creates or rents a pod.

Receipts are trusted local controller inputs, not grants from an HTTP user.
An independently supervised guard is required before a real rental. This module
does not make the provider bill a hard cap, or survive loss of the host/network.
"""
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

from .core import ProductionError, number, read_json, write_json


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RunpodControl:
    """Small v2 control adapter: only read/delete one explicitly recorded resource."""
    def __init__(self, token):
        if not isinstance(token,str) or not token.strip():
            raise ProductionError('Runpod control credential is not configured')
        self.token=token
        self.opener=urllib.request.build_opener(NoRedirect())
        self.base_url='https://api.runpod.io/v2'
        self.simulation=False

    def request(self, method, pod_id, runtime):
        if not re.fullmatch(r'[A-Za-z0-9_-]{3,80}',pod_id):
            raise ProductionError('Invalid Runpod resource ID')
        runtime.check()
        request=urllib.request.Request(self.base_url+'/pods/'+pod_id,
            method=method,headers={'Authorization':'Bearer '+self.token,'Accept':'application/json'})
        try:
            with self.opener.open(request,timeout=max(.1,min(10,runtime.deadline-time.monotonic()))) as response:
                chunks=[];size=0
                while True:
                    runtime.check()
                    # read1 returns after one underlying read, so a trickling peer
                    # cannot hold read(N) past the operation deadline indefinitely.
                    chunk=response.read1(min(65536,1024*1024+1-size))
                    if not chunk:break
                    chunks.append(chunk);size+=len(chunk)
                    if size>1024*1024:raise ProductionError('Oversized control response')
                runtime.check()
                raw=b''.join(chunks)
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            if exc.code==404:return None
            raise ProductionError('Runpod control request failed: HTTP '+str(exc.code)) from None
        except (OSError,ValueError):
            raise ProductionError('Runpod control request failed; details withheld') from None

    def get(self, pod_id, runtime):return self.request('GET',pod_id,runtime)
    def terminate(self, pod_id, runtime):return self.request('DELETE',pod_id,runtime)


def validate_lease(lease):
    if lease.get('schema_version')!=1 or lease.get('provider')!='runpod':
        raise ProductionError('Unsupported rental receipt')
    if lease.get('termination_authorized') is not True:
        raise ProductionError('Termination was not authorized for this disposable resource')
    if number(lease.get('budget_usd'),'budget',0)==0:
        raise ProductionError('No rental is allowed at zero budget')
    for key in ('created_at_epoch','terminate_at_epoch'):
        number(lease.get(key),key,1)
    if not 1<=lease['terminate_at_epoch']-lease['created_at_epoch']<=86400:
        raise ProductionError('Rental deadline must be 1 second to 24 hours from creation')
    number(lease.get('hourly_total_usd'),'total hourly price',0)
    number(lease.get('fixed_cost_usd'),'fixed cost',0)
    reserve=number(lease.get('cleanup_allowance_seconds'),'cleanup allowance',10,300)
    estimate=(lease['terminate_at_epoch']-lease['created_at_epoch']+reserve)*lease['hourly_total_usd']/3600+lease['fixed_cost_usd']
    if estimate>lease['budget_usd']:
        raise ProductionError('Declared lifetime including overhead exceeds budget')
    binding=lease.get('resource',{})
    if not re.fullmatch(r'[A-Za-z0-9_-]{3,80}',binding.get('id','')):
        raise ProductionError('Invalid bound resource ID')
    if not re.fullmatch(r'zina-video-[a-f0-9]{32}',binding.get('name','')):
        raise ProductionError('Guard accepts only uniquely named production pilot resources')
    if not isinstance(binding.get('createdAt'),str) or not binding['createdAt']:
        raise ProductionError('Provider creation timestamp is required for ownership binding')
    # These fields must be copied from the successful provider create response.
    from datetime import datetime
    try:created=datetime.fromisoformat(binding['createdAt'].replace('Z','+00:00'))
    except ValueError:raise ProductionError('Invalid provider timestamp') from None
    if created.tzinfo is None or abs(created.timestamp()-lease['created_at_epoch'])>.001:
        raise ProductionError('Deadline is not based on provider creation time')
    if lease.get('shared_resource') is not False:
        raise ProductionError('Shared resources cannot be terminated by a pilot guard')


def enforce(lease, control, receipt_path: Path, runtime, *, execute_authorized=False,
            force_due=False, now=None, retry_interval=1):
    """One bounded cleanup operation; completion requires a GET returning 404.

    Duplicate DELETE is safe only after a fresh matching ownership read. Unknown
    outcomes remain visible. No other pod or persistent volume is touched.
    """
    validate_lease(lease)
    if execute_authorized is not True:
        raise ProductionError('Explicit execution authorization is required')
    number(retry_interval,'retry interval',.01,10)
    now=time.time() if now is None else number(now,'current time',1)
    if now<lease['terminate_at_epoch'] and not force_due:
        return {'status':'waiting','terminate_at_epoch':lease['terminate_at_epoch']}
    from .core import object_digest
    binding=lease['resource'];lease_hash=object_digest(lease)
    # Caller holds the controller's own lease lock; only this resource is in scope.
    if receipt_path.exists():
        previous=read_json(receipt_path)
        if previous.get('lease_sha256')!=lease_hash:
            raise ProductionError('Cleanup receipt belongs to a different rental')
    result={'lease_sha256':lease_hash,'pod_id':binding['id'],'status':'cleanup_pending',
            'provider_absence_confirmed':False,'delete_attempts':0}
    write_json(receipt_path,result)
    try:
        for _ in range(5):
            runtime.check()
            pod=control.get(binding['id'],runtime)
            if pod is None:
                result.update(status='terminated_confirmed',provider_absence_confirmed=True)
                write_json(receipt_path,result);return result
            if any(pod.get(key)!=binding[key] for key in ('id','name','createdAt')) or pod.get('cluster'):
                result.update(status='ownership_mismatch')
                write_json(receipt_path,result)
                raise ProductionError('Ownership mismatch; no termination request sent')
            result['delete_attempts']+=1
            write_json(receipt_path,result)  # Durable intent before the billable-resource mutation.
            try:
                control.terminate(binding['id'],runtime)
            except ProductionError:
                # Lost DELETE replies are reconciled by GET, never by assuming success.
                pass
            until=time.monotonic()+retry_interval
            while time.monotonic()<until:
                runtime.check();time.sleep(min(.05,max(0,until-time.monotonic())))
        pod=control.get(binding['id'],runtime)
        if pod is None:
            result.update(status='terminated_confirmed',provider_absence_confirmed=True)
            write_json(receipt_path,result);return result
        raise ProductionError('Provider has not confirmed resource termination')
    except BaseException as exc:
        if result['status']!='ownership_mismatch':result['status']='cleanup_unconfirmed'
        result['error_type']=type(exc).__name__
        write_json(receipt_path,result)
        raise
