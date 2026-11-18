"""Compatibility entry point for the pinned existing Intake, without editing PR2.

The original order bytes, not derived analysis/status fields, bind preparation.
The original HTTP server still owns authentication, range reads and controller.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import signal
from threading import Lock
from uuid import UUID

from production import intake as backend
from production.core import ProductionError, object_digest, read_json

ORDERS_IMPLEMENTATION = '9f5ee1afe7d2ba298f08365fbd590e8857a5d835c76da1747d12df16b7fd9d05'
BaseIntake = backend.Intake
_construction_lock = Lock()


def ensure_supported():
    observed=hashlib.sha256(inspect.getsource(BaseIntake.orders).encode()).hexdigest()
    if observed != ORDERS_IMPLEMENTATION:
        raise ProductionError('Intake implementation changed; requalify the receipt compatibility adapter')


class CurrentReceiptIntake(BaseIntake):
    def orders(self):
        ensure_supported()
        views=super().orders()
        with self.connect() as db:
            raw={ident:json.loads(data) for ident,data in db.execute('SELECT id,data FROM orders')}
        for view in views:
            ident=str(UUID(view['id']));source=raw.get(ident)
            if source is None:raise ProductionError('Order disappeared during read')
            # Ignore only fields that the existing server derives for display.
            stable={k:v for k,v in source.items() if k not in {'status','analysis','preparation','transcript'}}
            if any(view.get(k)!=v for k,v in stable.items()):
                raise ProductionError('Order changed during metadata read')
            receipt_path=self.root/'preparations'/ident/'receipt.json'
            prep=dict(view.get('preparation',{}))
            for field in ['reference_count','blocker']:prep.pop(field,None)
            if receipt_path.is_file():
                receipt=read_json(receipt_path)
                if receipt.get('order_sha256')==object_digest(source):
                    prep.update(reference_count=len(receipt.get('reference_evidence',[])),blocker=receipt.get('blocker'))
                    prep.setdefault('status',receipt['status'])
            if prep:view['preparation']=prep
        return views


def server(root,port,**options):
    """Inject only the read model while constructing this isolated application."""
    ensure_supported()
    with _construction_lock:
        previous=backend.Intake
        try:
            backend.Intake=CurrentReceiptIntake
            return backend.server(root,port,**options)
        finally:
            backend.Intake=previous


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--port',type=int,default=18117)
    p.add_argument('--preparation-timeout',type=float,default=300)
    p.add_argument('--speech-python',type=Path);p.add_argument('--speech-model-path',type=Path)
    p.add_argument('--speech-model',choices=['tiny','small'],default='small')
    args=p.parse_args()
    def stop(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    with server(args.root,args.port,timeout=args.preparation_timeout,python=args.speech_python,
                model_path=args.speech_model_path,model=args.speech_model) as http:
        try:http.serve_forever()
        except KeyboardInterrupt:pass


if __name__=='__main__':main()
