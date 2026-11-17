"""Turn one verified generated shot into an editable, explicitly unreleased preview."""
import argparse
from fractions import Fraction
from pathlib import Path
import shutil

from .core import ProductionError, Runtime, digest, object_digest, probe, read_json, write_json
from .media import render
from .shots import folder, load_request, shot_file


def project_file(root, ident, request_id):
    """Read-only delivery of a current, previously built and verified package."""
    shot_file(root,ident,request_id)
    output=folder(root,ident,request_id)/'edit'
    if not output.is_dir():raise ProductionError('Project package has not been built')
    _verify_existing(root,ident,request_id,output,Runtime(30))
    receipt=read_json(output/'project-package.json')
    path=output/'preview-project.zip'
    if receipt['manifest_sha256']!=object_digest(read_json(output/'manifest.json')) or digest(path)!=receipt['sha256']:
        raise ProductionError('Project package changed')
    return path


def package_preview(output):
    """A portable review bundle, preserving the original and relative OTIO links."""
    import zipfile
    import opentimelineio as otio
    from .manifest import validate
    output=Path(output).resolve()
    manifest=read_json(output/'manifest.json')
    if manifest.get('artifact_kind')!='generated_scene_preview':
        raise ProductionError('Only generated scene previews can use this bundle route')
    checked=validate(manifest,output)
    report=read_json(output/'render/render.json')
    if checked['manifest_sha256']!=report['manifest_sha256'] or digest(output/'render/master.mp4')!=report['output_sha256']:
        raise ProductionError('Preview changed before packaging')
    if not all(report['technical_checks'].values()):
        raise ProductionError('Preview technical checks failed')
    timeline=otio.adapters.read_from_file(str(output/'render/timeline.otio'))
    mapping={path.as_uri():manifest['assets'][key]['path'] for key,path in checked['paths'].items()}
    for clip in timeline.find_clips():
        reference=clip.media_reference
        target=getattr(reference,'target_url',None)
        if target not in mapping:
            raise ProductionError('Timeline references unverified or external media')
        reference.target_url=mapping[target]
    target=output/'preview-project.zip';part=output/'preview-project.zip.partial'
    try:
        with zipfile.ZipFile(part,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('timeline.otio',otio.adapters.write_to_string(timeline,adapter_name='otio_json'))
            archive.write(output/'manifest.json','manifest.json')
            archive.write(output/'render/master.mp4','preview.mp4')
            for key,path in checked['paths'].items():archive.write(path,manifest['assets'][key]['path'])
            import json
            archive.writestr('checks.json',json.dumps({'manifest_sha256':report['manifest_sha256'],
                'preview_sha256':report['output_sha256'],'technical_checks':report['technical_checks'],
                'finished_video_accepted':False},indent=2))
            archive.writestr('README.txt','Распакуйте весь архив в одну папку.\n'
                'preview.mp4: монтажная копия для просмотра.\n'
                'assets/: неизменённый исходный результат генерации.\n'
                'timeline.otio: монтажная структура с относительными ссылками на assets/.\n'
                'manifest.json и checks.json: состав и проверки целостности.\n'
                'Это отдельная проверочная сцена, не принятый готовый фильм.\n')
        # Verify the actual archive bytes and every stored member CRC.
        with zipfile.ZipFile(part) as archive:
            if archive.testzip() is not None:raise ProductionError('Corrupted project archive')
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)
    write_json(output/'project-package.json',{'file':target.name,'bytes':target.stat().st_size,
        'sha256':digest(target),'manifest_sha256':report['manifest_sha256'],'finished_video_accepted':False})
    return target


