"""Validate a research ledger without treating URL count as reading evidence."""
import argparse,json,sys
from urllib.parse import urlsplit,urlunsplit

def canonical(url):
    p=urlsplit(url);path=p.path.rstrip('/')
    if path.endswith('.md'):path=path[:-3]
    return urlunsplit((p.scheme.lower(),p.netloc.lower().removeprefix('www.'),path,'',''))

def audit(rows,minimum=100):
    seen=set();errors=[];read=0
    for r in rows:
        ident=r.get('canonical_id') or canonical(r.get('url',''))
        if ident in seen:errors.append('duplicate:'+ident)
        seen.add(ident)
        if not r.get('url','').startswith('https://'):errors.append('invalid_url:'+str(r.get('id')))
        if r.get('status')=='read':
            if not r.get('note') or not r.get('accessed') or not r.get('read_scope'):
                errors.append('missing_read_evidence:'+str(r.get('id')))
            else:read+=1
    if read<minimum:errors.append(f'insufficient:{read}/{minimum}')
    return {'read':read,'unique':len(seen),'minimum':minimum,'valid':not errors,'errors':errors}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('ledger');p.add_argument('--minimum',type=int,default=100)
    a=p.parse_args();result=audit(json.load(open(a.ledger)),a.minimum)
    print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['valid'] else 1)

