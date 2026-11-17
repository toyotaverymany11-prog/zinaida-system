"""Owner-local order intake. Stores briefs and media; never starts generation.

The controller consumes preparation jobs committed alongside orders.
Bind only to loopback until a separately verified identity gateway is available.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import secrets
import sqlite3
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from .core import ProductionError, Runtime, digest, object_digest

MAX_UPLOAD = 128 * 1024 * 1024
MODES = {'reference', 'face_replace', 'body_replace', 'new_video'}


class Intake:
    def __init__(self, root: Path, *, enqueue=False):
        self.enqueue = enqueue
        self.root = root.resolve()
        (self.root / 'assets').mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, data TEXT NOT NULL)')

            db.execute("""CREATE TABLE IF NOT EXISTS preparation_jobs (
                order_id TEXT PRIMARY KEY REFERENCES orders(id),
                status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0)""")
            db.execute('BEGIN IMMEDIATE')
            columns = {row[1] for row in db.execute('PRAGMA table_info(preparation_jobs)')}
            for name, spec in {'analysis_status': "TEXT NOT NULL DEFAULT 'not_requested'",
                               'analysis_request_id': 'TEXT', 'analysis_error': 'TEXT',
                               'preview_status': "TEXT NOT NULL DEFAULT 'not_requested'",
                               'preview_request_id':'TEXT','preview_error':'TEXT'}.items():
                if name not in columns:
                    db.execute(f'ALTER TABLE preparation_jobs ADD COLUMN {name} {spec}')
            db.execute('CREATE TABLE IF NOT EXISTS analysis_requests (request_id TEXT PRIMARY KEY, order_id TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS preview_requests (request_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, request_sha256 TEXT NOT NULL, data TEXT NOT NULL)')

    def request_analysis(self, ident, request_id):
        ident, request_id = str(UUID(ident)), str(UUID(request_id))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT order_id FROM analysis_requests WHERE request_id=?', (request_id,)).fetchone()
            if previous:
                if previous[0] != ident:
                    raise ProductionError('Analysis ID belongs to a different order')
                return {'accepted': True}
            row = db.execute('SELECT status,analysis_status,preview_status FROM preparation_jobs WHERE order_id=?', (ident,)).fetchone()
            if not row or row[0] != 'awaiting_review' or any(v in {'queued','running','recovering','cancelling'} for v in row[1:]):
                raise ProductionError('Analysis needs prepared materials and no active attempt')
            db.execute('INSERT INTO analysis_requests VALUES (?,?)', (request_id,ident))
            db.execute("UPDATE preparation_jobs SET analysis_status='queued',analysis_request_id=?,analysis_error=NULL WHERE order_id=?",
                       (request_id,ident))
        return {'accepted': True}

    def cancel_analysis(self, ident):
        ident = str(UUID(ident))
        with self.connect() as db:
            db.execute("""UPDATE preparation_jobs SET analysis_status=CASE analysis_status
                WHEN 'queued' THEN 'cancelled' WHEN 'running' THEN 'cancelling'
                WHEN 'recovering' THEN 'cancelling' ELSE analysis_status END WHERE order_id=?""", (ident,))
            row = db.execute('SELECT analysis_status FROM preparation_jobs WHERE order_id=?',(ident,)).fetchone()
        if not row:
            raise ProductionError('Unknown order')
        return {'status': row[0]}

    def cancel_preparation(self, ident):
        ident = str(UUID(ident))
        with self.connect() as db:
            db.execute("""UPDATE preparation_jobs SET status=CASE status
                WHEN 'queued' THEN 'cancelled' WHEN 'running' THEN 'cancelling'
                ELSE status END WHERE order_id=?""", (ident,))
            row = db.execute('SELECT status FROM preparation_jobs WHERE order_id=?',
                             (ident,)).fetchone()
        if not row:
            raise ProductionError('Unknown preparation job')
        return {'status': row[0]}

    def retry_preparation(self, ident, request_id):
        ident, request_id = str(UUID(ident)), str(UUID(request_id))
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS preparation_retries
                (request_id TEXT PRIMARY KEY, order_id TEXT NOT NULL)""")
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT order_id FROM preparation_retries WHERE request_id=?',
                                  (request_id,)).fetchone()
            if previous:
                if previous[0] != ident:
                    raise ProductionError('Retry ID belongs to a different order')
                return {'accepted': True}
            row = db.execute('SELECT status,analysis_status,preview_status FROM preparation_jobs WHERE order_id=?', (ident,)).fetchone()
            if not row or row[0] in {'queued', 'running', 'cancelling'} or any(v in {'queued','running','recovering','cancelling'} for v in row[1:]):
                raise ProductionError('Order is missing or preparation is already active')
            db.execute('INSERT INTO preparation_retries VALUES (?,?)', (request_id, ident))
            db.execute("UPDATE preparation_jobs SET status='queued', attempts=0 WHERE order_id=?", (ident,))
        return {'accepted': True}

    @contextmanager
    def connect(self):
        connection=sqlite3.connect(self.root / 'intake.sqlite3', timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def asset(self, ident, runtime=None):
        if not isinstance(ident, str):
            raise ProductionError('Invalid asset identifier')
        with self.connect() as db:
            row = db.execute('SELECT data FROM assets WHERE id=?', (ident,)).fetchone()
        if not row:
            raise ProductionError('Unknown attachment')
        data = json.loads(row[0])
        if digest(self.root / 'assets' / ident, runtime) != ident:
            raise ProductionError('Attachment changed after upload')
        return data

    def upload(self, name, stream, size):
        if type(size) is not int or not 0 < size <= MAX_UPLOAD:
            raise ProductionError('Attachment must be between 1 byte and 128 MiB')
        if not isinstance(name, str) or not name or len(name) > 180 or any(ord(c)<32 for c in name):
            raise ProductionError('Invalid attachment name')
        suffix = Path(name).suffix.lower()
        if suffix not in {'.png','.jpg','.jpeg','.webp','.mp4','.mov','.webm','.wav','.mp3','.m4a','.ogg'}:
            raise ProductionError('Unsupported media format')
        with tempfile.NamedTemporaryFile(dir=self.root, suffix=suffix) as temp:
            remaining = size
            while remaining:
                chunk = stream.read(min(1024*1024, remaining))
                if not chunk:
                    raise ProductionError('Incomplete upload')
                temp.write(chunk)
                remaining -= len(chunk)
            temp.flush()
            path = Path(temp.name)
            if suffix in {'.png','.jpg','.jpeg','.webp'}:
                from PIL import Image
                with Image.open(path) as im:
                    im.verify()
                kind = 'image'
            else:
                info = json.loads(Runtime(20).run(['ffprobe','-v','error',
                    '-protocol_whitelist','file,pipe','-show_streams','-of','json',str(path)]))
                kinds = {s.get('codec_type') for s in info.get('streams',[])}
                kind = 'video' if 'video' in kinds else 'audio' if 'audio' in kinds else None
                if kind is None:
                    raise ProductionError('No readable audio or video stream')
            ident = digest(path)
            target = self.root / 'assets' / ident
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                existing = db.execute('SELECT data FROM assets WHERE id=?',(ident,)).fetchone()
                if existing:
                    return self.asset(ident)
                used = sum(json.loads(r[0])['bytes'] for r in db.execute('SELECT data FROM assets'))
                if used + size > 2 * 1024**3:
                    raise ProductionError('Local intake storage limit reached (2 GiB)')
                try:
                    os.link(path,target)
                except FileExistsError:
                    if digest(target)!=ident:
                        raise ProductionError('Stored attachment failed integrity verification')
                data = {'id':ident,'name':name,'bytes':size,'kind':kind}
                db.execute('INSERT INTO assets VALUES (?,?)',(ident,json.dumps(data,ensure_ascii=False)))
            return data

    def create(self, data):
        if not isinstance(data,dict) or set(data)-{'request_id','mode','brief','changes','preserve','references','characters','voice'}:
            raise ProductionError('Unknown order fields')
        try:
            ident = str(UUID(data['request_id']))
        except (KeyError, ValueError, TypeError, AttributeError) as exc:
            raise ProductionError('request_id must be a UUID') from exc
        mode = data.get('mode')
        if mode not in MODES:
            raise ProductionError('Choose an explicit production mode')
        texts={}
        for key in ('brief','changes','preserve'):
            text=data.get(key,'')
            if not isinstance(text,str) or len(text)>12000:
                raise ProductionError('Order text is invalid or too long')
            texts[key]=text.strip()
        attachments={}
        for key in ('references','characters'):
            ids=data.get(key,[])
            if not isinstance(ids,list) or len(ids)>12 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):
                raise ProductionError('Invalid attachment list')
            attachments[key]=[self.asset(i) for i in ids]
        voice=self.asset(data['voice']) if data.get('voice') else None
        if voice and voice['kind']!='audio':
            raise ProductionError('Voice order must contain audio')
        if not texts['brief'] and voice is None:
            raise ProductionError('Add a written or recorded order')
        if mode!='new_video' and not any(a['kind']=='video' for a in attachments['references']):
            raise ProductionError('This mode requires the actual reference video')
        if mode in {'face_replace','body_replace'} and not any(a['kind']=='image' for a in attachments['characters']):
            raise ProductionError('Replacement requires character reference images')
        constraints={
            'reference':'Analyze the reference before planning; preserve requested structure, motion and style.',
            'face_replace':'Preserve source timing, shots, action, body, background and audio; change only the specified face region.',
            'body_replace':'Preserve source timing, shots, camera, action and audio; body, occlusion, shadows and revealed background require explicit regional review.',
            'new_video':'Build and review a production plan from this order before generating assets.'}
        order={'id':ident,'revision':1,'mode':mode,**texts,**attachments,'voice':voice,
            'constraint':constraints[mode], 'status':'needs_transcription' if voice else 'needs_planning',
            'budget_usd':0,'generation_authorized':False,'provider_calls':0}
        fingerprint=object_digest(order)
        order['created_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT fingerprint,data FROM orders WHERE id=?',(ident,)).fetchone()
            if row:
                if row[0]!=fingerprint:
                    raise ProductionError('Request ID already belongs to a different order')
                order = json.loads(row[1])
            else:
                db.execute('INSERT INTO orders VALUES (?,?,?)',
                           (ident,fingerprint,json.dumps(order,ensure_ascii=False)))
            if self.enqueue:
                db.execute("INSERT OR IGNORE INTO preparation_jobs (order_id,status) VALUES (?,'queued')",
                           (ident,))
        return order

    def orders(self):
        with self.connect() as db:
            orders = [(json.loads(data), status) for data, status in db.execute(
                'SELECT orders.data, preparation_jobs.status FROM orders LEFT JOIN preparation_jobs '
                'ON orders.id=preparation_jobs.order_id ORDER BY orders.rowid DESC LIMIT 50')]
            analyses = {row[0]: {'status': row[1], 'request_id': row[2], 'error': row[3]}
                for row in db.execute('SELECT order_id,analysis_status,analysis_request_id,analysis_error FROM preparation_jobs')}
        for order, job_status in orders:
            if order['id'] in analyses:
                order['analysis'] = analyses[order['id']]
            fingerprint=object_digest(order)
            receipt=self.root/'preparations'/order['id']/'receipt.json'
            if receipt.is_file():
                data=json.loads(receipt.read_text())
                if data.get('order_sha256')==fingerprint:
                    order['preparation']={'status':data['status'],
                        'reference_count':len(data.get('reference_evidence',[])),
                        'blocker':data.get('blocker')}
            if job_status:
                order.setdefault('preparation', {})['status'] = job_status
            transcript=self.root/'transcripts'/f"{order['id']}.json"
            if order.get('voice') and transcript.is_file():
                data=json.loads(transcript.read_text())
                if data.get('source_sha256')==order['voice']['id']:
                    order['transcript']=data
                    order['status']='needs_transcript_review'
        return [order for order, _ in orders]


