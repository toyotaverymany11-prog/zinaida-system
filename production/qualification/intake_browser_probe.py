"""Exercise owner intake in a real browser using explicitly synthetic media.

Requires Playwright plus its Chromium headless shell in the invoking Python.
Creates only an owned loopback process, stops it on success or failure.
"""
import argparse
import json
import os
import re
from uuid import uuid4
from pathlib import Path
import signal
import subprocess
import time
import urllib.request


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--worker-python',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--port',type=int,default=18118)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    work=Path(__file__).resolve().parents[2]
    env={k:os.environ[k] for k in ('PATH','HOME','LANG','TMPDIR') if k in os.environ}
    log=(a.output/'server.log').open('w')
    process=subprocess.Popen([str(a.worker_python),'-m','production.intake','--root',str(a.output/'data'),
        '--port',str(a.port)],cwd=work,env=env,start_new_session=True,stdout=log,stderr=log)
    url=f'http://127.0.0.1:{a.port}'
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(50):
            if process.poll() is not None: raise RuntimeError('Intake exited before readiness')
            try:
                opener.open(url,timeout=1).close()
                break
            except OSError: time.sleep(.1)
        else: raise RuntimeError('Intake did not become ready')
        from playwright.sync_api import sync_playwright, expect
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=[
                '--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
            context=browser.new_context(viewport={'width':1365,'height':1000},permissions=['microphone'])
            page=context.new_page()
            page.set_default_timeout(12000)
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(url)
            page.get_by_label('Заменяем персонажа целиком',exact=True).check()
            page.locator('#brief').fill('Технический заказ: медведь вместо человека. Сохранить действие с чашкой.')
            page.locator('#changes').fill('Персонаж и связанные тени.')
            page.locator('#preserve').fill('Камера, тайминг и принятый звук.')
            page.locator('#references').set_input_files(str(a.source/'red.mp4'))
            page.locator('#characters').set_input_files(str(a.source/'qr.png'))
            page.get_by_role('button',name='Сохранить заказ',exact=True).click()
            expect(page.locator('#feedback')).to_contain_text('сохранён. Производство пока не запущено.')
            page.get_by_role('button',name='Сохранить заказ',exact=True).click()
            expect(page.locator('#submit')).to_be_enabled()
            assert page.locator('.receipt').count()==1
            page.reload()
            page.wait_for_selector('.receipt')
            expect(page.locator('.receipt')).to_contain_text(
                'Ожидается смысловая и художественная проверка.')
            prepared = json.load(opener.open(url+'/api/orders', timeout=5))[0]
            assert prepared['preparation']['status'] == 'awaiting_review'
            assert prepared['preparation']['reference_count'] == 1
            assert prepared['budget_usd'] == 0 and not prepared['generation_authorized']
            receipt = json.loads((a.output/'data'/'preparations'/prepared['id']/'receipt.json').read_text())
            assert receipt['provider_calls'] == 0 and receipt['semantic_review'] == 'not_performed'
            packet = json.load(opener.open(url+'/api/orders/'+prepared['id']+'/evidence', timeout=15))
            token = re.search(r"const token='([^']+)'", opener.open(url, timeout=3).read().decode())[1]
            plan = {'request_id': str(uuid4()), 'expected_revision': 0,
                'packet_sha256': packet['packet_sha256'],
                'plan': {'author': 'synthetic-browser-probe',
                    'summary': 'Техническая проверка сохранения плана на цветном образце',
                    'open_questions': ['Нужен настоящий художественный референс'],
                    'scenes': [{'source': {'asset_id': ref['asset_id'], 'start': 0,
                        'end': ref['duration_seconds']}, 'observation': 'Технический цветной образец',
                        'action': 'Проверить путь заказа без генерации',
                        'preserve': ['Длительность и порядок исходных кадров'],
                        'change': ['Художественная правка ещё не задана'],
                        'checks': ['Сверить длительность с исходником']}
                        for ref in packet['references']]}}
            request = urllib.request.Request(url+'/api/orders/'+prepared['id']+'/plan',
                data=json.dumps(plan).encode(), headers={'X-Intake-Token': token})
            first_plan = json.load(opener.open(request, timeout=15))
            assert json.load(opener.open(request, timeout=15)) == first_plan
            assert first_plan['revision'] == 1 and not first_plan['generation_authorized']
            review = context.new_page()
            review.on('pageerror',lambda error:errors.append(str(error)))
            review.goto(url+'/review/'+prepared['id'])
            expect(review.locator('body')).to_contain_text('Версия 1')
            expect(review.locator('body')).to_contain_text('Ожидается независимая')
            review.locator('figure img').first.scroll_into_view_if_needed()
            review.wait_for_function('() => document.querySelector("figure img").naturalWidth > 0')
            review.wait_for_function('() => document.querySelector("video").readyState >= 1')
            review.set_viewport_size({'width':390,'height':844})
            assert review.evaluate('() => document.documentElement.scrollWidth <= innerWidth')
            review.screenshot(path=str(a.output/'review-mobile.png'), full_page=True)
            review.close()
            page.screenshot(path=str(a.output/'desktop.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(a.output/'mobile.png'),full_page=True)
            page.get_by_label('Создаём новый ролик',exact=True).check()
            page.get_by_role('button',name='Записать голосом',exact=True).click()
            expect(page.locator('#record-state')).to_have_text('Идёт запись')
            page.wait_for_timeout(1200)
            page.get_by_role('button',name='Остановить запись',exact=True).click()
            expect(page.locator('#record-state')).to_have_text('Запись готова')
            page.get_by_role('button',name='Сохранить заказ',exact=True).click()
            expect(page.locator('.receipt')).to_have_count(2)
            assert errors==[],errors
            data=json.load(opener.open(url+'/api/orders'))
            assert data[0]['status']=='needs_transcription' and data[0]['voice']['kind']=='audio'
            report={'browser_flow':True,'duplicate_prevented':True,'reload_persists':True,
                'scene_plan_saved':True, 'evidence_images_loaded':True, 'reference_video_loaded':True, 'controller_status':prepared['preparation']['status'], 'mobile_overflow':False,'voice_recorded_and_saved':True,'page_errors':errors,
                'provider_calls':0,'production_started':False,'synthetic_media':True}
            (a.output/'report.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(report))
            browser.close()
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            process.wait(timeout=10)
        log.close()


if __name__=='__main__': main()
