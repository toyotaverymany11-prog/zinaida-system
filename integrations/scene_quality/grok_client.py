"""Finite Grok subscription turn through its documented CLI proxy; never an API key."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def generate(folder, prompt, model='grok-4.7', max_tokens=6000):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    identity={'model':model,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'max_tokens':max_tokens}
    marker=folder/'receipt.json';output=folder/'response.json'
    if marker.exists():
        rec=json.loads(marker.read_text())
        if rec['input']!=identity:raise RuntimeError('Request input changed')
        if rec['status']=='done':return json.loads(output.read_text())
        raise RuntimeError('Reconcile saved stream before any repeat')
    if model not in ['grok-4.7','grok-4.6'] or not 1<=len(prompt)<=30000 or not 16<=max_tokens<=8000:
        raise ValueError('Request outside preflight bounds')
    auth=json.loads(Path('/root/.hermes/auth.json').read_text())['providers']['xai-oauth']
    if auth.get('base_url','').rstrip('/')!='https://cli-chat-proxy.grok.com/v1':
        raise RuntimeError('Existing subscription route changed')
    # Use the installed Hermes provider's own compatibility headers, unchanged.
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('existing_xai_http','/usr/local/lib/hermes-agent/tools/xai_http.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    headers=helper.hermes_grok_cli_headers()
    headers.update({'Authorization':'Bearer '+auth['tokens']['access_token'],
                    'Content-Type':'application/json','x-grok-model-override':model})
    body={'model':model,'stream':True,'max_tokens':max_tokens,'response_format':{'type':'json_object'},
          'messages':[{'role':'system','content':'You are an isolated production analyst. '
            'Use only supplied input. Never call tools or execute actions. '
            'Return JSON only. Do not claim to see images or hear audio that were not supplied. '
            'Never grant artistic or publication approval.'},{'role':'user','content':prompt}]}
    rec={'status':'submitting_unknown_until_reconciled','input':identity,
         'route':'existing_xai_oauth_subscription_cli_proxy','paid_fallback':False,'created_at':time.time()}
    marker.write_text(json.dumps(rec,indent=2))
    request=urllib.request.Request('https://cli-chat-proxy.grok.com/v1/chat/completions',
        data=json.dumps(body,ensure_ascii=False).encode(),headers=headers)
    chunks=[];finished=False;finish_reason=None;usage=None;limit=time.monotonic()+150;count=0
    try:
        with urllib.request.build_opener(NoRedirect).open(request,timeout=25) as response,(folder/'stream.jsonl').open('wb') as saved:
            rec['provider_request_id']=response.headers.get('x-request-id');marker.write_text(json.dumps(rec,indent=2))
            for line in response:
                count+=len(line)
                if time.monotonic()>limit or count>2*1024*1024:raise TimeoutError('Bounded stream exceeded')
                saved.write(line);saved.flush()
                if not line.startswith(b'data:'):continue
                part=line[5:].strip()
                if part==b'[DONE]':finished=True;break
                a=json.loads(part)
                if a.get('usage'):usage=a['usage']
                for choice in a.get('choices',[]):
                    delta=choice.get('delta',{})
                    if delta.get('tool_calls'):raise RuntimeError('Unexpected tool action')
                    content=delta.get('content')
                    if isinstance(content,str):chunks.append(content)
                    if choice.get('finish_reason'):finish_reason=choice['finish_reason']
        (folder/'text.txt').write_text(''.join(chunks))
        if not finished or finish_reason not in ['stop','eos']:raise RuntimeError('Incomplete model turn')
        result=json.loads(''.join(chunks));output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
        rec.update(status='done',usage=usage,tool_calls=0,output_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
        marker.write_text(json.dumps(rec,indent=2));return result
    except Exception as e:
        rec.update(status='failed_saved_stream',error_type=type(e).__name__,http_status=getattr(e,'code',None))
        marker.write_text(json.dumps(rec,indent=2));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--prompt',required=True)
    p.add_argument('--model',default='grok-4.7');a=p.parse_args()
    r=generate(a.folder,Path(a.prompt).read_text(),a.model);print(json.dumps({'status':'done','keys':list(r)}))
