"""Attach an existing owner film as an immutable draft, never as a shot revision."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from production.pult_link import binding, collect, decode, fingerprint
from video_media import MAX_MEDIA_BYTES

SCHEMA = 'video.owner-imported-draft.v1'
FIELDS = {'schema','binding','source_kind','project_id','title','file','sha256',
          'bytes','duration_seconds','provenance'}

def _sha(data):
    return hashlib.sha256(data).hexdigest()

def _regular(path, maximum, *, owner=False):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('draft_symlink')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= maximum:
        raise ValueError('draft_file_size')
    if owner and (info.st_uid != os.geteuid() or info.st_mode & 0o022):
        raise ValueError('untrusted_draft_file')
    return path, info

def _manifest(path, link, artifact_id):
    path, before = _regular(path, 16384, owner=True)
    data = path.read_bytes(); after = path.stat()
    if (before.st_ino,before.st_mtime_ns,before.st_size) != (after.st_ino,after.st_mtime_ns,after.st_size):
        raise ValueError('draft_manifest_changed')
    value = decode(data)
    if not isinstance(value,dict) or set(value) != FIELDS | {'artifact_id'}:
        raise ValueError('invalid_import_manifest')
    payload = {k:v for k,v in value.items() if k != 'artifact_id'}
    if (payload['schema'] != SCHEMA or payload['source_kind'] != 'imported_film'
            or value['artifact_id'] != artifact_id or fingerprint(payload) != artifact_id
            or payload['binding'] != link or payload['file'] != 'asset.mp4'
            or not isinstance(payload['project_id'],str) or not 1 <= len(payload['project_id']) <= 100
            or not isinstance(payload['title'],str) or not 1 <= len(payload['title']) <= 200
            or not isinstance(payload['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',payload['sha256'])
            or type(payload['bytes']) is not int or not 0 < payload['bytes'] <= MAX_MEDIA_BYTES
            or type(payload['duration_seconds']) not in (int,float)
            or not math.isfinite(payload['duration_seconds']) or not 0 < payload['duration_seconds'] <= 86400
            or not isinstance(payload['provenance'],dict)):
        raise ValueError('invalid_import_manifest')
    return value

def imported_draft_producer(root, link, allowed):
    """Only a trusted config may supply artifact IDs and private manifest paths."""
    from video_owner_preview import FLAGS
    root=Path(root); link=binding(link)
    if (not isinstance(allowed,dict) or not 1 <= len(allowed) <= 20
            or any(not isinstance(k,str) or not re.fullmatch('[a-f0-9]{64}',k)
                   or not isinstance(v,str) or not Path(v).is_absolute()
                   for k,v in allowed.items())):
        raise ValueError('explicit_import_allowlist_required')
    allowed=dict(allowed)

    def current(expected, artifact_id):
        if expected != link or collect(root,link)['state'] != 'observed':
            raise ValueError('order_changed')
        if artifact_id not in allowed:
            raise ValueError('unknown_imported_draft')
        manifest=Path(allowed[artifact_id])
        return manifest, _manifest(manifest,link,artifact_id)

    def read_one(expected, artifact_id):
        manifest, value=current(expected,artifact_id)
        path, before=_regular(manifest.parent/value['file'],MAX_MEDIA_BYTES,owner=True)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            opened=os.fstat(fd)
            if (opened.st_dev,opened.st_ino,opened.st_size)!=(before.st_dev,before.st_ino,before.st_size):
                raise ValueError('draft_file_changed')
            parts=[];remaining=opened.st_size
            while remaining:
                part=os.read(fd,min(remaining,1024*1024))
                if not part:raise ValueError('draft_short_read')
                parts.append(part);remaining-=len(part)
            data=b''.join(parts);after=os.fstat(fd)
            if (opened.st_mtime_ns,opened.st_size)!=(after.st_mtime_ns,after.st_size):
                raise ValueError('draft_file_changed')
            if len(data)!=value['bytes'] or _sha(data)!=value['sha256']:
                raise ValueError('draft_sha_changed')
            new_path,new_value=current(expected,artifact_id)
            latest=path.stat()
            if (new_path!=manifest or new_value!=value
                    or (latest.st_dev,latest.st_ino,latest.st_mtime_ns,latest.st_size)
                    !=(opened.st_dev,opened.st_ino,opened.st_mtime_ns,opened.st_size)):
                raise ValueError('draft_source_changed')
            return data,value
        finally:os.close(fd)

    def produce(expected, artifact_id, kind):
        if kind=='owner_imported_draft_catalog':
            if artifact_id is not None:raise ValueError('invalid_import_id')
            rows=[]
            for key in sorted(allowed):
                data,value=read_one(expected,key)
                rows.append({n:value[n] for n in ['artifact_id','sha256','bytes','title',
                                                'source_kind','project_id','duration_seconds']})
            return {'binding':link,'current':True,'drafts':rows,**FLAGS}
        if kind!='owner_imported_draft_video':raise ValueError('invalid_import_kind')
        data,value=read_one(expected,artifact_id)
        return {'binding':link,'current':True,'artifact_id':artifact_id,'kind':kind,
                'sha256':value['sha256'],'data':data,**FLAGS}
    return produce

def attach(config_path, task_id, source, destination, *, expected_sha256,
           expected_duration, title, project_id, provenance):
    """Finite trusted import. Does not edit DB, producer config, web config or QA."""
    from video_binding import prepare
    config=json.loads(Path(config_path).read_text());entry=config['orders'][task_id]
    link=binding(entry['binding'])
    if link['task_id']!=task_id:raise ValueError('task_binding_mismatch')
    verified=prepare(config['pult_database'],**link)
    if verified!=link or collect(entry['root'],link)['state']!='observed':
        raise ValueError('current_owner_task_required')
    if not re.fullmatch('[a-f0-9]{64}',expected_sha256):
        raise ValueError('explicit_sha_required')
    if not isinstance(title,str) or not 1<=len(title)<=200:
        raise ValueError('title_required')
    if not isinstance(project_id,str) or not 1<=len(project_id)<=100:
        raise ValueError('project_required')
    if (type(expected_duration) not in (int,float) or not math.isfinite(expected_duration)
            or not 0<expected_duration<=86400):
        raise ValueError('explicit_duration_required')
    source,before=_regular(source,MAX_MEDIA_BYTES)
    data=source.read_bytes();after=source.stat()
    if (before.st_dev,before.st_ino,before.st_mtime_ns,before.st_size)!=(after.st_dev,after.st_ino,after.st_mtime_ns,after.st_size):
        raise ValueError('import_source_changed')
    if _sha(data)!=expected_sha256:raise ValueError('import_source_sha_mismatch')
    probe=json.loads(subprocess.check_output(
        ['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(source)],timeout=10))
    duration=float(probe['format']['duration'])
    if abs(duration-expected_duration)>0.002 or not any(
            s['codec_type']=='video' for s in probe['streams']) or not any(
            s['codec_type']=='audio' for s in probe['streams']):
        raise ValueError('import_media_metadata_mismatch')
    payload={'schema':SCHEMA,'binding':link,'source_kind':'imported_film','project_id':project_id,
             'title':title,'file':'asset.mp4','sha256':expected_sha256,'bytes':len(data),
             'duration_seconds':duration,'provenance':provenance}
    artifact_id=fingerprint(payload);value=dict(payload,artifact_id=artifact_id)
    destination=Path(destination).absolute()
    if any(p.is_symlink() for p in (destination,*destination.parents)):
        raise ValueError('untrusted_import_destination')
    destination.mkdir(parents=True,exist_ok=True,mode=0o700)
    owner=destination.stat()
    if owner.st_uid!=os.geteuid() or owner.st_mode&0o077:
        raise ValueError('private_import_destination_required')
    target=destination/artifact_id
    if target.exists():
        imported_draft_producer(entry['root'],link,{artifact_id:str(target/'manifest.json')})(
            link,artifact_id,'owner_imported_draft_video')
        return {'status':'existing_exact_import','artifact_id':artifact_id,'manifest':str(target/'manifest.json'),
                'sha256':expected_sha256,'bytes':len(data),'enabled':False}
    temporary=Path(tempfile.mkdtemp(prefix='.import-',dir=destination))
    try:
        (temporary/'asset.mp4').write_bytes(data);os.chmod(temporary/'asset.mp4',0o400)
        (temporary/'manifest.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
        os.chmod(temporary/'manifest.json',0o400)
        if collect(entry['root'],link)['state']!='observed' or prepare(config['pult_database'],**link)!=link:
            raise ValueError('binding_changed_during_import')
        temporary.rename(target)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    imported_draft_producer(entry['root'],link,{artifact_id:str(target/'manifest.json')})(
        link,artifact_id,'owner_imported_draft_video')
    return {'status':'imported_not_enabled','artifact_id':artifact_id,'manifest':str(target/'manifest.json'),
            'sha256':expected_sha256,'bytes':len(data),'enabled':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--task-id',required=True)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--expected-sha256',required=True);p.add_argument('--expected-duration',type=float,required=True)
    p.add_argument('--title',required=True);p.add_argument('--project-id',required=True)
    p.add_argument('--library-file-id',required=True);p.add_argument('--library-version',type=int,required=True)
    a=p.parse_args()
    result=attach(a.config,a.task_id,a.source,a.destination,expected_sha256=a.expected_sha256,
                  expected_duration=a.expected_duration,title=a.title,project_id=a.project_id,
                  provenance={'kind':'owner_library_file','library_file_id':a.library_file_id,
                              'library_version':a.library_version})
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
