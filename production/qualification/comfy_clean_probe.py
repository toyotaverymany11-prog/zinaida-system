"""Exercise the pinned recipe against a clean CPU-only ComfyUI through its API."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.request

from production.comfy import Executor
from production.core import Runtime, read_json, write_json
from production.model_install import cancel_on_signal
from production.recipes import WORKFLOWS, ltx25_plan


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--python',type=Path,required=True)
    p.add_argument('--comfy-source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    runtime=Runtime(120)
    lock=read_json(WORKFLOWS/'ltx25-t2v.lock.json')
    commit=runtime.run(['git','rev-parse','HEAD'],cwd=a.comfy_source).strip()
    assert commit==lock['runtime']['comfy_commit']
    cfg=(a.python.parent.parent/'pyvenv.cfg').read_text()
    assert 'include-system-site-packages = false' in cfg
    dependency_check=runtime.run([str(a.python),'-m','pip','check']).strip()
    torch_info=json.loads(runtime.run([str(a.python),'-I','-c',
        "import torch,json;print(json.dumps({'version':torch.__version__,'cuda':torch.version.cuda,'sum':torch.ones(3).sum().item()}))"]))
    assert torch_info['cuda'] is None and torch_info['sum']==3
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    root=a.output/'comfy-data';(root/'user').mkdir(parents=True)
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','TMPDIR'}}
    env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1')
    url=f'http://127.0.0.1:{port}'
    child=None
    with (a.output/'server.log').open('w') as log:
        try:
            child=subprocess.Popen([str(a.python),str(a.comfy_source/'main.py'),
                '--cpu','--offline','--disable-partner-nodes','--disable-all-custom-nodes',
                '--disable-auto-launch','--listen','127.0.0.1','--port',str(port),
                '--base-directory',str(root),'--user-directory',str(root/'user'),
                '--database-url','sqlite:///:memory:'],cwd=a.comfy_source,env=env,
                stdout=log,stderr=log,start_new_session=True)
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            while True:
                runtime.check()
                if child.poll() is not None:raise RuntimeError('Clean ComfyUI failed; inspect server.log')
                try:
                    with opener.open(url+'/object_info',timeout=1) as response:info=json.load(response)
                    break
                except OSError:time.sleep(.2)
            plan=ltx25_plan('A fixed camera watches a blue cube.',42,'clean-cpu-probe',url)
            result=Executor(url,a.output/'receipts').preflight(plan)
            queue=json.load(opener.open(url+'/queue',timeout=3))
            missing=sorted(set(plan['node_classes'])-set(info))
            assert not missing,missing
            assert len(result['errors'])==5,result
            assert all('model/option missing' in e for e in result['errors']),result
            assert not queue['queue_running'] and not queue['queue_pending']
            report={'comfy_commit':commit,'clean_venv':True,'pip_check':dependency_check,
                    'torch':torch_info,'recipe_nodes':len(plan['workflow']),
                    'missing_node_types':missing,'preflight':result,
                    'queue_empty':True,'generation_submitted':False,
                    'model_weights_downloaded':False}
            write_json(a.output/'report.json',report)
        finally:
            if child is not None and child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3)
    report['temporary_process_stopped']=child.poll() is not None
    write_json(a.output/'report.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    with cancel_on_signal():main()
