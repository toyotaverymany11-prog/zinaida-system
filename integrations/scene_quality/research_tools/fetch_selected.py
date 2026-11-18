import concurrent.futures
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
from index_repos import get

ROOT=Path(__file__).parent
SELECT={
'OpenMontageInc/OpenMontage':'''README.md
AGENT_GUIDE.md
docs/ARCHITECTURE.md
docs/PROVIDERS.md
docs/comfyui-adapter-plan.md
pipeline_defs/cinematic.yaml
skills/meta/checkpoint-protocol.md
skills/meta/creative-intake.md
skills/meta/reviewer.md
skills/meta/taste-direction.md
skills/meta/video-reference-analyst.md
skills/meta/voice-performance-director.md
skills/pipelines/cinematic/script-director.md
skills/pipelines/cinematic/scene-director.md
skills/pipelines/cinematic/asset-director.md
skills/pipelines/cinematic/edit-director.md''',
'HKUDS/ViMax':'''readme.md
prompts/agent.md
prompts/workflow.md
web/README.md
pipelines/script2video_pipeline.py
agents/storyboard_artist.py
agents/best_image_selector.py
agents/camera_image_generator.py
agent_runtime/vimax_adapters.py
utils/retry.py''',
'sanchezrobertodev/opsis':'''README.md
docs/comfy-workflows.md
docs/local-model-storage.md
docs/research/06-architecture-blueprint.md
infra/runpod/wan-core/README.md
infra/server/README.md
apps/server/src/studio/cinema/planner.py
apps/server/src/studio/pipelines/recipes/cinema.py
apps/server/src/studio/pipelines/recipes/talking.py
apps/server/src/studio/pipelines/recipes/cinema_cast.py
apps/server/src/studio/pipelines/engine.py
apps/server/src/studio/budget/guard.py''',
'HBAI-Ltd/Toonflow-app':'''docs/readme/readmeEn.md
docs/development.md
packages/mcp/README.md
packages/skills/workflow/references/stateAndDelivery.md
packages/skills/workflow/references/methods/storyDevelopment.md
packages/skills/workflow/references/methods/colorAndLight.md
packages/skills/v118workflow/references/knowledge/shotCraft.md
packages/skills/v118workflow/references/knowledge/videoPromptCraft.md
packages/skills/v118workflow/references/directorPlan.md
packages/skills/v118workflow/references/baseAssets.md
packages/teams/storyboardTeam/members/reviewer.md
packages/teams/storyboardTeam/knowledge/continuity.md
packages/nodes/director3dNode/readme.md
packages/tools/ffmpeg/readme.md''',
'hojiahao/cinefoundry':'''README.md
docs/install.md
docs/configuration.md
docs/production-pipeline.md
.agents/skills/cinematography-and-art-direction/SKILL.md
.agents/skills/character-and-continuity/SKILL.md
.agents/skills/dialogue-and-voice/SKILL.md
.agents/skills/shot-quality-gate/SKILL.md
.agents/skills/spark-model-scheduler/SKILL.md
.agents/skills/cinefoundry-micro-drama/SKILL.md
.agents/skills/screenwriting/SKILL.md
.agents/skills/editing-and-versioning/SKILL.md
src/pipelines/drama/index.ts''',
'ThinkFlowLab/OpenDirector':'''README.md
docs/architecture/agent-runtime.md
docs/architecture/capability-contract.md
docs/guides/video-model-capabilities.md
docs/guides/user-guide.md
docs/development/lessons.md
packages/agent/skills/character-replacement/workflow.md''',
'seme-org/open-director':'''README.md
apps/web/src/server/agent/graph/nodes/director.ts
apps/web/src/server/agent/graph/nodes/recipe/voice-agent.ts
apps/web/src/server/batch/pipeline.ts''',
'waooAI/waoowaoo':'''README_en.md
docs/INSTALL.md
docs/architecture/modules/durable-execution.md
docs/architecture/modules/failure-governance.md
docs/architecture/modules/billing-approval.md
docs/architecture/modules/provider-gateway.md
docs/architecture/modules/audio-production.md
src/lib/creative-skills/skills/video-direction/SKILL.md''',
'chatfire-AI/huobao-drama':'''README.en.md
docs/video-delivery-implementation.md
backend/workspace/skills/storyboard-breaker/SKILL.en.md
backend/src/agents/voice-reference-instructions.ts''',
'FireRedTeam/FireRed-OpenStoryline':'''README.md
docs/source/en/guide.md
docs/source/en/faq.md
.storyline/skills/default_editing_workflow_skill/SKILL.md
src/open_storyline/nodes/core_nodes/plan_timeline.py
src/open_storyline/nodes/core_nodes/understand_clips.py''',
'sjtuplayer/showvi':'''README_EN.md
prompts/README.md''',
'ByteDance/LatentSync':'''README.md
docs/syncnet_arch.md''',
'TMElyralab/MuseTalk':'''README.md
assets/BBOX_SHIFT.md''',
'MeiGen-AI/InfiniteTalk':'''README.md
generate_infinitetalk.py''',
'MeiGen-AI/MultiTalk':'''README.md''',
'Lightricks/LTX-2':'''README.md
packages/ltx-pipelines/docs/pipeline-selection.md
packages/ltx-pipelines/docs/conditioning.md
packages/ltx-pipelines/docs/optimization.md
packages/ltx-pipelines/docs/installation.md
packages/ltx-pipelines/src/ltx_pipelines/a2vid_two_stage.py''',
'Lightricks/ComfyUI-LTXVideo':'''example_workflows/2.5/README.md
tiled_fusion_sampler.md''',
'QwenLM/Qwen2.5-Omni':'''README.md
qwen-omni-utils/README.md''',
'Vchitect/VBench':'''README.md
VBench-2.0/README.md
VBench-2.0/README-FAQ.md''',
'TIGER-AI-Lab/VideoScore':'''README.md
benchmark/README.md''',
'Wan-Video/Wan2.2':'''README.md
wan/modules/animate/preprocess/UserGuider.md''',
'fishaudio/fish-speech':'''docs/en/inference.md
docs/en/install.md''',
}

