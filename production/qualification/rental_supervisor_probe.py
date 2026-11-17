"""Finite root/systemd probe against a loopback fake provider; never uses credentials."""
import argparse
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

from production.core import read_json,write_json
from production.rental_guard import launch,guard_status

def main(root):
    root.mkdir(parents=True,exist_ok=True)
    now=time.time();ident='probe_'+uuid.uuid4().hex[:12]
    pod={'id':ident,'name':'zina-video-'+uuid.uuid4().hex,'createdAt':datetime.fromtimestamp(now,timezone.utc).isoformat()}
    original=dict(pod);calls=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            calls.append('GET');self.send_response(200 if pod else 404);self.end_headers()
            if pod:self.wfile.write(json.dumps(pod).encode())
        def do_DELETE(self):
            calls.append('DELETE');pod.clear();self.send_response(204);self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    lease={'schema_version':1,'provider':'runpod','resource':original,'budget_usd':1,
        'hourly_total_usd':1,'fixed_cost_usd':0,'created_at_epoch':now,'terminate_at_epoch':now+8,
        'cleanup_allowance_seconds':10,'termination_authorized':True,'shared_resource':False}
    path=root/'lease.json';write_json(path,lease);unit=None
    report={'simulation':True,'real_runpod_mutations':0,'deadline':lease['terminate_at_epoch']}
    def wait_for(predicate,seconds=15):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            state=root/'state'/ident/'guard.json'
            if state.exists():
                data=read_json(state)
                if predicate(data):return data
            time.sleep(.05)
        raise RuntimeError('Supervisor did not reach expected state')
    try:
        result=launch(path,root/'state',Path(sys.executable),
            simulation_url=f'http://127.0.0.1:{server.server_port}/v2',supervisor='systemd')
        unit=result['unit'];first=wait_for(lambda r:r['phase']=='watching',5)
        report['first_pid']=first['pid'];report['simulation_ready']=guard_status(root/'state',lease)['ready']
        os.kill(first['pid'],signal.SIGKILL)
        second=wait_for(lambda r:r['phase']=='watching' and r['pid']!=first['pid'],5)
        report['replacement_pid']=second['pid'];report['restart_preserved_deadline']=second['terminate_at_epoch']==lease['terminate_at_epoch']
        end=wait_for(lambda r:r['phase']=='finished')
        receipt=read_json(root/'state'/ident/'cleanup.json')
        report.update(cleanup=receipt['status'],provider_absence_confirmed=receipt['provider_absence_confirmed'],calls=calls)
        assert report['restart_preserved_deadline'] and not report['simulation_ready']
        assert receipt['provider_absence_confirmed'] and calls.count('DELETE')==1
        report['passed']=True
    finally:
        if unit:
            subprocess.run(['systemctl','stop',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
            report['unit_active']=subprocess.run(['systemctl','is-active','--quiet',unit],timeout=5).returncode==0
            report['unit']=unit
        server.shutdown();server.server_close();write_json(root/'report.json',report)
    print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output)
