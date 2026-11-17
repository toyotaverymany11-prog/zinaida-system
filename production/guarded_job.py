"""One prepared video job: single allocation, independent cleanup, editable output.

Input artifacts and current price selection are prepared before this entrypoint.
No HTTP endpoint invokes it. Caller owns the dedicated root and exact intent.
"""
import argparse
import json
from pathlib import Path
import sys
import time

from .allocation import AllocationControl,allocate_once,launch_allocation,wait_allocated,watcher_ready,validate_intent
from .core import ProductionError,Runtime,read_json,write_json,object_digest
from .rental_guard import private_token
from .shots import load_request,check_current,folder,shot_file
from .shot_edit import build,package_preview
from .qualification.bound_pilot_runner import run


def execute(root,bundle,intake,request_file,credential,ssh_key):
    root=Path(root).resolve();intake=Path(intake).resolve()
    request=read_json(request_file)
    current=load_request(intake,request['order_id'],request['request_id'])
    if object_digest(current)!=object_digest(request):raise ProductionError('Prepared request file changed')
    check_current(intake,request['order_id'],request,Runtime(30))
    intent=read_json(root/'allocation.json');validate_intent(intent)
    if intent.get('request_sha256')!=request['request_sha256']:
        raise ProductionError('Allocation is not bound to this exact prepared shot')
    base=folder(intake,request['order_id'],request['request_id'])
    def finish(result):
        shot_file(intake,request['order_id'],request['request_id'])
        output=base/'edit';build(intake,request['order_id'],request['request_id'],output)
        if not (output/'project-package.json').exists():package_preview(output)
        from .shot_edit import project_file
        project_file(intake,request['order_id'],request['request_id'])
        result=dict(result,editable_project_ready=True,finished_video_accepted=False)
        write_json(root/'job-result.json',result);return result
    if (base/'result.json').exists():
        result=read_json(base/'result.json')
        if result.get('status')=='needs_quality_review':return finish(result)
    # Every prerequisite is checked before any cloud mutation.
    for name in ('comfy.tar.gz','worker.tar.gz','comfy-constraints.txt','gpu_bootstrap_probe.py'):
        if not (Path(bundle)/name).is_file():raise ProductionError('Pinned runtime bundle is incomplete')
    for name in ('download-locations.private.json','scoped_model_download.py'):
        if not (root/name).is_file():raise ProductionError('Prepared model transfer input missing')
    if not Path(ssh_key).is_file():raise ProductionError('SSH credential missing')
    control=AllocationControl(private_token(credential))
    try:
        # A resumed attempt is reconciliation-only; never start another create.
        if not (root/'create-intent.json').exists():
            if not (root/'launch.json').exists():
                write_json(root/'launch.json',launch_allocation(root,credential,sys.executable))
            runtime=Runtime(15)
            while not watcher_ready(root,intent):runtime.check();time.sleep(.1)
        allocate_once(root,control)  # Also validates an existing immutable intent.
        wait_allocated(root,timeout=30)
        result=run(root,Path(bundle),intake,Path(request_file),Path(credential),Path(ssh_key))
        return finish(result)
    finally:
        # Covers caller cancellation and unknown create replies. The already
        # running watcher keeps reconciling its original unique name.
        (root/'allocation-cancel').touch()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','bundle','intake','request-file','credential','ssh-key'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    from .model_install import cancel_on_signal
    with cancel_on_signal():
        result=execute(a.root,a.bundle,a.intake,a.request_file,a.credential,a.ssh_key)
    print(json.dumps({'status':result['status'],'editable_project_ready':result['editable_project_ready'],
        'finished_video_accepted':False}))
