"""Emit actual, numbered source excerpts and record their precise reading scope."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).parent

def excerpt(row,limit):
 lines=Path(row['local_path']).read_text().splitlines()
 # Find a substantive contract section, avoiding badge tables and import lists.
 terms=re.compile(r'quality|review|limitation|architect|pipeline|workflow|synchron|audio|character|continuity|retry|budget|failure|reference|render|voice|conditioning|select',re.I)
 if row['path'].endswith(('.py','.ts')):
  anchors=[i for i,l in enumerate(lines) if re.search(r'^(?:    )?(?:async )?def |^(?:export )?(?:async )?function |^class ',l) and terms.search(l)]
  start=anchors[0] if anchors else next((i for i,l in enumerate(lines) if len(l.strip())>30 and not l.startswith(('import ','from '))),0)
 else:
  anchors=[i for i,l in enumerate(lines) if l.startswith(('# ', '## ', '### ')) and terms.search(l)]
  start=next((i for i in anchors if i>4),anchors[0] if anchors else 0)
 chosen=[];chars=0
 for i in range(start,len(lines)):
  if chars+len(lines[i])>limit and chosen:break
  chosen.append((i+1,lines[i]));chars+=len(lines[i])+1
 return chosen,len(lines)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('start',type=int);p.add_argument('end',type=int);p.add_argument('--chars',type=int,default=1400);a=p.parse_args()
 rows=json.loads((ROOT/'ledger.json').read_text())
 for row in rows[a.start-1:a.end]:
  if row['status']=='unavailable':print(row['id'],'UNAVAILABLE',row['error']);continue
  pairs,total=excerpt(row,a.chars)
  row['emitted_scope']={'lines':[pairs[0][0],pairs[-1][0]],'total_lines':total,'purpose':'relevant architecture, capability or production contract section'}
  print('\n'+row['id']+' '+row['repo']+' '+row['path']+f' [lines {pairs[0][0]}-{pairs[-1][0]} of {total}]')
  print('\n'.join(f'{n}: {l}' for n,l in pairs))
 (ROOT/'ledger.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
