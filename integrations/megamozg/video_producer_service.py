"""Private Unix-socket producer. Web input can select only preconfigured tasks.

Each read runs in an isolated child with a 10-second timeout. One request at a
time; no renderer, model dispatch, database migration or account credentials.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys

MAX_RESPONSE=46*1024*1024


def worker(config,request):
    from production.pult_link import collect
    from video_scene_producer import scene_producer
    if set(request)!={'task','revision','kind'}:raise ValueError('invalid_request')
    entry=config['orders'][request['task']];link=entry['binding']
    # Session, assignment and current task revision are checked by the web
    # routes before and after this RPC. The producer admits only that OS UID
    # and this fixed configuration; it must not open the web system's WAL DB.
    kind=request['kind']
    if kind=='metadata':
        if request['revision'] is not None:raise ValueError('invalid_revision')
        result=collect(entry['root'],link)
    else:
        result=scene_producer(entry['root'],link,entry['request_id'],entry['revisions'])(link,request['revision'],kind)
        if 'data' in result:result['data_base64']=base64.b64encode(result.pop('data')).decode()
    return result


def client(path,link,revision,kind):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(12);sock.connect(str(path))
        sock.sendall(json.dumps({'task':link['task_id'],'revision':revision,'kind':kind}).encode()+b'\n')
        chunks=[];size=0
        while True:
            part=sock.recv(1024*1024)
            if not part:break
            size+=len(part)
            if size>MAX_RESPONSE:raise ValueError('response_too_large')
            chunks.append(part)
    value=json.loads(b''.join(chunks))
    if set(value)!= {'ok','result'} or value['ok'] is not True:raise ValueError('producer_unavailable')
    result=value['result']
    if 'data_base64' in result:result['data']=base64.b64decode(result.pop('data_base64'),validate=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['serve','worker']);parser.add_argument('--config',type=Path,required=True);args=parser.parse_args()
    config=json.loads(args.config.read_text())
    if args.action=='worker':
        request=json.loads(sys.stdin.buffer.read(2049))
        print(json.dumps(worker(config,request),allow_nan=False));return
    path=Path(config['socket'])
    if path.exists():raise RuntimeError('existing_socket_requires_reconciliation')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        server.bind(str(path));os.chown(path,0,config['pult_gid']);os.chmod(path,0o660);server.listen(4);server.settimeout(1)
        try:
            while True:
                try:conn,_=server.accept()
                except socket.timeout:continue
                with conn:
                    conn.settimeout(3)
                    _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                    if uid!=config['pult_uid']:continue
                    raw=bytearray()
                    try:
                        while len(raw)<=2048 and not raw.endswith(b'\n'):
                            part=conn.recv(1)
                            if not part:break
                            raw.extend(part)
                        if len(raw)>2048 or not raw.endswith(b'\n'):raise ValueError('request_too_large')
                        bootstrap='import sys;sys.path[:0]=[sys.argv.pop(1),sys.argv.pop(1)];from video_producer_service import main;main()'
                        source=Path(__file__).resolve().parents[2]
                        out=subprocess.run([sys.executable,'-I','-c',bootstrap,str(source),str(Path(__file__).resolve().parent),'worker','--config',str(args.config)],input=bytes(raw),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10,check=True).stdout
                        if len(out)>MAX_RESPONSE:raise ValueError('output_too_large')
                        packet={'ok':True,'result':json.loads(out)}
                    except Exception:packet={'ok':False,'result':None}
                    try:conn.sendall(json.dumps(packet).encode())
                    except OSError:pass
        finally:path.unlink(missing_ok=True)


if __name__=='__main__':main()
