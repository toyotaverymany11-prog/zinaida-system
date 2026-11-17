"""Exercise the source-preview window on a previously reviewed synthetic order."""
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
    url=f'http://127.0.0.1:{port}';log=(a.output/'server.log').open('w')
    child=None
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','TMPDIR'}}
    def start():
        nonlocal child
        child=subprocess.Popen([str(a.worker_python),'-m','production.intake','--root',str(a.root),'--port',str(port)],
            cwd=Path(__file__).resolve().parents[2],env=env,stdout=log,stderr=log,start_new_session=True)
        for _ in range(60):
            if child.poll() is not None:raise RuntimeError('Intake exited')
            try:
                with opener.open(url+'/api/health',timeout=1) as r:health=json.load(r)
                assert not health['planner_enabled'];return
            except OSError:time.sleep(.1)
        raise RuntimeError('No readiness')
    def stop():
        if child is not None and child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=2)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        start()
        orders=json.load(opener.open(url+'/api/orders',timeout=3));assert len(orders)==1
        ident=orders[0]['id']
        from playwright.sync_api import sync_playwright,expect
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':390,'height':844})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(url+'/review/'+ident)
            expect(page.locator('body')).to_contain_text('План отмечен как согласованный')
            if page.locator('#preview-build').is_enabled():page.locator('#preview-build').click()
            expect(page.locator('#preview-status')).to_contain_text('Черновая склейка готова.',timeout=25000)
            page.wait_for_function("() => document.getElementById('source-preview').readyState>=2")
            image=page.locator('#source-preview').evaluate('''async video => {
                video.currentTime=.5;
                await new Promise(resolve=>video.addEventListener('seeked',resolve,{once:true}));
                const c=document.createElement('canvas');c.width=video.videoWidth;c.height=video.videoHeight;
                const ctx=c.getContext('2d');ctx.drawImage(video,0,0);
                return {color:[...ctx.getImageData(100,100,1,1).data],duration:video.duration};
            }''')
            assert image['color'][2]>220 and image['color'][0]<30,image
            await_play="async video => {video.muted=true;await video.play();}"
            page.locator('#source-preview').evaluate(await_play)
            page.wait_for_function("() => document.getElementById('source-preview').currentTime>.8")
            page.locator('#source-preview').evaluate('video=>video.pause()')
            state=json.load(opener.open(url+'/api/orders/'+ident+'/preview',timeout=3))
            request_id=state['request_id'];assert state['status']=='ready'
            path=a.root/'previews'/ident/request_id/'receipt.json';receipt=json.loads(path.read_text())
            assert receipt['provider_calls']==0 and not receipt['generation_authorized']
            assert not receipt['finished_video_accepted']
            assert page.evaluate('() => document.documentElement.scrollWidth<=innerWidth')
            page.locator('#source-preview').scroll_into_view_if_needed()
            page.screenshot(path=str(a.output/'preview-mobile.png'))
            page.locator('#review-notes').fill('Synthetic probe: revoke only this plan decision.')
            page.locator('#change-plan').click()
            expect(page.locator('#preview-status')).to_contain_text('Сначала согласуй')
            expect(page.locator('#source-preview')).to_be_hidden()
            expect(page.locator('#preview-build')).to_be_disabled()
            denied=page.evaluate('async url => (await fetch(url)).status',url+'/api/orders/'+ident+'/preview/'+request_id)
            assert denied==409,denied
            page.locator('#review-notes').fill('Synthetic probe: restore local decision, no artistic acceptance.')
            page.locator('#accept-plan').click()
            expect(page.locator('#preview-status')).to_contain_text('Черновая склейка готова.')
            stop();start();page.reload()
            expect(page.locator('#preview-status')).to_contain_text('Черновая склейка готова.')
            after=json.load(opener.open(url+'/api/orders/'+ident+'/preview',timeout=3))
            assert after['request_id']==request_id and path.read_text()==json.dumps(receipt,ensure_ascii=False,indent=2)+'\n'
            assert not errors,errors
            report={'source_preview_played_in_browser':True,'sampled_pixel':image['color'],
                'duration':image['duration'],'restart_preserved_same_attempt':True,
                'revoked_decision_blocks_playback':True,
                'new_model_calls':0,'generation_authorized':False,'finished_video_accepted':False,
                'mobile_overflow':False,'page_errors':errors,'order_id':ident,'request_id':request_id}
            (a.output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
            browser.close()
    finally:stop();log.close()


if __name__=='__main__':main()
