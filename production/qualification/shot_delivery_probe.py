"""Download and revocation probe on a private copy of a real shot order."""
import argparse
import json
import hashlib
import shutil
import zipfile
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
    p.add_argument('--order-id',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    source_root=a.root
    a.root=a.output/'intake-copy'
    shutil.copytree(source_root,a.root)
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
                with opener.open(url+'/api/health',timeout=1) as r:json.load(r)
                break
            except OSError:time.sleep(.1)
        from playwright.sync_api import sync_playwright,expect
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':390,'height':844})
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(url+'/review/'+a.order_id)
            expect(page.locator('#shot-status')).to_contain_text('Нужна проверка качества')
            page.wait_for_function("() => document.getElementById('shot-video').readyState>=2")
            page.locator('#shot-video').evaluate('async v=>{v.muted=true;await v.play()}')
            page.wait_for_function("() => document.getElementById('shot-video').ended")
            playback=page.locator('#shot-video').evaluate('v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,ended:v.ended,error:v.error})')
            assert playback['ended'] and playback['error'] is None
            assert page.evaluate('() => document.documentElement.scrollWidth<=innerWidth')
            assert not errors,errors
            expect(page.locator('#shot-project')).to_be_visible()
            href=page.locator('#shot-project').get_attribute('href')
            with page.expect_download() as event:page.locator('#shot-project').click()
            downloaded=a.output/'browser-project.zip'
            event.value.save_as(downloaded)
            with zipfile.ZipFile(downloaded) as archive:
                assert archive.testzip() is None
                original=archive.read('assets/shot.mp4')
                assert hashlib.sha256(original).hexdigest()=='bd7e779a7972a4e040b5115e4933ac4db11b3506bd8e174b5334302fd379180b'
                timeline=json.loads(archive.read('timeline.otio'))
                refs=[]
                def visit(value):
                    if isinstance(value,dict):
                        if 'target_url' in value:refs.append(value['target_url'])
                        for child in value.values():visit(child)
                    elif isinstance(value,list):
                        for child in value:visit(child)
                visit(timeline)
                assert refs==['assets/shot.mp4','assets/shot.mp4'],refs
            page.locator('#review-notes').fill('Isolated copied order: test revocation of package delivery')
            page.locator('#change-plan').click()
            expect(page.locator('#review-feedback')).to_contain_text('Решение сохранено')
            page.locator('#shot-refresh').click()
            expect(page.locator('#shot-project')).to_be_hidden()
            denied=page.evaluate('async u=>(await fetch(u)).status',href)
            assert denied==409,denied
            assert not errors,errors
            browser.close()
        result={'status':'passed','download_bytes':downloaded.stat().st_size,'zip_sha256':hashlib.sha256(downloaded.read_bytes()).hexdigest(),'relative_references':refs,'revoked_delivery_status':denied,'original_order_unchanged':True,'playback':playback,'page_errors':errors,
                'semantic_audio_reviewed':False,'artistic_accepted':False,'finished_video_accepted':False}
        (a.output/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
    finally:
        if child.poll() is None:
            os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=2)
        log.close()


if __name__=='__main__':main()