def _verify_existing(root,ident,request_id,output,runtime):
    request=load_request(root,ident,request_id)
    receipt=read_json(folder(root,ident,request_id)/'result.json')
    binding={'request_sha256':request['request_sha256'],'output_sha256':receipt['output_sha256']}
    saved=read_json(output/'binding.json')
    if saved!=binding:raise ProductionError('Edit folder belongs to another shot')
    report=read_json(output/'render/render.json')
    if digest(output/'render/master.mp4',runtime)!=report['output_sha256']:
        raise ProductionError('Rendered preview changed')
    if digest(output/'assets/shot.mp4',runtime)!=receipt['output_sha256']:
        raise ProductionError('Edit source changed')
    manifest=read_json(output/'manifest.json')
    if object_digest(manifest)!=report['manifest_sha256']:
        raise ProductionError('Edit manifest changed')
    return report


def build(root, ident, request_id, output, *, timeout=180):
    """Serialize edits and preserve interrupted attempts before a bounded retry."""
    import fcntl
    import uuid
    output=Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.with_name(output.name+'.build.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ProductionError('Scene edit is already active') from None
        # Validate the current order before touching an old attempt.
        shot_file(root,ident,request_id)
        if output.exists() and not (output/'render/render.json').exists():
            request=load_request(root,ident,request_id)
            receipt=read_json(folder(root,ident,request_id)/'result.json')
            binding={'request_sha256':request['request_sha256'],'output_sha256':receipt['output_sha256']}
            if read_json(output/'binding.json')!=binding:
                raise ProductionError('Incomplete edit belongs to another shot')
            # Keep diagnostics and any partial output, never erase user content.
            output.rename(output.with_name(output.name+'.interrupted-'+uuid.uuid4().hex))
        return _build(root,ident,request_id,output,timeout=timeout)


def _build(root, ident, request_id, output, *, timeout=180):
    runtime=Runtime(timeout);output=Path(output).resolve()
    request=load_request(root,ident,request_id)
    source=shot_file(root,ident,request_id)
    receipt=read_json(folder(root,ident,request_id)/'result.json')
    binding={'request_sha256':request['request_sha256'],'output_sha256':receipt['output_sha256']}
    if output.exists():return _verify_existing(root,ident,request_id,output,runtime)
    info=probe(source,runtime)
    video=next((s for s in info['streams'] if s['codec_type']=='video'),None)
    if not video:raise ProductionError('Generated file has no video')
    rate=Fraction(video['avg_frame_rate'])
    if rate.denominator!=1:raise ProductionError('Fractional frame rate needs an explicit edit decision')
    frames=int(video['nb_frames'])
    output.mkdir(parents=True,exist_ok=False);(output/'assets').mkdir()
    write_json(output/'binding.json',binding)
    shutil.copyfile(source,output/'assets/shot.mp4')
    if digest(output/'assets/shot.mp4',runtime)!=receipt['output_sha256']:
        raise ProductionError('Copied source changed')
    manifest={'schema_version':1,'artifact_kind':'generated_scene_preview',
        'project_id':ident,'revision':'shot-'+request_id,'quality_profile':'photorealistic',
        'format':{'width':video['width'],'height':video['height'],'fps':int(rate)},
        'assets':{'shot':{'path':'assets/shot.mp4','sha256':receipt['output_sha256']}},
        'clips':[{'id':'scene','route':'cinematic','purpose':request['prompt'],
                  'asset':'shot','duration_frames':frames,
                  'source_audio':'keep' if any(s['codec_type']=='audio' for s in info['streams']) else 'mute'}],
        'characters':{},'audio':[],'overlays':[],
        'note':'Editable preview of one generated scene. Not a finished or accepted film.'}
    write_json(output/'manifest.json',manifest)
    result=render(manifest,output,output/'render',runtime)
    # Revocation during rendering must prevent reporting a current preview.
    shot_file(root,ident,request_id)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--order-id',required=True)
    p.add_argument('--request-id',required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--package',action='store_true')
    a=p.parse_args()
    import json
    result=build(a.root,a.order_id,a.request_id,a.output)
    if a.package:result=dict(result,review_package=str(package_preview(a.output)))
    print(json.dumps(result))
