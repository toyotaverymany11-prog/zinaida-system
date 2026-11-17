"""Owner-local order intake. Stores briefs and media; never starts generation.

This is the intake boundary of the future controller, not a competing job queue.
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
    def __init__(self, root: Path):
        self.root = root.resolve()
        (self.root / 'assets').mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, data TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        connection=sqlite3.connect(self.root / 'intake.sqlite3', timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def asset(self, ident):
        if not isinstance(ident, str):
            raise ProductionError('Invalid asset identifier')
        with self.connect() as db:
            row = db.execute('SELECT data FROM assets WHERE id=?', (ident,)).fetchone()
        if not row:
            raise ProductionError('Unknown attachment')
        data = json.loads(row[0])
        if digest(self.root / 'assets' / ident) != ident:
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
                return json.loads(row[1])
            db.execute('INSERT INTO orders VALUES (?,?,?)',(ident,fingerprint,json.dumps(order,ensure_ascii=False)))
        return order

    def orders(self):
        with self.connect() as db:
            orders=[json.loads(r[0]) for r in db.execute('SELECT data FROM orders ORDER BY rowid DESC LIMIT 50')]
        for order in orders:
            transcript=self.root/'transcripts'/f"{order['id']}.json"
            if order.get('voice') and transcript.is_file():
                data=json.loads(transcript.read_text())
                if data.get('source_sha256')==order['voice']['id']:
                    order['transcript']=data
                    order['status']='needs_transcript_review'
        return orders


def server(root, port):
    intake=Intake(root)
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def response(self, code, value, html=False):
            payload=value.encode() if html else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(payload)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'nonce-"+token+"'; style-src 'unsafe-inline'; connect-src 'self'; media-src blob:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def allowed(self, mutation=False):
            hosts={f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            host=self.headers.get('Host')
            origin=self.headers.get('Origin')
            return host in hosts and (origin is None or origin=='http://'+host) and (
                not mutation or secrets.compare_digest(self.headers.get('X-Intake-Token',''),token))

        def do_GET(self):
            if not self.allowed():
                return self.response(403,{'error':'Local owner access only'})
            if self.path=='/':
                page=Path(__file__).with_name('intake.html').read_text().replace('__SESSION_TOKEN__',token)
                return self.response(200,page,True)
            if self.path=='/api/orders':
                return self.response(200,intake.orders())
            self.response(404,{'error':'Not found'})

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
                    return self.response(201,intake.create(json.loads(self.rfile.read(size))))
                raise ProductionError('Invalid request size or path')
            except (ProductionError,ValueError,OSError,KeyError,TypeError) as exc:
                self.response(400,{'error':str(exc)})
    return HTTPServer(('127.0.0.1',port),Handler)


if __name__=='__main__':
    p=argparse.ArgumentParser(description='Local owner intake; no generation or public access')
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--port',type=int,default=18117)
    a=p.parse_args()
    server(a.root,a.port).serve_forever()
