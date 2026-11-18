"""Explicit bounded public-weight download; root must separately authorize execution."""
import argparse,hashlib,json,os,signal,time
from pathlib import Path

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(8*1024*1024),b''):h.update(data)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--lock',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--deadline',type=float,required=True);a=p.parse_args()
 remaining=int(a.deadline-time.time())
 if not 1<=remaining<=1800:raise RuntimeError('Finite current deadline required')
 signal.alarm(remaining);os.environ['HF_HUB_DISABLE_XET']='1'
 from huggingface_hub import hf_hub_download
 config=json.loads(a.lock.read_text());a.destination.mkdir(parents=True,exist_ok=True)
 for row in config['files']:
  if time.time()>=a.deadline:raise RuntimeError('Download deadline exhausted')
  filename=Path(hf_hub_download(config['repo_id'],row['path'],revision=config['revision'],local_dir=str(a.destination)))
  if filename.stat().st_size!=row['bytes'] or digest(filename)!=row['sha256']:raise RuntimeError('Public weight/config hash mismatch: '+row['path'])
 result={'status':'all_model_files_verified','model_revision':config['revision'],'lock_sha256':digest(a.lock),'verified_files':len(config['files']),'bytes':config['total_required_bytes']}
 (a.destination/'verified.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