def one(item):
 repo,path,index=item
 dest=ROOT/'documents'/repo.replace('/','_')/path
 dest.parent.mkdir(parents=True,exist_ok=True)
 url=f'https://raw.githubusercontent.com/{repo}/{index["branch"]}/'+urllib.parse.quote(path)
 entry={'repo':repo,'path':path,'canonical_id':f'github:{repo.lower()}:{path}',
        'url':f'https://github.com/{repo}/blob/{index["branch"]}/'+urllib.parse.quote(path),
        'download_url':url,'tree_sha':index.get('tree_sha'),'accessed':datetime.now(timezone.utc).isoformat(),
        'status':'downloaded_not_yet_read'}
 try:
  metadata=next(x for x in index['files'] if x['path']==path)
  data=dest.read_bytes() if dest.exists() else get(url)
  blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  if blob!=metadata['sha']:raise ValueError('File changed from pinned index')
  data.decode('utf-8'); dest.write_bytes(data)
  entry.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),blob_sha=blob,
               local_path=str(dest.resolve()))
 except Exception as e:entry.update(status='unavailable',error=str(e))
 return entry

if __name__=='__main__':
 items=[]
 for repo,paths in SELECT.items():
  index=json.loads((ROOT/'indexes'/(repo.replace('/','_')+'.json')).read_text())
  items.extend((repo,p,index) for p in paths.splitlines())
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:rows=list(ex.map(one,items))
 for i,r in enumerate(rows,1):r['id']=f'S{i:03}'
 (ROOT/'ledger.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 print(json.dumps({'selected':len(rows),'downloaded':sum(r['status']=='downloaded_not_yet_read' for r in rows),
                   'errors':[(r['id'],r['repo'],r['path'],r.get('error')) for r in rows if r['status']=='unavailable']}))
