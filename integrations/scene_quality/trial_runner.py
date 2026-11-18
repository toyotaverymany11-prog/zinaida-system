"""One internal A2V trial, bounded allocation and independent cleanup.

Uses a frozen snapshot of the already qualified production allocation/guard code.
No shared app is modified. No failed clip is released as an accepted film.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request
import urllib.parse
from uuid import uuid4


def cold_start_check(root, grant, now):
    """An allocation cannot bypass full cold-start timing with a cheaper grant."""
    from integrations.scene_quality.preflight import assess
    root = Path(root)
    proposal = json.loads((root/'cold-start-plan.json').read_text())
    lock = json.loads((root/'source/integrations/scene_quality/workflows/ltx25-i2v.lock.json').read_text())
    # This runner always downloads all pinned weights onto a disposable disk.
    # A future cache-aware runner needs its own verified cache receipt.
    if proposal.get('model_bytes_to_transfer') != lock['total_model_bytes']:
        raise RuntimeError('Cold-start estimate does not cover all pinned model bytes')
    proposal.update(grant_deadline_epoch=grant['terminate_at_epoch'],
                    remaining_budget_usd=grant['budget_usd'], hourly_total_ceiling_usd=5)
    result = assess(proposal, now)
    if not result['allocation_authorized']:
        raise RuntimeError('Cold-start blocked before POST: '+','.join(result['blockers']))
    return result


def recovery_grant(root, attempt, now):
    """A diagnosed SSH failure permits one replacement within the ORIGINAL grant."""
    if attempt == 1:
        return {'terminate_at_epoch': now + 43*60, 'budget_usd': 5}
    if attempt != 2:
        raise ValueError('At most one diagnosed replacement')
    first=Path(root)/'gpu-trial-01'
    intent=json.loads((first/'allocation.json').read_text())
    cleanup=json.loads((first/'runner-cleanup.json').read_text())
    error=json.loads((first/'error.json').read_text())
    if (cleanup.get('provider_absence_confirmed') is not True or
        error.get('error_type') != 'CalledProcessError' or (first/'queue-intent.json').exists()):
        raise RuntimeError('Replacement requires confirmed absence and diagnosed pre-inference failure')
    # Charge the failed attempt conservatively at the grant ceiling until cleanup receipt.
    used=max(0,(first/'runner-cleanup.json').stat().st_mtime-intent['created_at_epoch'])*5/3600
    remaining_budget=5-used
    if intent['terminate_at_epoch']-now<900 or remaining_budget<1:
        raise RuntimeError('Original qualification grant exhausted')
    return {'terminate_at_epoch':intent['terminate_at_epoch'],'budget_usd':remaining_budget}


def run(root, attempt=1):
    root=Path(root).resolve();sys.path.insert(0,str(root/'runtime_snapshot'))
    from production.allocation import AllocationControl,allocate_once,launch_allocation,wait_allocated,watcher_ready
    from production.rental import RunpodControl,enforce
    from production.rental_guard import private_token,guard_status
    from production.core import Runtime,read_json,write_json
    credential=Path('/opt/zinaida/private/video/runpod.key')
    ssh_key=Path('/opt/zinaida/private/video/gpu_pilot_ed25519')
    control=RunpodControl(private_token(credential));allocator=AllocationControl(private_token(credential))
    trial=root/('gpu-trial-%02d'%attempt);trial.mkdir(exist_ok=True)
    plan=read_json(root/'trial/binding.json');graph=read_json(root/'trial/workflow.json')
    from integrations.scene_quality.workflow import validate_static_ports
    validate_static_ports(graph)  # Fail before any paid resource for stale edges.
    children=[];streams=[];lease=None;ssh=None;intent=None
    def save(name,data):write_json(trial/name,data)
    def remaining():return max(0,(intent or {}).get('terminate_at_epoch',time.time())-time.time())
    def command(args,**kw):
        return subprocess.run(args,check=True,timeout=min(55,max(1,remaining()-10)),**kw)
    def start(args,name):
        stream=(trial/name).open('wb');streams.append(stream)
        p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,start_new_session=True)
        children.append(p);return p
    def wait(child,seconds):
        end=time.monotonic()+min(seconds,max(1,remaining()-130))
        while child.poll() is None:
            if time.monotonic()>end:raise TimeoutError('Finite child deadline')
            time.sleep(.5)
        if child.returncode:raise RuntimeError('Child failed, inspect private log')
    def http(endpoint,body=None,limit=8*1024*1024):
        data=json.dumps(body).encode() if body is not None else None
        req=urllib.request.Request(endpoint,data=data,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=min(20,max(1,remaining()-120))) as r:
            b=r.read(limit+1)
        if len(b)>limit:raise RuntimeError('Oversized Comfy response')
        return b
    try:
        # Validate immutable media locally before any allocation.
        for kind,key in [('image','image'),('speech','speech')]:
            f=root/'trial'/plan[key]['name']
            if hashlib.sha256(f.read_bytes()).hexdigest()!=plan[key]['sha256']:
                raise RuntimeError('Prepared media changed: '+kind)
        from importlib.util import spec_from_file_location,module_from_spec
        spec=spec_from_file_location('contract_snapshot',root/'source/integrations/scene_quality/contracts.py')
        mod=module_from_spec(spec);spec.loader.exec_module(mod)
        if mod.digest(graph)!=plan['graph_sha256']:raise RuntimeError('Graph binding changed')
        if not (root/'preflight-models.json').exists() or not (root/'download-locations.private.json').exists():
            raise RuntimeError('Fresh pinned model metadata missing')
        if time.time()-(root/'preflight-models.json').stat().st_mtime>1800:
            raise RuntimeError('Model metadata expired before rental')
        omni=read_json(root/'trial/omni-model.json')
        if omni.get('license_name')!='Apache-2.0' or len(omni.get('license_sha256',''))!=64:
            raise RuntimeError('Pinned experimental reviewer license unverified')
        if not (trial/'allocation.json').exists():
            # Same account is checked immediately before creating our one exclusive resource.
            active=allocator.collection('GET',Runtime(20))
            if active.get('pods') or active['pagination']['hasNextPage']:
                raise RuntimeError('Account has resources; do not interfere or allocate')
            now=time.time()
            grant=recovery_grant(root,attempt,now)
            save('cold-start-preflight.json',cold_start_check(root,grant,now))
            public_key=subprocess.check_output(['ssh-keygen','-y','-f',str(ssh_key)],text=True,timeout=5).strip()
            if not public_key.startswith('ssh-ed25519 '):raise RuntimeError('Existing SSH key binding invalid')
            intent={'schema_version':1,'approved':True,'created_at_epoch':now,**grant,
                'hourly_total_usd':5,'request_sha256':plan['graph_sha256'],
                'body':{'name':'zina-video-'+uuid4().hex,
                'image':'runpod/pytorch@sha256:e745934b44a4071b1d20a181cdff9e92dc4af3d304cbaafbd0d23f8dacbe5300',
                'gpu':{'id':'NVIDIA H100 80GB HBM3','count':1},'disk':140,'cloud':'SECURE',
                'dataCenterIds':['EU-FR-1','AP-IN-1'],'startSsh':True,'startJupyter':False,'ports':['22/tcp'],
                'env':{'PUBLIC_KEY':public_key}}}
            save('allocation.json',intent)
        else:intent=read_json(trial/'allocation.json')
        if not (trial/'launch.json').exists():save('launch.json',launch_allocation(trial,credential,sys.executable))
        deadline=time.monotonic()+20
        while not watcher_ready(trial,intent):
            if time.monotonic()>deadline:raise RuntimeError('Independent watcher not armed')
            time.sleep(.1)
        allocate_once(trial,allocator);lease=wait_allocated(trial,timeout=45)
        until=time.monotonic()+min(300,remaining()-900)
        while time.monotonic()<until:
            pod=control.get(lease['resource']['id'],Runtime(15));direct=(pod or {}).get('ssh',{}).get('direct')
            if direct:break
            time.sleep(2)
        else:raise RuntimeError('SSH readiness deadline')
        save('provider-ready.json',pod)
        opts=['-i',str(ssh_key),'-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=accept-new',
              '-o','BatchMode=yes','-o','PasswordAuthentication=no',
              '-o','UserKnownHostsFile='+str(trial/'known_hosts'),'-o','ConnectTimeout=10',
              '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3']
        ssh=['ssh',*opts,'-p',str(direct['port']),direct['username']+'@'+direct['host']]
        save('ssh-args.json',ssh);command(ssh+['echo connected'])
        bundle=Path('/opt/zinaida/staging/video-production-worker-20261117/gpu-pilot-20261117')
        package=trial/'deploy.tar.gz'
        with tarfile.open(package,'w:gz') as archive:
            for name in ['comfy.tar.gz','worker.tar.gz','comfy-constraints.txt','gpu_bootstrap_probe.py']:
                archive.add(bundle/name,arcname=name)
            archive.add(root/'runtime_snapshot/production/qualification/scoped_model_download.py',arcname='scoped_model_download.py')
            for name in ['sq_zina.jpg','sq_speech.wav','omni-model.json']:
                archive.add(root/'trial'/name,arcname=name)
            archive.add(root/'source/integrations/scene_quality/gpu_omni_probe.py',arcname='gpu_omni_probe.py')
        command(ssh+['tar -xzf - -C /workspace'],input=package.read_bytes())
        child=start(['timeout','650',*ssh,'python3 /workspace/gpu_bootstrap_probe.py --root /workspace --timeout 600'],'bootstrap.log')
        wait(child,650)
        command(ssh+['mkdir -p /workspace/comfy/input; cp /workspace/sq_zina.jpg /workspace/sq_speech.wav /workspace/comfy/input/'])
        for key in ['image','speech']:
            file=plan[key];r=command(ssh+['sha256sum /workspace/comfy/input/'+file['name']],capture_output=True)
            if r.stdout.decode().split()[0]!=file['sha256']:raise RuntimeError('Transferred media SHA mismatch')
        config=root/'download-locations.private.json'
        command(ssh+['umask 077; cat > /workspace/download-locations.private.json'],input=config.read_bytes());config.unlink()
        transfer_seconds=min(1200,int(remaining()-850))
        if transfer_seconds<60:raise RuntimeError('Insufficient original lease for model transfer')
        child=start(['timeout',str(transfer_seconds+30),*ssh,'python3 /workspace/scoped_model_download.py --timeout '+str(transfer_seconds)],'model-download.log')
        wait(child,transfer_seconds+30)
        r=command(ssh+['cat /workspace/model-download-report.json'],capture_output=True);models=json.loads(r.stdout);save('model-download-report.json',models)
        if models['status']!='verified':raise RuntimeError('Model hashes not verified')
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        tunnel=start(['timeout','1400',*ssh[:-1],'-o','ExitOnForwardFailure=yes','-L',f'127.0.0.1:{port}:127.0.0.1:8188','-N',ssh[-1]],'tunnel.log')
        base=f'http://127.0.0.1:{port}'
        for _ in range(40):
            try:json.loads(http(base+'/system_stats'));break
            except OSError:time.sleep(.5)
        else:raise RuntimeError('Comfy tunnel not ready')
        info=json.loads(http(base+'/object_info',limit=16*1024*1024));save('object-info.json',info)
        missing=sorted({n['class_type'] for n in graph.values()}-set(info))
        if missing:raise RuntimeError('Missing required nodes: '+','.join(missing))
        if not guard_status(trial,lease)['ready']:raise RuntimeError('Cleanup guard not ready')
        marker=trial/'queue-intent.json'
        if marker.exists():raise RuntimeError('Queue attempt already exists; reconcile without POST repeat')
        client=str(uuid4());save('queue-intent.json',{'client_id':client,'graph_sha256':plan['graph_sha256'],'status':'submitting'})
        submitted=json.loads(http(base+'/prompt',{'prompt':graph,'client_id':client,'extra_data':{'scene_quality_trial':client}}))
        save('queue-response.json',submitted);pid=submitted['prompt_id'];end=time.monotonic()+min(720,remaining()-150)
        while time.monotonic()<end:
            history=json.loads(http(base+'/history/'+urllib.parse.quote(pid)))
            h=history.get(pid)
            if h and h.get('status',{}).get('completed'):
                save('history.json',h)
                if h['status'].get('status_str')=='error':raise RuntimeError('Comfy execution reported error')
                break
            time.sleep(2)
        else:raise RuntimeError('Inference deadline; no automatic repeat')
        def videos(value):
            if isinstance(value,dict):
                if str(value.get('filename','')).endswith('.mp4'):yield value
                for v in value.values():yield from videos(v)
            elif isinstance(value,list):
                for v in value:yield from videos(v)
        media=next(videos(h.get('outputs',{})))
        if media.get('subfolder')!='scene_quality' or Path(media['filename']).name!=media['filename']:
            raise RuntimeError('Unexpected output location')
        query=urllib.parse.urlencode({k:media[k] for k in ['filename','subfolder','type']})
        movie=trial/'scene.mp4';movie.write_bytes(http(base+'/view?'+query,limit=64*1024*1024))
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(movie)]));save('ffprobe.json',probe)
        command(['ffmpeg','-v','error','-i',str(movie),'-map','0:v:0','-map','0:a:0','-f','null','-'])
        result={'status':'generated_needs_independent_av_review','sha256':hashlib.sha256(movie.read_bytes()).hexdigest(),
                'bytes':movie.stat().st_size,'duration_seconds':float(probe['format']['duration']),
                'binding':plan,'owner_ready':False,'publication':False}
        save('result.json',result)
        # Optional native AV experiment shares the SAME bounded rental. It cannot approve release.
        if remaining()>600:
            try:
                http(base+'/free',{'unload_models':True,'free_memory':True})
                setup=('python3 -m venv --system-site-packages /workspace/qa-venv && '
                    '/workspace/qa-venv/bin/pip install --disable-pip-version-check --no-cache-dir '
                    'transformers==4.52.3 qwen-omni-utils==0.0.8 accelerate av soundfile')
                child=start(['timeout','180',*ssh,setup],'qa-install.log');wait(child,180)
                path='/workspace/comfy/output/scene_quality/'+media['filename']
                child=start(['timeout','380',*ssh,'HF_HUB_DISABLE_XET=1 /workspace/qa-venv/bin/python '
                      '/workspace/gpu_omni_probe.py --video '+path+' --model-config /workspace/omni-model.json '
                      '--output /workspace/qa-result.json'],'qa-model.log');wait(child,380)
                q=command(ssh+['cat /workspace/qa-result.json'],capture_output=True);save('qa-result.json',json.loads(q.stdout))
            except Exception as exc:save('qa-unqualified.json',{'status':'not_qualified','error_type':type(exc).__name__})
        return result
    except BaseException as exc:
        save('error.json',{'error_type':type(exc).__name__,'message':str(exc)[:200],
                           'paid_create_repeated':False,'owner_ready':False});raise
    finally:
        for child in children:
            if child.poll() is None:
                try:os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=3)
                except (ProcessLookupError,subprocess.TimeoutExpired):
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
        for stream in streams:stream.close()
        (trial/'allocation-cancel').touch()
        (root/'download-locations.private.json').unlink(missing_ok=True)
        if lease:enforce(lease,control,trial/'runner-cleanup.json',Runtime(120),execute_authorized=True,force_due=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--attempt',type=int,choices=[1,2],default=1);a=p.parse_args()
    def stop(signum,frame):raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    print(json.dumps(run(a.root,a.attempt)))
