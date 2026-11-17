"""Read/write/playback probe on an explicitly synthetic, prebuilt shot fixture."""
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
    p.add_argument('--worker-python',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    url=f'http://127.0.0.1:{port}'
    log=(a.output/'server.log').open('w')
    child=subprocess.Popen([str(a.worker_python),'-m','production.intake','--root',str(a.root),'--port',str(port)],
        cwd=Path(__file__).resolve().parents[2],stdout=log,stderr=log,start_new_session=True)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        for _ in range(60):
            if child.poll() is not None:raise RuntimeError('Intake exited')
            try:
                with opener.open(url+'/api/health',timeout=1) as r:health=json.load(r)
                assert not health['planner_enabled'];break
            except OSError:time.sleep(.1)
        orders=json.load(opener.open(url+'/api/orders',timeout=3));assert len(orders)==1
        ident=orders[0]['id']
        from playwright.sync_api import sync_playwright,expect
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':390,'height':844})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(url+'/review/'+ident)
            expect(page.locator('#shot-status')).to_contain_text('Нужна проверка качества')
            page.wait_for_function("() => document.getElementById('shot-video').readyState>=2")
            page.locator('#shot-video').evaluate('async v=>{v.muted=true;await v.play()}')
            page.wait_for_function("() => document.getElementById('shot-video').ended")
            playback=page.locator('#shot-video').evaluate('v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,ended:v.ended,error:v.error})')
            page.locator('#shot-notes').fill('Synthetic geometry failure; not real model qualification')
            page.locator('#shot-accept').click()
            expect(page.locator('#shot-status')).to_contain_text('failed quality criterion')
            page.locator('#shot-reject').click()
            expect(page.locator('#shot-status')).to_contain_text('Нужна доработка сцены')
            for checkbox in page.locator('[data-shot-check]').all():checkbox.check()
            page.locator('#shot-notes').fill('All synthetic fixture structural checks only')
            page.locator('#shot-accept').click()
            expect(page.locator('#shot-status')).to_contain_text('Сцена принята отдельно')
            state=json.load(opener.open(url+'/api/orders/'+ident+'/shots',timeout=3))
            assert not state['quality_review']['finished_video_accepted']
            page.locator('#review-notes').fill('Revoke synthetic plan')
            page.locator('#change-plan').click()
            expect(page.locator('#review-feedback')).to_contain_text('Решение сохранено')
            page.locator('#shot-refresh').click()
            expect(page.locator('#shot-status')).to_contain_text('План изменился')
            expect(page.locator('#shot-video')).to_be_hidden()
            denied=page.evaluate('async u=>(await fetch(u)).status',url+'/api/orders/'+ident+'/shots/'+state['request_id']+'/video')
            assert denied==409
            assert page.evaluate('() => document.documentElement.scrollWidth<=innerWidth')
            assert not errors,errors
            browser.close()
        result={'status':'passed','fixture':'synthetic_red_clip_not_gpu_generation','playback':playback,
                'failed_checks_block_acceptance':True,'revoked_plan_denied':denied,'page_errors':errors,
                'finished_video_accepted':False}
        (a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    finally:
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=2)
        log.close()


if __name__=='__main__':main()
