"""Audit one installed candidate tool with local technical fixtures only.

Run with OpenMontage's isolated Python. This is tool qualification, not a
creative pipeline run or evidence that the complete producer is autonomous.
The caller must bound execution time and supply a credential-free environment.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--application', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if (args.application / '.env').exists():
        raise RuntimeError('Use a separate checkout without provider credentials')
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(args.application))
    from tools.tool_registry import registry
    registry.discover('tools.video.video_stitch')
    tool = registry.get('video_stitch')
    assert tool is not None
    results = []
    for transition, expected_frames in [('cut', 144), ('crossfade', 96)]:
        output = args.output / f'{transition}.mp4'
        result = tool.execute({'operation': 'stitch',
            'clips': [str(args.source / name) for name in ('red.mp4','blue.mp4','red.mp4')],
            'transition': transition, 'transition_duration': 1.0,
            'output_path': str(output)})
        record = {'transition': transition, 'tool_success': result.success,
                  'error': result.error, 'expected_frames': expected_frames}
        if output.exists() and result.success:
            probe = subprocess.run(['ffprobe','-v','error','-show_streams','-show_format',
                '-of','json',str(output)], capture_output=True, text=True, check=True, timeout=15)
            info = json.loads(probe.stdout)
            stream = next(s for s in info['streams'] if s['codec_type']=='video')
            subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],
                capture_output=True, check=True, timeout=30)
            samples=[]
            for second in ((0.5,2.5,4.5) if transition=='cut' else (0.5,1.5,2.5,3.5)):
                raw = subprocess.run(['ffmpeg','-v','error','-ss',str(second),'-i',str(output),
                    '-frames:v','1','-vf','scale=1:1','-pix_fmt','rgb24','-f','rawvideo','-'],
                    capture_output=True, check=True, timeout=15).stdout
                samples.append({'second':second,'rgb':list(raw[:3])})
            record.update({'frames':int(stream['nb_frames']), 'samples':samples,
                'duration':float(info['format']['duration']), 'decodes':True,
                'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                'exact_duration':int(stream['nb_frames'])==expected_frames})
        results.append(record)
    report={'candidate':'OpenMontage',
        'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.application,text=True).strip(),
        'scope':'one local montage tool; no director or complete project qualification',
        'provider_calls':0,'artistic_pilot':False,'results':results}
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
