"""Local audiovisual input controls, deliberately not an artistic gold dataset."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import secrets
import subprocess

from .contracts import Invalid,require_text,sha
from .supervisor import file_sha,write

PALETTE={'red':'0xFF4040','green':'0x40FF40','blue':'0x4040FF'}


def build(root,sources):
    root=Path(root)
    if root.exists() and any(root.iterdir()):raise Invalid('Control batch exists; reconcile instead of regenerating')
    if not isinstance(sources,list) or not 2<=len(sources)<=8:raise Invalid('Provide2..8 frozen speech sources')
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    (root/'media').mkdir();private=root/'private';private.mkdir(mode=0o700)
    public=[];gold=[];groups=set()
    for index,source in enumerate(sources):
        path=Path(source['file']);expected=sha(source['sha256']);require_text(source['literal_words'],'frozen source transcript')
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or file_sha(path)!=expected:
            raise Invalid('Frozen speech source changed')
        if expected in groups:raise Invalid('Use distinct frozen source groups');
        groups.add(expected)
        meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(path)],timeout=15))
        audio=next(x for x in meta['streams'] if x['codec_type']=='audio')
        if not 0<float(audio['duration'])<=6:raise Invalid('Speech must fit finite6second control')
        token=secrets.token_hex(16);seed=secrets.token_hex(16);rng=random.Random(int(seed,16))
        colors=list(PALETTE);rng.shuffle(colors);flash_frame=rng.randrange(58,84) if index%2 else None
        background=f'color=c={PALETTE[colors[0]]}:s=320x568:r=24:d=6'
        filters=(f"[0:v]drawbox=x=0:y=0:w=iw:h=ih:color={PALETTE[colors[1]]}:t=fill:enable='between(n,48,95)',"
                 f"drawbox=x=0:y=0:w=iw:h=ih:color={PALETTE[colors[2]]}:t=fill:enable='gte(n,96)'[bg];"
                 "[bg][1:v]overlay=x='20+28*t':y=270:shortest=1,"
                 "drawtext=text='SILENT':fontcolor=white:fontsize=24:x=16:y=24")
        if flash_frame is not None:filters+=f",drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(n,{flash_frame},{flash_frame+1})'"
        filters+='[v];[2:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=end_sample=288000,asetpts=N/SR/TB[a]'
        out=root/'media'/(token+'.mp4')
        command=['ffmpeg','-v','error','-y','-f','lavfi','-i',background,
                 '-f','lavfi','-i','color=c=white:s=24x24:r=24:d=6','-i',str(path),
                 '-filter_complex',filters,'-map','[v]','-map','[a]','-t','6','-r','24','-fps_mode','cfr',
                 '-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac',
                 '-ar','48000','-b:a','128k','-movflags','+faststart',str(out)]
        subprocess.run(command,check=True,timeout=60)
        actual=file_sha(out)
        public.append({'id':token,'file':'media/'+out.name,'mime_type':'video/mp4',
                       'sha256':actual,'bytes':out.stat().st_size,'duration_seconds':6})
        gold.append({'id':token,'artifact_sha256':actual,'source_group_sha256':expected,
                     'split':'development' if index==0 else 'holdout','private_seed':seed,
                     'expected_colors':colors,'color_change_frames':[48,96],
                     'moving_object':'white square moves left to right,2D diagnostic only',
                     'literal_audible_words':source['literal_words'],'visible_distractor':'SILENT',
                     'black_flash_frames':[] if flash_frame is None else [flash_frame,flash_frame+1],
                     'label_basis':'Programmatically specified exact frames plus previously frozen speech source; not artistic opinion'})
    packet={'schema_version':1,'purpose':'input_modality_preflight_only',
            'assets':public,'question':'For each video report visible color order, moving objects, literal audible words, lettering and uncertainty with timestamps. Do not infer audio from lettering.',
            'artistic_scopes_qualified':[],'model_called':False}
    write(root/'public-request.json',packet)
    write(private/'gold.json',{'purpose':'private_objective_input_controls_only',
        'cases':gold,'not_a_complete_artistic_calibration_dataset':True,'artistic_scopes_qualified':[]})
    return {'controls':len(public),'public_request_sha256':file_sha(root/'public-request.json'),
            'private_gold_sha256':file_sha(private/'gold.json'),'provider_calls':0,
            'artistic_scopes_qualified':[],'new_external_usd':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--frozen-sources',type=Path,required=True);a=p.parse_args()
    print(json.dumps(build(a.root,json.loads(a.frozen_sources.read_text())),indent=2))


if __name__=='__main__':main()
