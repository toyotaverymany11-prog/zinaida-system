"""Cooperative project registry. Not an access-control system or background agent.

Every write uses a revision guard and an OS lock. Expired claims still reserve
their scope until the previous operation is reconciled and explicitly released.
"""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import tempfile
import time


def overlap(a, b):
    return a == b or a.startswith(b.rstrip('/')+'/') or b.startswith(a.rstrip('/')+'/')


def change(state, request, now):
    if request['expected_revision'] != state['revision']:
        raise ValueError('revision_conflict')
    record = request['record']
    required = {'id','owner','status','scopes','branch','checkpoint','next_step','evidence','lease_until'}
    if set(record) != required or record['status'] not in {'working','paused','released','observed'}:
        raise ValueError('invalid_record')
    if not all(isinstance(record[k],str) and record[k] for k in ('id','owner','branch','checkpoint','next_step')):
        raise ValueError('invalid_record')
    if not isinstance(record['scopes'],list) or not record['scopes']:
        raise ValueError('missing_scopes')
    for scope in record['scopes']:
        if (not isinstance(scope,str) or not scope.startswith(('repo:/','server:/','service:/'))
                or any(x in {'','.','..'} for x in scope.split(':/',1)[1].split('/')[1:])):
            raise ValueError('invalid_scope')
    if not isinstance(record['evidence'],list) or not all(isinstance(x,str) for x in record['evidence']):
        raise ValueError('invalid_evidence')
    if type(record['lease_until']) not in (int,float) or not math.isfinite(record['lease_until']) or not 0 <= record['lease_until'] <= now+7200:
        raise ValueError('invalid_lease')
    previous = state['records'].get(record['id'])
    if previous and previous['owner'] != record['owner']:
        raise ValueError('owner_mismatch')
    # Observed records reserve scope too, but do not claim the other chat adopted
    # this protocol. Release requires reading its actual outstanding operations.
    if record['status'] != 'released':
        for key, other in state['records'].items():
            if key != record['id'] and other['status'] != 'released':
                if any(overlap(a,b) for a in record['scopes'] for b in other['scopes']):
                    raise ValueError('scope_conflict:'+key)
    record = dict(record, updated_at=now)
    return {'revision':state['revision']+1,'records':dict(state['records'],**{record['id']:record})}


def update(root, request):
    root=Path(root);root.mkdir(mode=0o700,parents=True,exist_ok=True)
    with (root/'registry.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=root/'registry.json'
        state=json.loads(path.read_text()) if path.exists() else {'revision':0,'records':{}}
        result=change(state,request,time.time())
        fd,name=tempfile.mkstemp(dir=root,prefix='.registry-')
        try:
            with os.fdopen(fd,'w') as out:
                json.dump(result,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
            os.replace(name,path)
            d=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(d)
            finally:os.close(d)
        finally:
            if os.path.exists(name):os.unlink(name)
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['read','update']);p.add_argument('--root',required=True);args=p.parse_args()
    if args.action=='read':
        result=json.loads((Path(args.root)/'registry.json').read_text())
        for record in result['records'].values():
            record['lease_expired']=record['lease_until']<time.time()
    else:
        import sys
        result=update(args.root,json.load(sys.stdin))
    print(json.dumps(result,ensure_ascii=False,indent=2))
