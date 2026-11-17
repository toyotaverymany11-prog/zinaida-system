"""Bounded CPU-only shot corrections, preserving every source and prior revision."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import uuid

from .core import ProductionError, Runtime, digest, object_digest, read_json, write_json
from .media import render
from .shot_edit import package_preview
from .shots import folder, shot_file


def revise(root, order_id, request_id, edit, *, timeout=180):
    """Create/reuse one exact trim/audio decision. Never sends a model request."""
    if not isinstance(edit,dict) or set(edit)!={'source_sha256','start_frame','duration_frames','source_audio'}:
        raise ProductionError('Correction requires exact source, frame range and audio decision')
    if (type(edit['start_frame']) is not int or edit['start_frame']<0 or
            type(edit['duration_frames']) is not int or edit['duration_frames']<1 or
            edit['source_audio'] not in {'keep','mute'}):
        raise ProductionError('Invalid correction frame range or audio decision')
    runtime=Runtime(timeout)
    source=shot_file(root,order_id,request_id)
    if digest(source,runtime)!=edit['source_sha256']:
        raise ProductionError('Correction belongs to another source version')
    base=folder(root,order_id,request_id)
    # The unmodified editable project must already exist. A correction cannot
    # silently trigger its preparation or a model generation.
    original=base/'edit'
    if not (original/'render/render.json').is_file():
        raise ProductionError('Build the original editable scene before correcting it')
    from .shot_edit import _verify_existing
    _verify_existing(root,order_id,request_id,original,runtime)
    manifest=read_json(original/'manifest.json')
    clip=manifest['clips'][0]
    if edit['start_frame']+edit['duration_frames']>clip['duration_frames']:
        raise ProductionError('Correction extends beyond original frames')
    if edit['source_audio']=='keep' and clip['source_audio']!='keep':
        raise ProductionError('Original scene has no source audio to keep')
    binding={'request_id':request_id,'source_sha256':edit['source_sha256'],
             'base_manifest_sha256':object_digest(manifest),'edit':edit}
    revision=object_digest(binding)
    parent=base/'revisions';parent.mkdir(exist_ok=True)
    output=parent/revision
    with (parent/(revision+'.lock')).open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ProductionError('This correction is already running') from None
        if output.exists():
            if read_json(output/'binding.json')!=binding:raise ProductionError('Correction binding changed')
            if (output/'result.json').is_file():
                result=read_json(output/'result.json')
                report=read_json(output/'render/render.json')
                if (digest(output/'render/master.mp4',runtime)!=report['output_sha256'] or
                    digest(output/'assets/shot.mp4',runtime)!=edit['source_sha256'] or
                    object_digest(read_json(output/'manifest.json'))!=report['manifest_sha256'] or
                    digest(output/'preview-project.zip',runtime)!=result['package_sha256']):
                    raise ProductionError('Saved correction changed')
                shot_file(root,order_id,request_id)
                return result
            output.rename(parent/(revision+'.interrupted-'+uuid.uuid4().hex))
        output.mkdir();write_json(output/'binding.json',binding)
        (output/'assets').mkdir();shutil.copyfile(source,output/'assets/shot.mp4')
        if digest(output/'assets/shot.mp4',runtime)!=edit['source_sha256']:
            raise ProductionError('Correction source changed during copy')
        manifest['revision']='edit-'+revision[:24]
        manifest['clips'][0].update(source_in_seconds=edit['start_frame']/manifest['format']['fps'],
            duration_frames=edit['duration_frames'],source_audio=edit['source_audio'])
        write_json(output/'manifest.json',manifest)
        report=render(manifest,output,output/'render',runtime)
        archive=package_preview(output)
        shot_file(root,order_id,request_id)
        result={'revision_id':revision,'status':'needs_quality_review','output':str(output),
            'source_sha256':edit['source_sha256'],'output_sha256':report['output_sha256'],
            'package_sha256':digest(archive,runtime),'edit':edit,'technical_checks':report['technical_checks'],
            'external_requests_sent':0,'finished_video_accepted':False}
        write_json(output/'result.json',result)
        return result


def revision_file(root,order_id,request_id,revision_id,kind):
    """Deliver an immutable correction only while its original plan is current."""
    import re
    if not re.fullmatch(r'[a-f0-9]{64}',revision_id) or kind not in {'video','project'}:
        raise ProductionError('Invalid correction address')
    source=shot_file(root,order_id,request_id)
    output=folder(root,order_id,request_id)/'revisions'/revision_id
    binding=read_json(output/'binding.json');result=read_json(output/'result.json')
    if (object_digest(binding)!=revision_id or binding['request_id']!=request_id or
            binding['source_sha256']!=digest(source) or result['revision_id']!=revision_id or
            result['edit']!=binding['edit'] or result['source_sha256']!=binding['source_sha256']):
        raise ProductionError('Correction binding changed')
    report=read_json(output/'render/render.json')
    if object_digest(read_json(output/'manifest.json'))!=report['manifest_sha256']:
        raise ProductionError('Correction manifest changed')
    path=output/('render/master.mp4' if kind=='video' else 'preview-project.zip')
    expected=result['output_sha256'] if kind=='video' else result['package_sha256']
    if digest(path)!=expected:raise ProductionError('Correction media changed')
    return path


def revisions(root,order_id,request_id):
    import re
    shot_file(root,order_id,request_id)
    parent=folder(root,order_id,request_id)/'revisions'
    if not parent.exists():return []
    result=[]
    for output in sorted(parent.iterdir()):
        if not output.is_dir() or not re.fullmatch(r'[a-f0-9]{64}',output.name):continue
        if len(result)>=100:raise ProductionError('Too many corrections for one scene')
        try:
            revision_file(root,order_id,request_id,output.name,'video')
            revision_file(root,order_id,request_id,output.name,'project')
            receipt=read_json(output/'result.json')
            result.append({key:receipt[key] for key in ('revision_id','edit','output_sha256','status','finished_video_accepted')})
        except (ProductionError,OSError,ValueError,KeyError):continue
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--order-id',required=True);p.add_argument('--request-id',required=True)
    p.add_argument('--edit',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(revise(a.root,a.order_id,a.request_id,read_json(a.edit))))
