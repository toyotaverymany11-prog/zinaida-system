"""One real subscription-authenticated visual analysis; synthetic video, no generation."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import urllib.request


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--worker-python',type=Path,required=True)
    p.add_argument('--codex',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--port',type=int,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    work=Path(__file__).resolve().parents[2]
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','TMPDIR'}}
    log=(a.output/'server.log').open('w')
    process=subprocess.Popen([str(a.worker_python),'-m','production.intake','--root',str(a.output/'data'),
        '--port',str(a.port),'--planner-codex',str(a.codex),'--analysis-timeout','35'],cwd=work,env=env,
        start_new_session=True,stdout=log,stderr=log)
    url=f'http://127.0.0.1:{a.port}'
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(50):
            if process.poll() is not None:raise RuntimeError('Intake exited')
            try:opener.open(url,timeout=1).close();break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('No HTTP readiness')
        from playwright.sync_api import sync_playwright,expect
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':390,'height':844})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url)
            page.locator('#brief').fill('Разбери приложенный материал. Сохрани хронометраж и цветовую палитру. Это техническая проба, не придумывай сюжет.')
            page.locator('#references').set_input_files(str(a.source/'blue.mp4'))
            page.get_by_role('button',name='Сохранить заказ',exact=True).click()
            expect(page.locator('.analysis-status')).to_contain_text('План составлен.',timeout=40000)
            orders=json.load(opener.open(url+'/api/orders',timeout=3));assert len(orders)==1
            order=orders[0];ident=order['id']
            assert order['analysis']['status']=='needs_review' and order['budget_usd']==0
            packet=json.load(opener.open(url+'/api/orders/'+ident+'/evidence',timeout=10))
            plan=packet['latest_plan'];assert plan['revision']==1 and not plan['generation_authorized']
            text=json.dumps(plan['plan'],ensure_ascii=False)
            assert re.search('син|голуб',text,re.I),text
            assert plan['semantic_review']=='pending' and plan['artistic_review']=='pending'
            receipt=json.loads((a.output/'data/analyses'/ident/order['analysis']['request_id']/'receipt.json').read_text())
            assert receipt['status']=='plan_saved' and receipt['evidence']['tool_calls']==0
            token=re.search(r"const token='([^']+)'",opener.open(url,timeout=3).read().decode())[1]
            repeat=urllib.request.Request(url+'/api/orders/'+ident+'/analyze',
                data=json.dumps({'request_id':order['analysis']['request_id']}).encode(),headers={'X-Intake-Token':token})
            assert json.load(opener.open(repeat,timeout=3))['accepted']
            assert json.load(opener.open(url+'/api/orders',timeout=3))[0]['analysis']['status']=='needs_review'
            page.reload();expect(page.locator('.analysis-status')).to_contain_text('План составлен.')
            page.get_by_role('link',name='Материалы и план',exact=True).click()
            expect(page.locator('body')).to_contain_text('Версия 1')
            expect(page.locator('body')).to_contain_text('Ожидается независимая')
            page.locator('#review-notes').fill('Синтетическая техническая проверка решения по плану; художественная приёмка не выполнялась.')
            page.get_by_role('button',name='План согласован',exact=True).click()
            expect(page.locator('#review-feedback')).to_contain_text('Решение сохранено.')
            reviewed=json.load(opener.open(url+'/api/orders/'+ident+'/evidence',timeout=10))['latest_plan']
            assert reviewed['local_review']['decision']=='accept_plan'
            assert not reviewed['generation_authorized'] and not reviewed['local_review']['finished_video_accepted']
            page.reload()
            expect(page.locator('body')).to_contain_text('План отмечен как согласованный')
            assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth')
            page.get_by_role('heading',name='План сцен',exact=True).scroll_into_view_if_needed()
            page.screenshot(path=str(a.output/'plan-mobile.png'))
            assert not errors,errors
            report={'real_codex_visual_analysis':True,'correct_synthetic_color':True,
                'durable_plan_revision':1,'repeated_request_did_not_requeue':True,
                'local_plan_decision_saved_without_generation':True,
                'generation_authorized':False,'artistic_acceptance':False,'synthetic_media':True,
                'page_errors':errors,'usage':receipt['evidence']['usage'],'model':receipt['evidence']['model']}
            (a.output/'report.json').write_text(json.dumps(report,indent=2))
            print(json.dumps(report));browser.close()
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=6)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=2)
        log.close()


if __name__=='__main__':main()
