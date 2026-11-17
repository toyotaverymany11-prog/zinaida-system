"""One bounded subscription video attempt, with durable no-repeat receipts.

Operator-only. Uses the selected Hermes profile's existing OAuth grant, never
XAI_API_KEY. No account sharing, storage_options, renderer or automatic fallback.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

BASE='https://api.x.ai/v1'


def save(path,value):
    temp=path.with_suffix('.new')
    with temp.open('w') as file:
        json.dump(value,file,ensure_ascii=False,indent=2);file.flush();os.fsync(file.fileno())
    os.replace(temp,path)


def credentials(auth):
    entry=json.loads(Path(auth).read_text()).get('providers',{}).get('xai-oauth',{})
    token=entry.get('tokens',{}).get('access_token')
    if not isinstance(token,str) or not token:raise ValueError('subscription_reauthentication_required')
    return token


def api(token,path,payload=None):
    headers={'Authorization':'Bearer '+token,'User-Agent':'Hermes-Agent/video-subscription-qualification'}
    if payload is not None:headers['Content-Type']='application/json'
    req=urllib.request.Request(BASE+path,headers=headers,data=None if payload is None else json.dumps(payload).encode(),method='GET' if payload is None else 'POST')
    with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)


def submit(directory,auth,prompt,*,duration=3):
    if not isinstance(prompt,str) or not 1<=len(prompt)<=4000 or type(duration) is not int or not 1<=duration<=5:raise ValueError('invalid_bounded_prompt')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    receipt=directory/'attempt.json'
    payload={'model':'grok-imagine-video','prompt':prompt,'duration':duration,'aspect_ratio':'16:9','resolution':'720p'}
    signature=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    # Exclusive creation is the dispatch lock and survives process termination.
    try:
        with receipt.open('x') as file:json.dump({'state':'reserved','payload_sha256':signature,'requests_sent':0},file)
    except FileExistsError:
        prior=json.loads(receipt.read_text())
        if prior.get('payload_sha256')!=signature:raise ValueError('attempt_input_changed')
        return prior
    token=credentials(auth)
    state={'state':'submitting','payload_sha256':signature,'requests_sent':1,'route':'saved_xai_oauth_only','paid_api_key_used':False,'started_at':time.time()};save(receipt,state)
    try:
        response=api(token,'/videos/generations',payload)
        request_id=response.get('request_id')
        from uuid import UUID
        if not isinstance(request_id,str) or str(UUID(request_id))!=request_id:raise ValueError('missing_request_id')
        state.update(state='submitted',request_id=request_id)
    except urllib.error.HTTPError as error:state.update(state='rejected',http=error.code)
    except Exception as error:state.update(state='unknown',error_type=type(error).__name__)
    save(receipt,state);return state


def resume(directory,auth,*,timeout=240):
    if not 1<=timeout<=240:raise ValueError('invalid_timeout')
    directory=Path(directory);receipt=directory/'attempt.json';state=json.loads(receipt.read_text())
    if state['state']=='verified':
        if hashlib.sha256((directory/'video.mp4').read_bytes()).hexdigest()!=state['sha256']:raise ValueError('saved_video_changed')
        return state
    if state['state']!='submitted':raise ValueError('outcome_requires_reconciliation_no_repeat')
    token=credentials(auth);deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        response=api(token,'/videos/'+state['request_id']);status=response.get('status')
        if status in {'failed','error','expired','cancelled'}:
            state.update(state='failed',provider_status=status);save(receipt,state);return state
        if status=='done' and isinstance(response.get('video'),dict):break
        time.sleep(min(5,max(0,deadline-time.monotonic())))
    else:return dict(state,poll_deadline_reached=True)
    url=response['video'].get('url','');parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname:raise ValueError('invalid_download_url')
    # Credential is deliberately not attached to the provider-returned media URL.
    temporary=directory/'video.part';total=0
    with urllib.request.urlopen(url,timeout=25) as source,temporary.open('wb') as output:
        while True:
            block=source.read(1024*1024)
            if not block:break
            total+=len(block)
            if total>32*1024*1024:raise ValueError('media_too_large')
            output.write(block)
    subprocess.run(['ffmpeg','-v','error','-i',str(temporary),'-f','null','-'],check=True,capture_output=True,timeout=30)
    probe=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(temporary)],check=True,capture_output=True,text=True,timeout=15)
    info=json.loads(probe.stdout);stream=next(s for s in info['streams'] if s['codec_type']=='video')
    out=directory/'video.mp4';os.replace(temporary,out)
    state.update(state='verified',sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=total,duration=info['format']['duration'],width=stream['width'],height=stream['height'],finished_video_accepted=False)
    save(receipt,state);return state


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['submit','resume']);p.add_argument('--directory',type=Path,required=True);p.add_argument('--auth',type=Path,required=True);p.add_argument('--prompt');p.add_argument('--duration',type=int,default=3);a=p.parse_args()
    print(json.dumps(submit(a.directory,a.auth,a.prompt,duration=a.duration) if a.action=='submit' else resume(a.directory,a.auth),ensure_ascii=False))
