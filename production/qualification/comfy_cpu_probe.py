"""Load an upstream workflow and export its API graph without weights or generation."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.request


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--comfy-source',type=Path,required=True)
    p.add_argument('--python',type=Path,required=True)
    p.add_argument('--workflow',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','TMPDIR'}}
    env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    log=(a.output/'server.log').open('w')
    child=subprocess.Popen([str(a.python),str(a.comfy_source/'main.py'),'--cpu','--offline',
        '--disable-partner-nodes','--disable-all-custom-nodes','--disable-auto-launch',
        '--listen','127.0.0.1','--port',str(port)],cwd=a.comfy_source,env=env,
        stdout=log,stderr=log,start_new_session=True)
    url=f'http://127.0.0.1:{port}'
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(150):
            if child.poll() is not None:raise RuntimeError('ComfyUI exited before readiness; inspect server.log')
            try:
                with opener.open(url+'/object_info',timeout=1) as r:info=json.load(r)
                break
            except OSError:time.sleep(.2)
        else:raise RuntimeError('ComfyUI readiness deadline')
        (a.output/'object_info.json').write_text(json.dumps(info))
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page()
            page.set_default_timeout(15000)
            submitted=[];errors=[];failed=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('requestfailed',lambda request:failed.append({'url':request.url,'failure':request.failure}))
            def guard(route):
                # The frontend must record its version in this disposable local profile.
                preferences = route.request.url.startswith(url+'/api/settings/') and route.request.method == 'POST'
                if not route.request.url.startswith(url+'/') or (route.request.method not in {'GET','HEAD'} and not preferences):
                    submitted.append(route.request.url);route.abort()
                else:route.continue_()
            page.route('**/*',guard)
            page.goto(url,wait_until='domcontentloaded')
            try:
                page.wait_for_function('() => !!window.comfyAPI?.app?.app?.graph')
            except Exception:
                diagnostic={'page_errors':errors,'failed':failed[:15],'blocked_writes':submitted,
                            'text':page.locator('body').inner_text()[:3000],
                            'globals':page.evaluate('() => Object.keys(window).filter(k=>/comfy|app|graph/i.test(k))')}
                (a.output/'browser-diagnostic.json').write_text(json.dumps(diagnostic,indent=2))
                print(json.dumps(diagnostic))
                raise
            workflow=json.loads(a.workflow.read_text())
            graph=page.evaluate('''async workflow => {
                const app=window.comfyAPI.app.app;
                await app.loadGraphData(workflow);
                const result=await app.graphToPrompt();return result.output;
            }''',workflow)
            (a.output/'api-workflow.json').write_text(json.dumps(graph,indent=2))
            browser.close()
        # Only disposable UI settings may be written. Every generation POST is blocked.
        missing=sorted({node['class_type'] for node in graph.values()}-set(info))
        from production.comfy import Executor
        from production.core import Runtime
        from production.recipes import ltx25_plan, verify_ltx25_weights
        plan=ltx25_plan('A fixed camera watches a blue cube on a grey table.',42,
                        'ltx25-cpu-preflight',url)
        preflight=Executor(url,a.output/'receipts').preflight(plan)
        (a.output/'recipe-preflight.json').write_text(json.dumps(preflight,indent=2))
        weights=verify_ltx25_weights(a.comfy_source/'models',Runtime(30))
        (a.output/'weight-check.json').write_text(json.dumps(weights,indent=2))
        queue=json.load(opener.open(url+'/queue',timeout=3))
        assert not queue['queue_running'] and not queue['queue_pending']
        report={'cpu_only':True,'generation_submitted':False,'api_nodes_disabled':True,
                'exported_nodes':len(graph),'missing_node_types':missing,
                'blocked_browser_writes':len(submitted),'queue_empty':True,
                'recipe_nodes':len(plan['workflow']),'recipe_preflight':preflight,
                'weight_check':weights}
        (a.output/'report.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
        assert not missing,missing
    finally:
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=2)
        log.close()


if __name__=='__main__':main()
