"""Exercise copied Megamozg app with synthetic identities and real local HTTPS.

Usage: python probe_pult_video.py STAGE. No shared state or external request.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3
import ssl
import subprocess
import sys
import tempfile
import time
from uuid import uuid4


async def main(stage):
    sys.path[:0] = [str(stage/'source'), str(stage/'source/integrations/megamozg'),
                   str(stage/'pult/pult_backend'), str(stage/'pult')]
    from aiohttp import ClientSession, TCPConnector, web
    from app import create_app, COOKIE
    from production.intake import Intake
    from production.pult_export import export_once, read_snapshot
    from video_routes import install
    from video_binding import prepare
    from video_media import install as install_media
    from video_refresh import refresh_once
    from playwright.async_api import async_playwright

    report = {'tests': [], 'environment': 'isolated synthetic HTTPS app',
              'external_model_calls': 0, 'production_changed': False}
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        report['tests'].append(name)

    with tempfile.TemporaryDirectory(prefix='probe-', dir=stage) as td:
        root = Path(td)
        async def auth(username, password):
            return {'id': 'owner-probe', 'username': 'owner-probe', 'name': 'Проверочный владелец'} if (username, password) == ('owner-probe', 'synthetic-only') else None
        app = create_app(root/'pult-state', stage/'pult/pult_ui/index.html',
                         origin='https://127.0.0.1', owner_auth=auth,
                         worker_enabled=False, executor=None, business_loader=lambda: None)
        store = app['store']
        order = Intake(root/'video', enqueue=True).create({'request_id': str(uuid4()), 'mode': 'new_video',
                                                          'brief': 'PRIVATE SOURCE DO NOT PROJECT'})
        with sqlite3.connect(root/'video/intake.sqlite3') as db:
            fp = db.execute('SELECT fingerprint FROM orders').fetchone()[0]
        task_id = str(uuid4())
        row = dict(id=task_id, title='Проверка связи с видеопроизводством', description='Синтетический заказ',
                   expected_result='Показать этап заказа', created_by='owner-probe', assignee_user_id='owner-probe',
                   assignee_kind='human', status='queued', waiting_on='', waiting_reason='', next_step='',
                   evidence='', result_note='', revision=1, attempts=0, created=time.time(), updated=time.time(), accepted_by=None)
        with store.db() as db:
            for uid, role in [('owner-probe','owner'), ('staff-probe','employee'), ('other-owner','owner')]:
                db.execute('INSERT INTO users(id,username,name,role,active) VALUES(?,?,?,?,1)', (uid,uid,uid,role))
            db.execute('INSERT INTO team_tasks('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',tuple(row.values()))
        link = dict(task_id=task_id, task_revision=1, owner_id='owner-probe', order_id=order['id'], order_fingerprint=fp)
        link = prepare(root/'pult-state/pult.sqlite3', **link)
        check('explicit_binding_from_real_pult_schema',link['task_id']==task_id)
        source_before = hashlib.sha256((root/'video/intake.sqlite3').read_bytes()).hexdigest()
        cache = root/'projection'; cache.mkdir(mode=0o700)
        published = refresh_once(root/'pult-state/pult.sqlite3',root/'video',cache,link)
        check('bounded_export_observed', published['state']=='observed')
        (root/'video').rename(root/'source-offline')
        check('web_source_unavailable', not (root/'video').exists())
        with store.db() as db:db.execute('UPDATE team_tasks SET revision=2 WHERE id=?',(task_id,))
        try:
            refresh_once(root/'pult-state/pult.sqlite3',root/'source-offline',cache,link)
            raise AssertionError('revoked_binding_refreshed')
        except ValueError:
            check('refresh_invalidates_revoked_binding',read_snapshot(cache,link) is None)
        with store.db() as db:db.execute('UPDATE team_tasks SET revision=1 WHERE id=?',(task_id,))
        refresh_once(root/'pult-state/pult.sqlite3',root/'source-offline',cache,link)
        flags = {'mode': 'normal', 'reads': 0}
        def loader(binding):
            flags['reads'] += 1
            if flags['mode'] == 'slow':
                time.sleep(2)
            if flags['mode'] == 'missing':
                raise FileNotFoundError()
            if flags['mode'] == 'revoke':
                with store.db() as db:
                    db.execute("DELETE FROM sessions WHERE user_id='owner-probe'")
            data = read_snapshot(cache, binding)
            if flags['mode']=='stale':
                data['observed_at'] -= 400
            data['private_unexpected'] = 'MUST NOT LEAK'
            return data
        install(app, store, {task_id: link}, loader)
        media_state={'revoked':False,'calls':0,'tampered':False}
        revision='d'*64
        video_bytes=(stage/'media-test.mp4').read_bytes() if (stage/'media-test.mp4').exists() else None
        def produce_media(expected,rev,kind):
            media_state['calls']+=1
            if media_state['revoked']:raise ValueError('plan_revoked')
            if kind=='catalog':return {'binding':link,'current':True,'versions':[{'revision':revision,'kinds':['video','project']}] if video_bytes else []}
            if rev!=revision:raise ValueError('unknown_revision')
            data=video_bytes if kind=='video' else b'PK\x05\x06'+b'\0'*18
            return {'binding':link,'revision':revision,'kind':kind,'current':True,'data':data,
                    'sha256':('0'*64 if media_state['tampered'] else hashlib.sha256(data).hexdigest())}
        install_media(app,store,{task_id:link},produce_media)
        cert, key = root/'cert.pem', root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                        '-subj','/CN=localhost','-keyout',str(key),'-out',str(cert)],
                       check=True, capture_output=True, timeout=10)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); tls.load_cert_chain(cert,key)
        runner = web.AppRunner(app); await runner.setup()
        site = web.TCPSite(runner, '127.0.0.1', 0, ssl_context=tls); await site.start()
        base = 'https://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
        endpoint = base+'/api/workboard/tasks/'+task_id+'/video'
        try:
            async with ClientSession(connector=TCPConnector(ssl=False)) as client:
                async with client.post(base+'/api/login',json={'username':'owner-probe','password':'synthetic-only'},headers={'Origin':'https://127.0.0.1'}) as r:
                    check('synthetic_login',r.status==200); token = r.cookies[COOKIE].value
                cookies = {COOKIE:token}
                async def get(cookie=None, url=endpoint):
                    async with client.get(url,cookies=cookie or {}) as r:
                        return r.status, await r.json()
                before = flags['reads']
                check('anonymous_401', (await get())[0]==401)
                check('staff_403', (await get({COOKIE:store.session('staff-probe')}))[0]==403)
                check('other_owner_403', (await get({COOKIE:store.session('other-owner')}))[0]==403)
                check('no_source_read_before_authorization', flags['reads']==before)
                status, data = await get(cookies)
                check('bound_order_observed',status==200 and data['state']=='observed' and data['preparation']=='queued')
                check('no_private_data',all(x not in json.dumps(data) for x in ['PRIVATE','LEAK',str(root),order['id']]))
                check('no_execution_or_film_acceptance',data['can_execute'] is False and data['finished_video_accepted'] is False)
                check('unknown_task_404',(await get(cookies,base+'/api/workboard/tasks/'+str(uuid4())+'/video'))[0]==404)
                flags['mode']='stale';check('expired_snapshot',(await get(cookies))[1]['state']=='stale')
                flags['mode']='missing';check('missing_is_not_ready',(await get(cookies))[1]['state']=='unavailable')
                flags['mode']='normal'
                with store.db() as db: db.execute('UPDATE team_tasks SET revision=2 WHERE id=?',(task_id,))
                before=flags['reads'];check('changed_task_binding',(await get(cookies))[1]['state']=='binding_stale')
                check('stale_binding_no_source_read',before==flags['reads'])
                with store.db() as db: db.execute('UPDATE team_tasks SET revision=1 WHERE id=?',(task_id,))
                flags['mode']='slow'; before=flags['reads']
                replies=await asyncio.gather(*(get(cookies) for _ in range(12)))
                check('single_flight_during_timeout',flags['reads']==before+1 and all(r[1]['state']=='unavailable' for r in replies))
                await get(cookies)
                check('no_new_thread_after_timeout',flags['reads']==before+1)
                await asyncio.sleep(0.6)
                flags['mode']='revoke';check('session_revoked_during_read',(await get(cookies))[0]==401)
                flags['mode']='normal'; token=store.session('owner-probe');cookies={COOKIE:token}
                if video_bytes:
                    url=endpoint+'/media/'+revision+'/video'
                    before=media_state['calls']
                    async with client.get(url) as r:check('media_anonymous_denied',r.status==401)
                    async with client.get(url,cookies={COOKIE:store.session('staff-probe')}) as r:check('media_unassigned_staff_denied',r.status==403)
                    check('media_no_producer_before_auth',before==media_state['calls'])
                    async with client.get(url,cookies=cookies,headers={'Range':'bytes=0-31'}) as r:
                        check('media_range_exact',r.status==206 and await r.read()==video_bytes[:32])
                    async with client.get(url,cookies=cookies,headers={'Range':'bytes=999999999-'}) as r:check('media_invalid_range',r.status==416)
                    media_state['tampered']=True
                    async with client.get(url,cookies=cookies) as r:check('media_hash_mismatch_denied',r.status==409)
                    media_state['tampered']=False;media_state['revoked']=True
                    async with client.get(url,cookies=cookies) as r:check('media_revoked_plan_denied',r.status==409)
                    media_state['revoked']=False
                    with store.db() as db:db.execute("UPDATE team_tasks SET assignee_user_id='staff-probe' WHERE id=?",(task_id,))
                    async with client.get(url,cookies={COOKIE:store.session('staff-probe')}) as r:check('media_assigned_staff_allowed',r.status==200 and await r.read()==video_bytes)
                    check('metadata_assigned_staff_allowed',(await get({COOKIE:store.session('staff-probe')}))[1]['state']=='observed')
                    with store.db() as db:db.execute("UPDATE team_tasks SET assignee_user_id='owner-probe' WHERE id=?",(task_id,))
                    async with client.get(url,cookies={COOKIE:store.session('staff-probe')}) as r:check('media_unassigned_again_denied',r.status==403)

            async with async_playwright() as p:
                browser=await p.chromium.launch(headless=True, args=['--no-sandbox'])
                try:
                    errors=[]
                    for width in (1024,390):
                        context=await browser.new_context(ignore_https_errors=True,viewport={'width':width,'height':900})
                        await context.add_cookies([{'name':COOKIE,'value':token,'url':base,'secure':True,'httpOnly':True,'sameSite':'Strict'}])
                        page=await context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                        await page.goto(base+'/team#workboard?task='+task_id)
                        panel=page.locator('[data-video-observation]')
                        await panel.wait_for(state='visible',timeout=10000)
                        await page.get_by_text('Состояние заказа прочитано',exact=True).wait_for()
                        check('visible_panel_'+str(width), 'Материалы: в очереди' in await panel.inner_text())
                        check('no_overflow_'+str(width),await page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                        await page.reload();await page.get_by_text('Состояние заказа прочитано',exact=True).wait_for()
                        check('reload_'+str(width),await panel.count()==1)
                        if video_bytes:
                            video=panel.locator('video');await video.wait_for()
                            await video.evaluate('(v)=>{v.muted=true;return v.play()}')
                            await video.evaluate('(v)=>new Promise((resolve,reject)=>{if(v.ended)return resolve();const timer=setTimeout(()=>reject(new Error("playback_timeout")),12000);v.addEventListener("ended",()=>{clearTimeout(timer);resolve()},{once:true})})')
                            check('protected_video_played_'+str(width),await video.evaluate('(v)=>v.error===null && v.ended'))
                            async with page.expect_download() as download:
                                await panel.get_by_text('Скачать монтажный комплект',exact=True).click()
                            file=await (await download.value).path()
                            check('protected_project_download_'+str(width),Path(file).read_bytes()==b'PK\x05\x06'+b'\0'*18)
                        await panel.screenshot(path=str(stage/('panel-'+str(width)+'.png')))
                        await context.close()
                    check('no_javascript_errors',not errors)
                finally:
                    await browser.close()
            check('source_database_unchanged',source_before==hashlib.sha256((root/'source-offline/intake.sqlite3').read_bytes()).hexdigest())
            with store.db() as db:
                check('no_model_jobs',db.execute('SELECT count(*) FROM tasks').fetchone()[0]==0)
                check('no_board_execution',db.execute('SELECT attempts FROM team_tasks WHERE id=?',(task_id,)).fetchone()[0]==0)
            report['source_reads']=flags['reads'];report['passed']=True
        finally:
            await runner.cleanup()
    (stage/'probe-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main(Path(sys.argv[1]).resolve()))
