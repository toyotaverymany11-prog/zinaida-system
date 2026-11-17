"""Finite operator-run qualification on an already leased, guarded exclusive Pod.

No cloud creation, public listener, account token export or shared-service edits.
The existing protected controller remains the independent cleanup backstop.
"""
import argparse
import io
import json
from pathlib import Path
import socket
import subprocess
import tarfile
import time

from production.core import Runtime, ProductionError, read_json, write_json, object_digest
from production.rental import RunpodControl, enforce
from production.rental_guard import private_token, guard_status
from production.shots import execute_shot, image_file, check_current, load_request


def transfer_budget(terminate_at_epoch, now):
    seconds=min(1500,int(terminate_at_epoch-now)-720)
    if seconds < 60:
        raise ProductionError('Insufficient original lease time for transfer')
    return seconds


def run(root, bundle, intake, request_file, credential, ssh_key):
    root=root.resolve();lease=read_json(root/'lease.json');request=read_json(request_file)
    control=RunpodControl(private_token(credential));runtime=Runtime(2100)
    children=[];logs=[]
    def command(args, **kwargs):
        runtime.check()
        return subprocess.run(args,check=True,timeout=min(55,runtime.deadline-time.monotonic()),**kwargs)
    def start(args, log):
        stream=(root/log).open('w');logs.append(stream)
        p=subprocess.Popen(args,stdout=stream,stderr=stream,stdin=subprocess.DEVNULL,start_new_session=True)
        children.append(p);return p
    try:
        canonical = load_request(intake, request['order_id'], request['request_id'])
        if canonical != request:
            raise ProductionError('Runner request differs from canonical prepared shot')
        check_current(intake, request['order_id'], request, runtime)
        if not guard_status(root,lease)['ready']:raise ProductionError('Independent guard not ready')
        ready_deadline=time.monotonic()+180
        while time.monotonic()<ready_deadline:
            pod=control.get(lease['resource']['id'],runtime)
            direct=(pod or {}).get('ssh',{}).get('direct')
            if direct:break
            time.sleep(2)
        else:raise ProductionError('SSH allocation deadline')
        write_json(root/'provider-ready.json',pod)
        opts=['-i',str(ssh_key),'-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=accept-new',
              '-o','UserKnownHostsFile='+str(root/'known_hosts'),'-o','ConnectTimeout=10',
              '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3']
        ssh=['ssh',*opts,'-p',str(direct['port']),direct['username']+'@'+direct['host']]
        write_json(root/'ssh-args.json',ssh)
        command(ssh+['echo connected'])
        package=io.BytesIO()
        with tarfile.open(fileobj=package,mode='w:gz') as archive:
            for name in ('comfy.tar.gz','worker.tar.gz','comfy-constraints.txt','gpu_bootstrap_probe.py'):
                archive.add(bundle/name,arcname=name)
            archive.add(root/'scoped_model_download.py',arcname='scoped_model_download.py')
        command(ssh+['tar -xzf - -C /workspace'],input=package.getvalue())
        bootstrap=start(['timeout','650',*ssh,'python3 /workspace/gpu_bootstrap_probe.py --root /workspace --timeout 600'],'bootstrap.log')
        while bootstrap.poll() is None:runtime.check();time.sleep(1)
        if bootstrap.returncode:raise ProductionError('GPU bootstrap failed')
        if request['recipe'] == 'ltx25-i2v':
            path = image_file(intake, request['order_id'], request, runtime)
            name = request['input_image']['filename']
            command(ssh+['mkdir -p /workspace/comfy/input; cat > /workspace/comfy/input/'+name],
                    input=path.read_bytes())
            check = command(ssh+['sha256sum /workspace/comfy/input/'+name], capture_output=True)
            if check.stdout.decode().split()[0] != request['input_image']['sha256']:
                raise ProductionError('GPU input image transfer SHA mismatch')
            write_json(root/'input-image-transfer.json', request['input_image'])
        config=root/'download-locations.private.json'
        command(ssh+['umask 077; cat > /workspace/download-locations.private.json'],input=config.read_bytes())
        config.unlink()
        # Preserve inference and cleanup time from the original lease. Never
        # reuse an unrelated fixed transfer limit or extend the provider lease.
        transfer_seconds=transfer_budget(lease['terminate_at_epoch'],time.time())
        write_json(root/'transfer-budget.json',{'seconds':transfer_seconds,'inference_and_cleanup_reserve':720})
        download=start(['timeout',str(transfer_seconds+30),*ssh,
            'python3 /workspace/scoped_model_download.py --timeout '+str(transfer_seconds)],'model-download.log')
        while download.poll() is None:runtime.check();time.sleep(1)
        # Preserve small diagnostics before execution deletes the rental.
        for filename in ('gpu-runtime-report.json','model-download-report.json','transfer-preflight.json'):
            result=command(ssh+['cat /workspace/'+filename],capture_output=True)
            write_json(root/filename,json.loads(result.stdout))
        if download.returncode or read_json(root/'model-download-report.json')['status']!='verified':
            raise ProductionError('Model transfer qualification failed')
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        tunnel=start(['timeout','900',*ssh[:-1],'-o','ExitOnForwardFailure=yes','-L',f'127.0.0.1:{port}:127.0.0.1:8188','-N',ssh[-1]],'tunnel.log')
        import urllib.request
        for _ in range(30):
            if tunnel.poll() is not None:raise ProductionError('Tunnel exited')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/system_stats',timeout=1) as response:json.load(response)
                break
            except OSError:time.sleep(.5)
        else:raise ProductionError('Tunnel readiness failed')
        grant={'approved':True,'request_sha256':request['request_sha256'],
               'lease_sha256':object_digest(lease),'endpoint':f'http://127.0.0.1:{port}',
               'max_runtime_seconds':600,'budget_usd':1}
        write_json(root/'grant.json',grant)
        result=execute_shot(intake,request['order_id'],request['request_id'],grant,
            root/'lease.json',root,credential,execute_authorized=True)
        write_json(root/'result.json',result)
        return result
    except BaseException as exc:
        write_json(root/'runner-error.json',{'error_type':type(exc).__name__,'at_epoch':time.time()})
        raise
    finally:
        # Only our own short-lived process groups; shared services stay intact.
        import os,signal
        for child in children:
            if child.poll() is None:
                try:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3)
                except ProcessLookupError:
                    pass
        for stream in logs:stream.close()
        (root/'download-locations.private.json').unlink(missing_ok=True)
        enforce(lease,control,root/'runner-cleanup.json',Runtime(120),execute_authorized=True,force_due=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','bundle','intake','request-file','credential','ssh-key'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    from production.model_install import cancel_on_signal
    with cancel_on_signal():
        result=run(a.root,a.bundle,a.intake,a.request_file,a.credential,a.ssh_key)
    print(json.dumps({'status':result['status'],'finished_video_accepted':False}))
