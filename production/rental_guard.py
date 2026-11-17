"""Finite independent lease monitor. No resource creation or generation.

The controller must observe a live ready receipt before using its rented pod.
This process survives its launching controller, but not host loss or SIGKILL.
Restart uses the original lease deadline; it cannot extend a rental.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import stat
import sys
import time
from urllib.parse import urlparse

from .core import ProductionError, Runtime, object_digest, read_json, write_json
from .rental import RunpodControl, enforce, validate_lease


def private_token(path=None):
    if path is None:
        value=os.environ.get('PRODUCTION_RUNPOD_API_KEY') or os.environ.get('RUNPOD_API_KEY')
    else:
        path=Path(path)
        if path.is_symlink():raise ProductionError('Credential cannot be a symlink')
        info=path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid()
                or stat.S_IMODE(info.st_mode)&0o077 or info.st_size>4096):
            raise ProductionError('Credential file must be owner-only and at most 4096 bytes')
        value=path.read_text().strip()
    if not value or any(c.isspace() for c in value):
        raise ProductionError('Runpod control credential is not configured correctly')
    return value


class SimulationControl(RunpodControl):
    def __init__(self,url):
        parsed=urlparse(url)
        if (parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','::1'}
                or not parsed.port or parsed.username or parsed.password or parsed.query
                or parsed.fragment or parsed.path not in {'','/v2'}):
            raise ProductionError('Simulation accepts only a loopback HTTP fixture')
        super().__init__('fixture-no-real-credential')
        self.base_url=url.rstrip('/')
        self.simulation=True


def start_token(pid):
    try:
        text=Path('/proc',str(pid),'stat').read_text()
        parts=text[text.rfind(')')+2:].split()
        if parts[0]=='Z':return None
        return parts[19]
    except (OSError,IndexError):return None


def guard_status(root,lease,*,max_heartbeat_age=5):
    """Fail closed on stale receipt, PID reuse, simulation or a changed grant."""
    validate_lease(lease)
    path=Path(root)/lease['resource']['id']/'guard.json'
    if not path.is_file():return {'ready':False,'reason':'guard_missing'}
    r=read_json(path)
    ready=(r.get('lease_sha256')==object_digest(lease) and r.get('phase')=='watching'
           and r.get('simulation') is False and r.get('provider_verified') is True
           and 0<=time.time()-r.get('heartbeat_at',0)<=max_heartbeat_age
           and start_token(r.get('pid'))==r.get('process_start') and r.get('process_start') is not None
           and time.time()<lease['terminate_at_epoch'])
    return {'ready':bool(ready),'reason':'live_guard' if ready else 'guard_not_live_or_not_qualified',
            'status':r}


def watch(lease_path,root,control,*,cancel_file=None,heartbeat_seconds=1):
    lease=read_json(lease_path);validate_lease(lease)
    lease_hash=object_digest(lease)
    root=Path(root).resolve();folder=root/lease['resource']['id']
    if folder.is_symlink():raise ProductionError('Guard state cannot be a symlink')
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    for name in ('guard.lock','guard.json','cleanup.json'):
        if (folder/name).is_symlink():raise ProductionError('Guard state cannot be a symlink')
    with (folder/'guard.lock').open('a') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ProductionError('A guard already owns this resource') from None
        status_path=folder/'guard.json'
        if status_path.exists() and read_json(status_path).get('lease_sha256')!=lease_hash:
            raise ProductionError('Guard restart cannot change the original rental grant')
        status={'schema_version':1,'lease_sha256':lease_hash,'pod_id':lease['resource']['id'],
                'pid':os.getpid(),'process_start':start_token(os.getpid()),
                'simulation':control.simulation,'provider_verified':False,
                'phase':'starting','heartbeat_at':time.time(),
                'terminate_at_epoch':lease['terminate_at_epoch']}
        write_json(status_path,status)
        stop={'requested':False,'reason':'deadline'}
        def request_stop(*_):stop.update(requested=True,reason='signal')
        previous={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
        cleanup=None;cleanup_started=False
        try:
            for sig in previous:signal.signal(sig,request_stop)
            pod=control.get(lease['resource']['id'],Runtime(15))
            if pod is not None and (any(pod.get(k)!=lease['resource'][k] for k in ('id','name','createdAt')) or pod.get('cluster')):
                status.update(phase='ownership_mismatch')
                raise ProductionError('Guard ownership check failed')
            # Both clocks bound the run: a backwards wall-clock adjustment cannot extend it.
            remaining=max(0,min(86400,lease['terminate_at_epoch']-time.time()))
            monotonic_end=time.monotonic()+remaining
            status.update(phase='watching',provider_verified=pod is not None)
            write_json(status_path,status)
            next_beat=0
            while pod is not None and time.time()<lease['terminate_at_epoch'] and time.monotonic()<monotonic_end:
                if stop['requested']:break
                if cancel_file and Path(cancel_file).exists():stop['reason']='cancel_file';break
                if object_digest(read_json(lease_path))!=lease_hash:
                    stop['reason']='lease_changed';break
                if time.monotonic()>=next_beat:
                    status['heartbeat_at']=time.time();write_json(status_path,status)
                    next_beat=time.monotonic()+heartbeat_seconds
                time.sleep(.1)
            status.update(phase='cleaning',stop_reason=stop['reason'],heartbeat_at=time.time())
            write_json(status_path,status)
            cleanup_started=True
            cleanup=enforce(lease,control,folder/'cleanup.json',
                Runtime(lease['cleanup_allowance_seconds']),execute_authorized=True,force_due=True)
            status.update(phase='finished',cleanup_status=cleanup['status'])
            return cleanup
        except BaseException as exc:
            if status['phase']!='ownership_mismatch':
                status.update(phase='failed',error_type=type(exc).__name__)
                # Use the originally validated grant even if its source file is
                # subsequently removed or corrupted. Never extend that grant.
                if not cleanup_started:
                    try:
                        cleanup=enforce(lease,control,folder/'cleanup.json',
                            Runtime(lease['cleanup_allowance_seconds']),
                            execute_authorized=True,force_due=True)
                        status['cleanup_status']=cleanup['status']
                    except BaseException as cleanup_exc:
                        status.update(cleanup_status='cleanup_unconfirmed',
                                      cleanup_error_type=type(cleanup_exc).__name__)
            raise
        finally:
            status.update(heartbeat_at=time.time(),provider_verified=False)
            write_json(status_path,status)
            for sig,old in previous.items():signal.signal(sig,old)
            fcntl.flock(handle,fcntl.LOCK_UN)


def launch(lease_path,root,python,*,credential_file=None,simulation_url=None,supervisor='process'):
    """Detach a finite guard without a shell; caller must check its ready receipt."""
    import subprocess
    lease_path=Path(lease_path).resolve();root=Path(root).resolve()
    lease=read_json(lease_path);validate_lease(lease)
    if not simulation_url:private_token(credential_file)
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    args=[str(python),'-m','production.rental_guard','watch','--lease',str(lease_path),'--root',str(root)]
    if credential_file:args+=['--credential-file',str(Path(credential_file).resolve())]
    if simulation_url:args+=['--simulation-control-url',simulation_url]
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','PRODUCTION_RUNPOD_API_KEY','RUNPOD_API_KEY'}}
    if simulation_url:
        env.pop('RUNPOD_API_KEY',None);env.pop('PRODUCTION_RUNPOD_API_KEY',None)
    if supervisor=='systemd':
        import math
        if not simulation_url and credential_file is None:
            raise ProductionError('Systemd guard requires a private credential file')
        unit='zina-video-guard-'+lease['resource']['id']
        lifetime=math.ceil(max(1,lease['terminate_at_epoch']-time.time())+lease['cleanup_allowance_seconds']+20)
        # Only a new transient, isolated unit; never edit an existing/shared unit.
        command=['systemd-run','--unit='+unit,'--collect','--property=Type=simple',
            '--property=Restart=on-failure','--property=RestartSec=1',
            '--property=StartLimitBurst=3','--property=StartLimitIntervalSec=3600',
            '--property=RuntimeMaxSec='+str(lifetime),
            '--property=TimeoutStopSec='+str(lease['cleanup_allowance_seconds']+2),
            '--property=WorkingDirectory='+str(Path(__file__).resolve().parents[1]),*args]
        result=subprocess.run(command,env={k:v for k,v in env.items() if k in {'PATH','HOME','LANG'}},
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
        if result.returncode:raise ProductionError('Isolated guard supervisor launch failed')
        return {'unit':unit+'.service','lease_sha256':object_digest(lease),'ready':False,
                'note':'Supervisor launch is not readiness; require guard_status.'}
    if supervisor!='process':raise ProductionError('Unknown guard supervisor')
    with (root/(lease['resource']['id']+'.log')).open('a') as log:
        child=subprocess.Popen(args,cwd=Path(__file__).resolve().parents[1],env=env,
            stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
    return {'pid':child.pid,'process_start':start_token(child.pid),'lease_sha256':object_digest(lease),
            'ready':False,'note':'Launch is not readiness; require guard_status before using the rental.'}


def main():
    parser=argparse.ArgumentParser(description='Finite rental guard; never creates resources')
    parser.add_argument('command',choices=['watch','launch','status'])
    parser.add_argument('--lease',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--credential-file',type=Path)
    parser.add_argument('--simulation-control-url')
    parser.add_argument('--cancel-file',type=Path)
    parser.add_argument('--supervisor',choices=['process','systemd'],default='process')
    args=parser.parse_args()
    try:
        if args.command=='status':result=guard_status(args.root,read_json(args.lease))
        elif args.command=='launch':
            result=launch(args.lease,args.root,Path(sys.executable),credential_file=args.credential_file,
                          simulation_url=args.simulation_control_url,supervisor=args.supervisor)
        else:
            control=(SimulationControl(args.simulation_control_url) if args.simulation_control_url
                     else RunpodControl(private_token(args.credential_file)))
            result=watch(args.lease,args.root,control,cancel_file=args.cancel_file)
        print(json.dumps(result));return 0
    except (ProductionError,OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'guard_failed','error_type':type(exc).__name__}));return 2


if __name__=='__main__':sys.exit(main())