def server(root, port, **preparation_options):
    from .controller import PreparationController

    intake = Intake(root, enqueue=True)
    class IntakeServer(HTTPServer):
        def serve_forever(self, poll_interval=0.5):
            try:
                self.controller.thread.start()
                super().serve_forever(poll_interval)
            finally:
                self.controller.close()

        def server_close(self):
            if hasattr(self, 'controller'):
                self.controller.close()
            super().server_close()

    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def response(self, code, value, html=False, content_type=None):
            payload = value if isinstance(value, bytes) else (
                value.encode() if html else json.dumps(value,ensure_ascii=False).encode())
            self.send_response(code)
            self.send_header('Content-Type',content_type or ('text/html; charset=utf-8' if html else 'application/json; charset=utf-8'))
            self.send_header('Content-Length',str(len(payload)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'nonce-"+token+"'; style-src 'unsafe-inline'; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def file_response(self, path, content_type):
            import re
            size = path.stat().st_size
            start, end, code = 0, size - 1, 200
            requested = self.headers.get('Range')
            if requested:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                if not match or not any(match.groups()):
                    return self.response(416, {'error': 'Invalid range'})
                first, last = match.groups()
                if first:
                    start = int(first)
                    end = min(int(last), end) if last else end
                else:
                    start = max(0, size - int(last))
                if not 0 <= start <= end < size:
                    return self.response(416, {'error': 'Invalid range'})
                code = 206
            self.connection.settimeout(15)
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(end - start + 1))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if code == 206:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            with path.open('rb') as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining:
                    data = stream.read(min(65536, remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)

        def allowed(self, mutation=False):
            hosts={f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            host=self.headers.get('Host')
            origin=self.headers.get('Origin')
            return host in hosts and (origin is None or origin=='http://'+host) and (
                not mutation or secrets.compare_digest(self.headers.get('X-Intake-Token',''),token))

        def do_GET(self):
            if not self.allowed():
                return self.response(403,{'error':'Local owner access only'})
            try:
                if self.path == '/':
                    page=Path(__file__).with_name('intake.html').read_text().replace('__SESSION_TOKEN__',token)
                    return self.response(200,page,True)
                if self.path == '/api/health':
                    return self.response(200, {'preparation_running': self.server.controller.thread.is_alive(),
                        'planner_enabled': self.server.controller.planner is not None,
                        'error': self.server.controller.failure})
                if self.path == '/api/orders':
                    return self.response(200,intake.orders())
                from .planning import order_evidence, latest_plan, media_file, review_page, source_file
                parts = urlparse(self.path).path.split('/')
                if len(parts) == 3 and parts[1] == 'review':
                    return self.response(200, review_page(root, parts[2], token), True)
                if len(parts) >= 5 and parts[:3] == ['', 'api', 'orders']:
                    ident = str(UUID(parts[3]))
                    if len(parts) == 5 and parts[4] == 'shots':
                        from .shots import shot_state
                        return self.response(200,shot_state(root,ident))
                    if len(parts) == 7 and parts[4] == 'shots' and parts[6] == 'video':
                        from .shots import shot_file
                        return self.file_response(shot_file(root,ident,parts[5]),'video/mp4')
                    if len(parts) == 5 and parts[4] == 'preview':
                        from .preview import preview_state
                        return self.response(200,preview_state(root,ident))
                    if len(parts) == 6 and parts[4] == 'preview':
                        from .preview import preview_file
                        return self.file_response(preview_file(root,ident,parts[5]),'video/mp4')
                    if len(parts) == 5 and parts[4] == 'evidence':
                        packet = order_evidence(root, ident)
                        packet['latest_plan'] = latest_plan(root, ident, packet['packet_sha256'])
                        return self.response(200, packet)
                    if len(parts) == 6 and parts[4] == 'source':
                        path, content_type = source_file(root, ident, parts[5])
                        return self.file_response(path, content_type)
                    if len(parts) == 6 and parts[4] == 'media':
                        path, kind = media_file(root, ident, int(parts[5]))
                        return self.response(200, path.read_bytes(),
                            content_type='image/jpeg' if kind == 'image' else 'audio/wav')
                self.response(404,{'error':'Not found'})
            except (ProductionError, ValueError, OSError, KeyError, TypeError) as exc:
                self.response(409, {'error': str(exc)})

        def do_POST(self):
            if not self.allowed(True):
                return self.response(403,{'error':'Invalid local request'})
            self.connection.settimeout(30)
            try:
                size=int(self.headers.get('Content-Length','0'))
                url=urlparse(self.path)
                if url.path=='/api/uploads':
                    name=parse_qs(url.query).get('name',[''])[0]
                    return self.response(201,intake.upload(name,self.rfile,size))
                if url.path=='/api/orders' and 0<size<=65536:
                    if not self.server.controller.thread.is_alive():
                        raise ProductionError('Preparation controller is unavailable; restart the local session')
                    order = intake.create(json.loads(self.rfile.read(size)))
                    self.server.controller.ready.set()
                    return self.response(201, order)
                parts = url.path.split('/')
                if len(parts) == 5 and parts[:3] == ['', 'api', 'orders'] and parts[4] == 'shots' and 0 < size <= 2048:
                    from .shots import prepare_shot
                    return self.response(200,prepare_shot(root,parts[3],json.loads(self.rfile.read(size))))
                if len(parts) == 7 and parts[:3] == ['', 'api', 'orders'] and parts[4] == 'shots' and parts[6] == 'review' and 0 < size <= 16384:
                    from .shots import review_shot
                    return self.response(200,review_shot(root,parts[3],parts[5],json.loads(self.rfile.read(size))))
                if len(parts) == 5 and parts[:3] == ['', 'api', 'orders'] and parts[4] == 'preview' and 0 < size <= 1024:
                    if not self.server.controller.thread.is_alive():
                        raise ProductionError('Controller is unavailable')
                    from .preview import request_preview
                    result=request_preview(root,parts[3],json.loads(self.rfile.read(size)))
                    self.server.controller.ready.set()
                    return self.response(200,result)
                if len(parts) == 6 and parts[:3] == ['', 'api', 'orders'] and parts[4:] == ['preview','cancel'] and size == 0:
                    from .preview import cancel_preview
                    return self.response(200,cancel_preview(root,parts[3]))
                if len(parts) == 5 and parts[:3] == ['', 'api', 'orders'] and parts[4] == 'analyze' and 0 < size <= 1024:
                    if self.server.controller.planner is None or not self.server.controller.thread.is_alive():
                        raise ProductionError('Visual planner is not configured or controller is unavailable')
                    data = json.loads(self.rfile.read(size))
                    result = intake.request_analysis(parts[3], data['request_id'])
                    self.server.controller.ready.set()
                    return self.response(200, result)
                if len(parts) == 6 and parts[:3] == ['', 'api', 'orders'] and parts[4:] == ['analysis','cancel'] and size == 0:
                    return self.response(200, intake.cancel_analysis(parts[3]))
                if len(parts) == 5 and parts[:3] == ['', 'api', 'orders'] and parts[4] == 'retry' and 0 < size <= 1024:
                    if not self.server.controller.thread.is_alive():
                        raise ProductionError('Preparation controller is unavailable; restart the local session')
                    data = json.loads(self.rfile.read(size))
                    result = intake.retry_preparation(parts[3], data['request_id'])
                    self.server.controller.ready.set()
                    return self.response(200, result)
                if len(parts) == 5 and parts[:3] == ['', 'api', 'orders'] and parts[4] == 'plan' and 0 < size <= 1048576:
                    from .planning import save_plan
                    return self.response(201, save_plan(root, parts[3], json.loads(self.rfile.read(size))))
                if len(parts) == 5 and parts[:3] == ['', 'api', 'orders'] and parts[4] == 'plan-review' and 0 < size <= 65536:
                    from .planning import save_plan_review
                    return self.response(201, save_plan_review(root, parts[3], json.loads(self.rfile.read(size))))
                if len(parts) == 5 and parts[:3] == ['', 'api', 'orders'] and parts[4] == 'cancel' and size == 0:
                    return self.response(200, intake.cancel_preparation(parts[3]))
                raise ProductionError('Invalid request size or path')
            except (ProductionError,ValueError,OSError,KeyError,TypeError) as exc:
                self.response(400,{'error':str(exc)})
    http = IntakeServer(('127.0.0.1', port), Handler)
    try:
        http.controller = PreparationController(intake, **preparation_options)
    except BaseException:
        HTTPServer.server_close(http)
        raise
    return http


if __name__=='__main__':
    p=argparse.ArgumentParser(description='Local owner intake; no generation or public access')
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--port',type=int,default=18117)
    p.add_argument('--preparation-timeout', type=float, default=300)
    p.add_argument('--speech-python', type=Path)
    p.add_argument('--speech-model-path', type=Path)
    p.add_argument('--speech-model', choices=['tiny', 'small'], default='small')
    p.add_argument('--planner-codex', type=Path)
    p.add_argument('--analysis-timeout', type=float, default=180)
    a=p.parse_args()
    import signal

    def stop(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    from .analysis import CodexPlanner
    planner = CodexPlanner(a.planner_codex) if a.planner_codex else None
    with server(a.root, a.port, timeout=a.preparation_timeout, python=a.speech_python,
                planner=planner, analysis_timeout=a.analysis_timeout,
                model_path=a.speech_model_path, model=a.speech_model) as http:
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            pass
