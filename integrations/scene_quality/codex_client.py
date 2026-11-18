"""Existing ChatGPT subscription, isolated model turn, durable stdout on failures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def generate(folder, prompt_file, schema_file, *, executable='/usr/local/bin/codex', model='gpt-6.1-sol', timeout=160):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    prompt=Path(prompt_file).read_bytes();schema=Path(schema_file).read_bytes()
    key={'prompt_sha256':hashlib.sha256(prompt).hexdigest(),'schema_sha256':hashlib.sha256(schema).hexdigest(),'model':model}
    marker=folder/'attempt.json';output=folder/'response.json'
    if marker.exists():
        prior=json.loads(marker.read_text())
        if prior['input']!=key:raise RuntimeError('Input changed under same request')
        if prior['status']=='done':return json.loads(output.read_text())
        raise RuntimeError('Inspect saved events before any retry')
    rec={'status':'submitting','input':key,'auth_route':'existing_chatgpt_login','paid_fallback':False}
    marker.write_text(json.dumps(rec,indent=2))
    rules=folder/'instructions.txt';rules.write_text('You are an isolated production analyst. Use only supplied text. '
        'Never use tools, files, network, shell or other agents. Return JSON only. '
        'Distinguish observed input, proposals and unknowns. Never grant artistic approval.')
    args=[executable,'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check',
          '--sandbox','read-only','-C',str(folder),'-m',model,'--output-schema',str(Path(schema_file).resolve()),
          '--output-last-message',str(output.resolve()),'--json']
    config={'project_doc_max_bytes':'0','agents.enabled':'false','web_search':'"disabled"','mcp_servers':'{}',
            'model_reasoning_effort':'"low"','forced_login_method':'"chatgpt"',
            'plugins._default.enabled':'false','apps._default.enabled':'false','skills.bundled.enabled':'false',
            'skills.include_instructions':'false','model_instructions_file':json.dumps(str(rules.resolve()))}
    for k,v in config.items():args+=['-c',k+'='+v]
    for feature in ['hooks','apps','shell_tool','unified_exec','multi_agent','skill_search']:args+=['--disable',feature]
    args+=['-']
    env={k:v for k,v in os.environ.items() if k in ['PATH','HOME','LANG','TMPDIR']}
    with (folder/'events.jsonl').open('wb') as out,(folder/'stderr.log').open('wb') as err:
        try:
            r=subprocess.run(args,input=prompt,stdout=out,stderr=err,cwd=folder,env=env,timeout=timeout)
        except subprocess.TimeoutExpired:
            rec['status']='timeout_inspect_events';marker.write_text(json.dumps(rec,indent=2));raise
    events=[]
    for line in (folder/'events.jsonl').read_text().splitlines():
        if line.strip():events.append(json.loads(line))
    if r.returncode or not any(e.get('type')=='turn.completed' for e in events):
        rec.update(status='failed_saved_events',exit_code=r.returncode,
                   errors=[e.get('error',e.get('message')) for e in events if e.get('type') in ['error','turn.failed']])
        marker.write_text(json.dumps(rec,indent=2));raise RuntimeError('Model turn failed; events preserved')
    if any(e.get('item',{}).get('type') not in ['agent_message','reasoning','error'] for e in events if 'item' in e):
        rec['status']='unexpected_tool_activity';marker.write_text(json.dumps(rec,indent=2));raise RuntimeError(rec['status'])
    result=json.loads(output.read_text());rec.update(status='done',output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        tool_calls=0,usage=next(e.get('usage') for e in reversed(events) if e.get('type')=='turn.completed'))
    marker.write_text(json.dumps(rec,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--prompt',required=True);p.add_argument('--schema',required=True)
    p.add_argument('--model',default='gpt-6.1-sol');a=p.parse_args()
    r=generate(a.folder,a.prompt,a.schema,model=a.model);print(json.dumps({'status':'done','keys':list(r)}))
