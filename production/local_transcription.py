"""Transcribe an intake recording using an explicitly installed local Whisper.

No model downloads, API credentials, GPU allocation or automatic brief approval.
The original recording and written order remain unchanged.
"""
import argparse
import json
import fcntl
import os
from uuid import uuid4
from pathlib import Path
from uuid import UUID

from .core import ProductionError, Runtime, digest, probe, read_json, write_json
from .intake import Intake

MODEL_SHA = {
    'small': '9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794',
    'tiny': '65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9',
}


def transcribe(root, order_id, python, model_path, model='small', timeout=180, runtime=None,
               expected_sha256=None):
    ident = str(UUID(order_id))
    folder = Path(root).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f'transcription-{ident}.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProductionError('Transcription already running') from exc
        return _transcribe(root, ident, python, model_path, model, timeout, runtime, expected_sha256)


def _transcribe(root, order_id, python, model_path, model, timeout, runtime, expected_sha256):
    ident=str(UUID(order_id))
    intake=Intake(root)
    with intake.connect() as db:
        row=db.execute('SELECT data FROM orders WHERE id=?',(ident,)).fetchone()
    if not row:
        raise ProductionError('Unknown order')
    order=json.loads(row[0])
    if not order.get('voice'):
        raise ProductionError('Order has no voice recording')
    runtime = runtime or Runtime(timeout)
    asset=intake.asset(order['voice']['id'], runtime)
    target=intake.root/'transcripts'/f'{ident}.json'
    runtime.check()
    checksum = target.with_suffix('.sha256')
    if target.exists():
        known_hash = expected_sha256
        if known_hash is None and checksum.is_file():
            known_hash = checksum.read_text().strip()
        if known_hash and digest(target, runtime) == known_hash:
            previous = read_json(target)
            if (previous.get('source_sha256') == asset['id']
                    and previous.get('model') == model
                    and previous.get('order_id') == ident):
                return previous
        # Keep the previous derived text for audit, then regenerate from source.
        archive = target.parent / 'history'
        archive.mkdir(exist_ok=True)
        backup = archive / f'{ident}-{uuid4()}.json'
        os.link(target, backup)
    if model not in MODEL_SHA or not model_path.is_file() or digest(model_path, runtime)!=MODEL_SHA[model]:
        raise ProductionError('Expected official cached Whisper weights; automatic download is disabled')
    source=intake.root/'assets'/asset['id']
    duration=float(probe(source,runtime)['format'].get('duration',0))
    if not 0<duration<=120:
        raise ProductionError('Voice orders are limited to 120 seconds')
    result=json.loads(runtime.run([str(python),str(Path(__file__).with_name('whisper_child.py')),
        '--source',str(source),'--model',str(model_path)]))
    if digest(source,runtime)!=asset['id']:
        raise ProductionError('Recording changed during transcription')
    report={'order_id':ident,'source_sha256':asset['id'],'model':model,
        'model_sha256':MODEL_SHA[model], 'status':'draft_needs_review','provider_calls':0,
        'duration_seconds':duration,**result}
    write_json(target,report)
    checksum.write_text(digest(target, runtime) + '\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--order-id',required=True)
    p.add_argument('--python',type=Path,required=True)
    p.add_argument('--model-path',type=Path,required=True)
    p.add_argument('--model',choices=MODEL_SHA,default='small')
    p.add_argument('--timeout',type=float,default=180)
    a=p.parse_args()
    print(json.dumps(transcribe(a.root,a.order_id,a.python,a.model_path,a.model,a.timeout),ensure_ascii=False))
