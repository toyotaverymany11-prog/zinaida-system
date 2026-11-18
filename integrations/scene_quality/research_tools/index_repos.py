import concurrent.futures
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).parent
REPOS={
 'OpenMontageInc/OpenMontage':'main','HKUDS/ViMax':'main',
 'seme-org/open-director':'main','ThinkFlowLab/OpenDirector':'main',
 'sanchezrobertodev/opsis':'main','HBAI-Ltd/Toonflow-app':'master',
 'waooAI/waoowaoo':'main','hojiahao/cinefoundry':'main',
 'FireRedTeam/FireRed-OpenStoryline':'main','chatfire-AI/huobao-drama':'master',
 'sjtuplayer/showvi':'master','ByteDance/LatentSync':'main',
 'TMElyralab/MuseTalk':'main','MeiGen-AI/InfiniteTalk':'main',
 'MeiGen-AI/MultiTalk':'main','Lightricks/LTX-2':'main',
 'Lightricks/ComfyUI-LTXVideo':'master','QwenLM/Qwen2.5-Omni':'main',
 'Vchitect/VBench':'master','TIGER-AI-Lab/VideoScore':'main',
 'Wan-Video/Wan2.2':'main','fishaudio/fish-speech':'main',
}

def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'VideoProductionResearch/1.0'})
 with urllib.request.urlopen(req,timeout=25) as r:return r.read()

def one(item):
 repo,branch=item; path=ROOT/'indexes'/(repo.replace('/','_')+'.json');path.parent.mkdir(exist_ok=True)
 if path.exists():return json.loads(path.read_text())
 try:
  data=json.loads(get(f'https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1'))
  result={'repo':repo,'branch':branch,'tree_sha':data['sha'],'truncated':data.get('truncated'),
          'files':[x for x in data['tree'] if x['type']=='blob']}
 except Exception as e:result={'repo':repo,'branch':branch,'error':str(e)}
 path.write_text(json.dumps(result));return result

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:rows=list(ex.map(one,REPOS.items()))
 for r in rows:
  docs=[x['path'] for x in r.get('files',[]) if x['path'].lower().endswith('.md')
        and not any(v in x['path'].lower() for v in ['node_modules','changelog','license','readme_zh','readme.zh','readme.ja','readme_ja','readme_ko','readme.ko'])]
  print(r['repo'],r.get('error',''),json.dumps(docs[:160],ensure_ascii=False))
