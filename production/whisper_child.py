"""Runs in the operator-selected Python containing the installed Whisper package."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True)
    a=p.parse_args()
    # Passing a resolved file, never a model alias, prevents implicit downloads.
    model_path=a.model.resolve(strict=True)
    import torch
    import whisper
    torch.set_num_threads(2)
    model=whisper.load_model(str(model_path),device='cpu')
    result=model.transcribe(str(a.source.resolve(strict=True)),language='ru',fp16=False,
        temperature=0,condition_on_previous_text=False,verbose=None)
    print(json.dumps({'text':result['text'].strip(),'language':result.get('language'),
        'segments':[{key:s[key] for key in ('start','end','text','avg_logprob','no_speech_prob')}
                    for s in result.get('segments',[])]},ensure_ascii=False))


if __name__=='__main__': main()
