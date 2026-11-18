"""Exact-file technical observations. No image metric certifies artistic quality."""
from pathlib import Path
from fractions import Fraction
import argparse
import hashlib
import json
import subprocess
import numpy as np


def audio_samples(path, seconds=60):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-t',str(seconds),
        '-vn','-ac','1','-ar','16000','-f','f32le','-'],timeout=90)
    return np.frombuffer(raw,dtype='<f4')


def compare_speech(source, movie):
    """Waveform preservation and track offset, explicitly not mouth synchronization."""
    a,b=audio_samples(source),audio_samples(movie)
    n=min(len(a),len(b))
    if n<1600:raise ValueError('Too little actual audio')
    a,b=a[:n],b[:n]
    best=(-2,0)
    # Search +/-100ms, first at2ms resolution and then at a single sample.
    def correlation(lag):
        x,y=(a[lag:],b[:-lag]) if lag>0 else (a[:lag],b[-lag:]) if lag<0 else (a,b)
        denom=float(np.linalg.norm(x)*np.linalg.norm(y))
        return float(np.dot(x,y)/denom) if denom>1e-12 else 0
    for lag in range(-1600,1601,32):
        score=correlation(lag)
        if score>best[0]:best=(score,lag)
    for lag in range(max(-1600,best[1]-31),min(1600,best[1]+31)+1):
        score=correlation(lag)
        if score>best[0]:best=(score,lag)
    return {'source_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
            'normalized_correlation':best[0],'source_offset_samples':best[1],
            'source_offset_ms':best[1]/16,'compared_seconds':n/16000,
            'mouth_sync_measured':False,'words_or_voice_identity_verified':False}


def ranges(indices):
    out=[]
    for i in indices:
        if out and i==out[-1][1]+1:out[-1][1]=i
        else:out.append([i,i])
    return out


def inspect(path, speech=None):
    path=Path(path)
    metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames',
        '-show_streams','-show_format','-of','json',str(path)],timeout=90))
    video=next(s for s in metadata['streams'] if s['codec_type']=='video')
    fps=float(Fraction(video['avg_frame_rate']))
    duration=float(metadata['format']['duration'])
    if duration>60 or not 1<=fps<=120:raise ValueError('Qualification clip outside finite bounds')
    # Every decoded frame is inspected, including defects shorter than model sampling.
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0',
        '-vf','scale=128:72:flags=area,format=gray','-fps_mode','passthrough',
        '-f','rawvideo','-'],timeout=90)
    if len(raw)%(128*72):raise ValueError('Incomplete decoded frame')
    frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,72,128)
    expected=int(video.get('nb_read_frames',len(frames)))
    if len(frames)!=expected:raise ValueError('Decoder frame count disagreement')
    mean=frames.mean(axis=(1,2));dark=(frames<12).mean(axis=(1,2))
    delta=np.abs(np.diff(frames.astype(np.int16),axis=0)).mean(axis=(1,2))
    # A candidate flash needs visible context on BOTH sides. Intentional cuts still need review.
    black=ranges(np.flatnonzero((dark>.98)&(mean<10)).tolist())
    flashes=[]
    for start,end in black:
        if start>0 and end<len(frames)-1 and end-start+1<=3 and mean[start-1]>35 and mean[end+1]>35:
            flashes.append({'start_frame':start,'end_frame_inclusive':end,'start':start/fps,
                'end':(end+1)/fps,'stage':'editing','severity':'major','modality':'visual',
                'expected':'Continuous intended image or explicitly planned cut',
                'observed':'Brief near-black interval between brighter frames',
                'evidence':f'All frames decoded; near-black frames {start}..{end}',
                'change':'Inspect this exact interval; replace accidental blank frames at the edit source',
                'recheck':'Decode corrected version and verify this interval against the intended transition'})
    result={'artifact_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'bytes':path.stat().st_size,'duration_seconds':duration,'fps':fps,
        'decoded_frames':len(frames),'all_frames_inspected':True,'metadata':metadata,
        'observations':{'near_black_ranges':black,'low_change_ranges':ranges((np.flatnonzero(delta<.08)+1).tolist()),
                        'low_change_is_not_automatic_rejection':True},
        'candidate_findings':flashes,'artistic_approval':False,'lip_sync_qualified':False}
    if speech:result['source_audio_comparison']=compare_speech(speech,path)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--video',required=True);p.add_argument('--speech');p.add_argument('--output',required=True)
    a=p.parse_args();r=inspect(a.video,a.speech);Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps({k:r[k] for k in ['artifact_sha256','decoded_frames','candidate_findings','artistic_approval']}))
