"""Bounded cuts-only source preview, never a generated or accepted final film."""
import fcntl
from fractions import Fraction
import json
import math
from pathlib import Path
from uuid import UUID

from .core import ProductionError, Runtime, digest, object_digest, read_json, write_json
from .intake import Intake
from .planning import latest_plan, order_evidence


class PreviewInterrupted(ProductionError):
    pass


def approved_packet(root, ident, request, runtime):
    packet = order_evidence(root, ident, runtime=runtime)
    proposal = latest_plan(root, ident, packet['packet_sha256'])
    if (not proposal or proposal['revision'] != request['expected_revision'] or
            packet['packet_sha256'] != request['packet_sha256'] or
            proposal.get('local_review', {}).get('decision') != 'accept_plan'):
        raise ProductionError('Preview needs the current locally accepted plan and unchanged evidence')
    return packet, proposal


def preview_manifest(packet, proposal):
    scenes = proposal['plan']['scenes']
    if len(scenes) > 100 or any(not s['source'] for s in scenes):
        raise ProductionError('Source preview needs 1..100 existing video intervals; generated scenes are unavailable')
    refs = {r['asset_id']: r for r in packet['references']}
    first = refs[scenes[0]['source']['asset_id']]['video_format'][0]
    ratio = Fraction(first.get('avg_frame_rate', '24/1'))
    fps = int(ratio) if ratio.denominator == 1 and ratio in {24,25,30,48,50,60} else 24
    scale = min(1, 640/max(first['width'],first['height']))
    width, height = (max(64, int(first[k]*scale)//2*2) for k in ('width','height'))
    assets, clips = {}, []
    for i, scene in enumerate(scenes):
        source = scene['source']; asset = source['asset_id']; ref = refs[asset]
        # Never request beyond the measured end. Short sub-frame scenes are rejected.
        frames = math.floor((source['end']-source['start'])*fps + 1e-7)
        if frames < 1:
            raise ProductionError('Source interval is shorter than one preview frame')
        assets[asset] = {'path':'assets/'+asset, 'sha256':asset}
        clips.append({'id':f'scene-{i+1}', 'route':'existing', 'asset':asset,
            'purpose':'Source timing preview only: '+scene['action'],
            'source_in_seconds':source['start'], 'duration_frames':frames,
            'source_audio':'keep' if ref['audio_index'] is not None else 'mute'})
    return {'schema_version':1, 'artifact_kind':'source_timing_preview', 'project_id':packet['order']['id'],
        'revision':f"preview-{proposal['revision']}", 'quality_profile':'source_matched',
        'format':{'width':width,'height':height,'fps':fps}, 'assets':assets,
        'clips':clips, 'characters':{}, 'audio':[], 'overlays':[]}


def request_preview(root, ident, request):
    ident = str(UUID(ident))
    if not isinstance(request,dict) or set(request) != {'request_id','expected_revision','packet_sha256'}:
        raise ProductionError('Invalid source-preview request')
    request_id = str(UUID(request['request_id']))
    if type(request['expected_revision']) is not int or request['expected_revision'] < 1:
        raise ProductionError('Invalid plan revision')
    intake = Intake(Path(root)); fingerprint = object_digest(request)
    packet, proposal = approved_packet(root,ident,request,Runtime(30))
    preview_manifest(packet,proposal)  # Reject unsupported plans before queueing.
    with intake.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT order_id,request_sha256 FROM preview_requests WHERE request_id=?',
                         (request_id,)).fetchone()
        if old:
            if old != (ident,fingerprint):
                raise ProductionError('Preview request ID belongs to different content')
            return {'accepted':True,'request_id':request_id}
        job = db.execute('SELECT status,analysis_status,preview_status FROM preparation_jobs WHERE order_id=?',
                         (ident,)).fetchone()
        active = {'queued','running','recovering','cancelling'}
        if not job or job[0] != 'awaiting_review' or job[1] in active or job[2] in active:
            raise ProductionError('Prepared order and idle controller stages are required')
        db.execute('INSERT INTO preview_requests VALUES (?,?,?,?)',
                   (request_id,ident,fingerprint,json.dumps(request)))
        db.execute("UPDATE preparation_jobs SET preview_status='queued',preview_request_id=?,preview_error=NULL WHERE order_id=?",
                   (request_id,ident))
    return {'accepted':True,'request_id':request_id}


def cancel_preview(root, ident):
    ident = str(UUID(ident))
    with Intake(Path(root)).connect() as db:
        db.execute("""UPDATE preparation_jobs SET preview_status=CASE preview_status
            WHEN 'queued' THEN 'cancelled' WHEN 'running' THEN 'cancelling'
            WHEN 'recovering' THEN 'cancelling' ELSE preview_status END WHERE order_id=?""",(ident,))
    return preview_state(root,ident)


def preview_state(root, ident):
    ident = str(UUID(ident))
    with Intake(Path(root)).connect() as db:
        row=db.execute('SELECT preview_status,preview_request_id,preview_error FROM preparation_jobs WHERE order_id=?',(ident,)).fetchone()
    if not row: raise ProductionError('Unknown order')
    result={'status':row[0],'request_id':row[1],'error':row[2]}
    if row[1]:
        request=stored_request(root,ident,row[1])
        result.update(plan_revision=request['expected_revision'],packet_sha256=request['packet_sha256'])
    return result


def stored_request(root, ident, request_id):
    ident,request_id=str(UUID(ident)),str(UUID(request_id))
    with Intake(Path(root)).connect() as db:
        row=db.execute('SELECT order_id,data FROM preview_requests WHERE request_id=?',(request_id,)).fetchone()
    if not row or row[0] != ident:raise ProductionError('Unknown source-preview request')
    return json.loads(row[1])


def render_preview(root, ident, request_id, *, timeout=180, should_cancel=None, recover_only=False):
    from .media import render
    root=Path(root).resolve();ident=str(UUID(ident));request_id=str(UUID(request_id))
    runtime=Runtime(timeout,should_cancel=should_cancel)
    request=stored_request(root,ident,request_id)
    packet,proposal=approved_packet(root,ident,request,runtime)
    manifest=preview_manifest(packet,proposal)
    folder=root/'previews'/ident/request_id;folder.mkdir(parents=True,exist_ok=True)
    output=folder/'render';receipt_path=folder/'receipt.json'
    with (folder/'lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:raise ProductionError('Preview attempt is already active') from exc
        if receipt_path.exists():
            receipt=read_json(receipt_path)
            if receipt.get('request_sha256') != object_digest(request):
                raise ProductionError('Preview receipt does not match the requested plan')
            if not (output/'render.json').is_file():
                raise PreviewInterrupted('Incomplete source preview; explicit retry is required')
        elif recover_only:
            raise PreviewInterrupted('No completed source preview to recover')
        else:
            receipt={'request_sha256':object_digest(request),'order_id':ident,'request_id':request_id,
                'plan_revision':proposal['revision'],'packet_sha256':packet['packet_sha256'],
                'scope':'source_timing_preview_only','state':'rendering',
                'generation_authorized':False,'finished_video_accepted':False,'provider_calls':0,
                'limitations':['Source cuts only; requested visual changes, replacement and generation are not applied.',
                               'Preview up to 640 pixels; timing is rounded down to complete output frames.']}
            write_json(receipt_path,receipt)
            render(manifest,root,output,runtime)
        report=read_json(output/'render.json')
        if receipt['state']=='preview_ready' and receipt.get('output_sha256') != report['output_sha256']:
            raise ProductionError('Previously verified preview receipt does not match render report')
        if report['manifest_sha256'] != object_digest(manifest) or digest(output/'master.mp4',runtime) != report['output_sha256']:
            raise ProductionError('Preview output or manifest changed')
        approved_packet(root,ident,request,runtime)  # Reject edits/revocation during rendering.
        runtime.check()
        receipt.update(state='preview_ready',output_sha256=report['output_sha256'],
                       manifest_sha256=report['manifest_sha256'],duration=report['probe']['format']['duration'])
        write_json(receipt_path,receipt)
        return receipt


def preview_file(root, ident, request_id):
    root=Path(root).resolve();ident=str(UUID(ident));request_id=str(UUID(request_id))
    request=stored_request(root,ident,request_id);runtime=Runtime(30)
    state=preview_state(root,ident)
    if state['status']!='ready' or state['request_id']!=request_id:
        raise ProductionError('Source preview is not the current completed attempt')
    approved_packet(root,ident,request,runtime)
    folder=root/'previews'/ident/request_id
    receipt=read_json(folder/'receipt.json');path=folder/'render/master.mp4'
    if (receipt.get('state') != 'preview_ready' or receipt.get('request_sha256') != object_digest(request)
            or digest(path,runtime) != receipt['output_sha256']):
        raise ProductionError('Source preview is incomplete or changed')
    return path


def preview_controls(ident, proposal, token):
    from html import escape
    config=json.dumps({'order_id':ident,'revision':proposal['revision'],
                       'packet_sha256':proposal['packet_sha256'],'token':token,
                       'accepted':proposal.get('local_review',{}).get('decision')=='accept_plan'})
    return ('<section><h2>Черновая склейка исходников</h2>'
        '<p>Проверка порядка и длительности сцен по согласованному плану. '
        'Замены людей, генерация и описанные визуальные изменения здесь ещё не выполнены. '
        'Черновик уменьшен до 640 пикселей, исходный звук сохраняется.</p>'
        '<button id="preview-build">Собрать склейку</button> '
        '<button id="preview-cancel" hidden>Остановить сборку</button>'
        '<p id="preview-status" role="status"></p>'
        '<video id="source-preview" controls preload="metadata" hidden style="width:100%;max-height:520px"></video>'
        '</section><script nonce="'+escape(token,quote=True)+'">const previewConfig='+config+';'+r'''
        let previewRequest=crypto.randomUUID(),previewState,previewPolls=0,previewTimer;
        const previewBuild=document.getElementById('preview-build'),previewCancel=document.getElementById('preview-cancel');
        const previewStatus=document.getElementById('preview-status'),previewVideo=document.getElementById('source-preview');
        const previewURL='/api/orders/'+previewConfig.order_id+'/preview';
        async function showPreview(){
            clearTimeout(previewTimer);
            try{
                const response=await fetch(previewURL);const value=await response.json();
                if(!response.ok)throw Error(value.error);
                previewState=value.status;
                const current=value.plan_revision===previewConfig.revision&&value.packet_sha256===previewConfig.packet_sha256;
                const active=['queued','running','recovering','cancelling'].includes(value.status);
                const labels={not_requested:'Склейка ещё не запрошена.',queued:'Сборка ожидает выполнения.',
                  running:'Собираю исходные фрагменты.',recovering:'Проверяю сохранившуюся сборку.',
                  cancelling:'Останавливаю сборку.',cancelled:'Сборка отменена.',ready:'Черновая склейка готова. Это не готовый ролик.',
                  failed:'Сборка не завершена.',timed_out:'Время сборки истекло.',interrupted:'Сборка была прервана.'};
                previewStatus.textContent=(value.error||labels[value.status]||value.status);
                if(value.request_id&&!current)previewStatus.textContent='Сборка относится к другой версии плана. Нужна новая склейка.';
                if(!previewConfig.accepted)previewStatus.textContent='Сначала согласуй текущую версию плана.';
                previewBuild.disabled=!previewConfig.accepted||active||(current&&value.status==='ready');previewCancel.hidden=!active;
                previewVideo.hidden=!(previewConfig.accepted&&current&&value.status==='ready');
                if(previewVideo.hidden){previewVideo.pause();previewVideo.removeAttribute('src');}
                if(!previewVideo.hidden){const src=previewURL+'/'+value.request_id;if(previewVideo.getAttribute('src')!==src)previewVideo.src=src;}
                if(active&&++previewPolls<110)previewTimer=setTimeout(showPreview,2000);
                else if(active)previewStatus.textContent+=' Обнови страницу, чтобы проверить результат.';
            }catch(error){previewStatus.textContent=error.message;previewBuild.disabled=false;}
        }
        previewBuild.onclick=async()=>{
            previewBuild.disabled=true;
            if(['failed','timed_out','interrupted','cancelled','ready'].includes(previewState))previewRequest=crypto.randomUUID();
            try{const response=await fetch(previewURL,{method:'POST',headers:{'X-Intake-Token':previewConfig.token},
                body:JSON.stringify({request_id:previewRequest,expected_revision:previewConfig.revision,packet_sha256:previewConfig.packet_sha256})});
                const value=await response.json();if(!response.ok)throw Error(value.error);previewPolls=0;showPreview();
            }catch(error){previewStatus.textContent=error.message;previewBuild.disabled=false;}
        };
        previewCancel.onclick=async()=>{try{const response=await fetch(previewURL+'/cancel',{method:'POST',headers:{'X-Intake-Token':previewConfig.token}});
            const value=await response.json();if(!response.ok)throw Error(value.error);showPreview();
            }catch(error){previewStatus.textContent=error.message;}};
        showPreview();
        '''+'</script>')
