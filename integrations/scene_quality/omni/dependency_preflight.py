"""Actual dependency imports before copying public weights or loading a model."""
import argparse,hashlib,importlib,importlib.metadata,json,os,re,shutil,signal,sys
from pathlib import Path

def validate_lock(path):
 path=Path(path);d=json.loads(path.read_text());seen=set()
 if not re.fullmatch('[a-f0-9]{40}',d['revision']):raise ValueError('Invalid revision')
 for row in d['files']:
  n=row['path']
  if Path(n).name!=n or n in seen or type(row['bytes']) is not int or row['bytes']<=0 or not re.fullmatch('[a-f0-9]{64}',row['sha256']):raise ValueError('Invalid public model file lock')
  seen.add(n)
 if sum(r['bytes'] for r in d['files'])!=d['total_required_bytes']:raise ValueError('Lock byte total mismatch')
 return {'lock_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'model_revision':d['revision'],'files':len(d['files']),'shards':sum(r['path'].endswith('.safetensors') for r in d['files']),'total_expected_bytes':d['total_required_bytes']}

def collect(require_cuda=False,requirements=None):
 os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN']='1'
 out={'status':'checking_dependencies','actual_python':sys.executable,'python_version':sys.version.split()[0],'checks':{},'errors':[],'weights_loaded':False,'inference_started':False,'network_requested':False,'artistic_approval':False}
 modules={'torch':'torch','torchvision':'torchvision','torchaudio':'torchaudio','av':'av','soundfile':'soundfile','librosa':'librosa','accelerate':'accelerate','qwen-omni-utils':'qwen_omni_utils','transformers':'transformers','safetensors':'safetensors'}
 for package,name in modules.items():
  try:
   m=importlib.import_module(name);row={'imported':True,'version':importlib.metadata.version(package)}
   if name=='transformers':
    for attr in ['Qwen2_5OmniForConditionalGeneration','Qwen2_5OmniProcessor']:row[attr]=getattr(m,attr).__name__
   if name=='qwen_omni_utils':
    if not callable(getattr(m,'process_mm_info',None)):raise RuntimeError('process_mm_info missing')
    row['process_mm_info']=True
   if name=='torch':
    row.update(cuda_build=m.version.cuda,cuda_available=m.cuda.is_available())
    if require_cuda and not row['cuda_available']:raise RuntimeError('CUDA required on evaluator')
   out['checks'][package]=row
  except TimeoutError:raise
  except Exception as e:
   out['checks'][package]={'imported':False,'error_type':type(e).__name__,'error':str(e)[:500]};out['errors'].append(package+': '+type(e).__name__)
 trio=[out['checks'].get(n,{}) for n in ['torch','torchaudio']]
 if all(r.get('imported') for r in trio):
  v=[r['version'].split('+')[0].split('.')[:2] for r in trio]
  if v[0]!=v[1]:out['errors'].append('torch_torchaudio_release_series_mismatch')
  tags=[r['version'].split('+',1)[1] if '+' in r['version'] else None for r in trio]
  if all(t and t.startswith('cu') for t in tags) and tags[0]!=tags[1]:out['errors'].append('torch_torchaudio_cuda_wheel_tag_mismatch')
 if requirements:
  for line in Path(requirements).read_text().splitlines():
   if '==' not in line or line.lstrip().startswith('#'):continue
   n,expected=line.strip().split('==',1)
   try:actual=importlib.metadata.version(n)
   except importlib.metadata.PackageNotFoundError:actual=None
   if actual!=expected:out['errors'].append(f'pin_mismatch:{n}:{actual}:{expected}')
 for n in ['ffmpeg','ffprobe']:
  out['checks'][n]={'path':shutil.which(n)}
  if not shutil.which(n):out['errors'].append(n+'_missing')
 out['status']='dependencies_ready' if not out['errors'] else 'dependency_preflight_failed';return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--require-cuda',action='store_true');p.add_argument('--requirements',type=Path,default=Path(__file__).with_name('requirements.txt'));p.add_argument('--lock',type=Path,default=Path(__file__).with_name('model.lock.json'));p.add_argument('--timeout-seconds',type=int,default=45);a=p.parse_args()
 if not 1<=a.timeout_seconds<=120:raise ValueError('Finite timeout required')
 def expired(signum,frame):raise TimeoutError('Dependency import timeout')
 signal.signal(signal.SIGALRM,expired);signal.alarm(a.timeout_seconds)
 try:r=collect(a.require_cuda,a.requirements);r['model_lock']=validate_lock(a.lock)
 except TimeoutError:r={'status':'dependency_preflight_timeout','actual_python':sys.executable,'inference_started':False,'network_requested':False}
 finally:signal.alarm(0)
 print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['status']=='dependencies_ready' else 2)
if __name__=='__main__':main()
