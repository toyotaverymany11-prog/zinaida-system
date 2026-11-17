"""Turn one verified generated shot into an editable, explicitly unreleased preview."""
import argparse
from fractions import Fraction
from pathlib import Path
import shutil

from .core import ProductionError, Runtime, digest, object_digest, probe, read_json, write_json
from .media import render
from .shots import folder, load_request, shot_file


def build(root, ident, request_id, output, *, timeout=180):
    runtime=Runtime(timeout);output=Path(output).resolve()
    request=load_request(root,ident,request_id)
    source=shot_file(root,ident,request_id)
    receipt=read_json(folder(root,ident,request_id)/'result.json')
    binding={'request_sha256':request['request_sha256'],'output_sha256':receipt['output_sha256']}
    if output.exists():
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
    a=p.parse_args()
    import json
    print(json.dumps(build(a.root,a.order_id,a.request_id,a.output)))
