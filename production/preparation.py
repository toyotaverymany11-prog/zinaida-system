"""Bounded preparation of one saved order, with durable evidence and no generation.

No global queue or daemon is created. The owning controller invokes this worker
for a particular order. Repeated execution verifies and reuses completed work.
"""
import argparse
import fcntl
import json
from pathlib import Path
import time
from uuid import UUID, uuid4

from .core import ProductionError, Runtime, digest, local_asset, object_digest, read_json, write_json
from .intake import Intake
from .local_transcription import transcribe
from .media import inspect_video


def verified(root, item):
    try:
        return bool(item.get('files')) and all(
            digest(local_asset(root,f['path']))==f['sha256'] for f in item['files'])
    except (OSError,ProductionError,KeyError,TypeError):
        return False


def prepare_order(root, order_id, *, python=None, model_path=None, model='small',
                  timeout=300, cancel_file=None, max_samples=12):
    ident=str(UUID(order_id))
    if type(max_samples) is not int or not 2<=max_samples<=80:
        raise ProductionError('max_samples must be 2..80')
    intake=Intake(root)
    runtime=Runtime(timeout,cancel_file)
    with intake.connect() as db:
        row=db.execute('SELECT data FROM orders WHERE id=?',(ident,)).fetchone()
    if not row:
        raise ProductionError('Unknown order')
    order=json.loads(row[0])
    fingerprint=object_digest(order)
    output=intake.root/'preparations'/ident
    output.mkdir(parents=True,exist_ok=True)
    with (output/'worker.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: raise ProductionError('Order preparation already running') from exc
        receipt_path=output/'receipt.json'
        previous=read_json(receipt_path) if receipt_path.exists() else {}
        if previous and previous.get('order_sha256')!=fingerprint:
            raise ProductionError('Stored order changed; a new revision is required')
        receipt={'order_id':ident,'order_sha256':fingerprint,'status':'running',
            'attempt_id':str(uuid4()),'started_at':time.time(),'reference_evidence':[],
            'semantic_review':'not_performed','generation_authorized':False,'provider_calls':0}
        write_json(receipt_path,receipt)
        try:
            runtime.check()
            # Verify even attachments that do not need video processing.
            for a in [*order['references'],*order['characters'],*([order['voice']] if order.get('voice') else [])]:
                runtime.check()
                intake.asset(a['id'])
            cached={e['asset_id']:e for e in previous.get('reference_evidence',[])}
            for a in order['references']:
                if a['kind']!='video': continue
                runtime.check()
                item=cached.get(a['id'])
                if not item or item.get('max_samples')!=max_samples or not verified(intake.root,item):
                    folder=output/receipt['attempt_id']/a['id']
                    report=inspect_video(intake.root/'assets'/a['id'],folder,runtime,max_samples)
                    item={'asset_id':a['id'],'max_samples':max_samples,'analysis_path':str((folder/'analysis.json').relative_to(intake.root)),
                        'source_sha256':report['source_sha256'],'files':[
                            {'path':str(f.relative_to(intake.root)),'sha256':digest(f)}
                            for f in sorted(folder.rglob('*')) if f.is_file()]}
                receipt['reference_evidence'].append(item)
                write_json(receipt_path,receipt)
            if order.get('voice'):
                if python is None or model_path is None:
                    receipt.update(status='blocked',blocker='Local speech runtime is not configured')
                    write_json(receipt_path,receipt)
                    return receipt
                runtime.check()
                transcript=transcribe(intake.root,ident,python,model_path,model,runtime=runtime)
                receipt['transcript']={'path':f'transcripts/{ident}.json',
                    'sha256':digest(intake.root/'transcripts'/f'{ident}.json'),
                    'status':transcript['status']}
            runtime.check()
            receipt.update(status='prepared_for_review',finished_at=time.time(),
                required_next=['Review original intent and any transcript',
                    'Analyze actual reference action, timing, camera and invariants',
                    'Approve a scene plan and separate any billable execution budget'])
            write_json(receipt_path,receipt)
            return receipt
        except BaseException as exc:
            receipt.update(status='failed_or_cancelled',error=str(exc),finished_at=time.time())
            write_json(receipt_path,receipt)
            raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description='Prepare one order without generation or paid calls')
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--order-id',required=True)
    p.add_argument('--python',type=Path)
    p.add_argument('--model-path',type=Path)
    p.add_argument('--model',choices=['tiny','small'],default='small')
    p.add_argument('--timeout',type=float,default=300)
    p.add_argument('--cancel-file',type=Path)
    p.add_argument('--max-samples',type=int,default=12)
    a=p.parse_args()
    print(json.dumps(prepare_order(a.root,a.order_id,python=a.python,model_path=a.model_path,
        model=a.model,timeout=a.timeout,cancel_file=a.cancel_file,max_samples=a.max_samples),ensure_ascii=False))
