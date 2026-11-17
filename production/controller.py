"""Single owner-local controller for durable, CPU-only order preparation."""
import fcntl
import logging
from threading import Event, Thread

from .core import Cancelled, ProductionError, number
from .preparation import prepare_order


class PreparationController:
    def __init__(self, intake, *, timeout=300, python=None, model_path=None, model='small'):
        self.intake = intake
        self.options = dict(timeout=number(timeout, 'timeout', 0.1, 3600),
                            python=python, model_path=model_path, model=model)
        self.stop = Event()
        self.ready = Event()
        self.thread = Thread(target=self.run, name='order-preparation')
        self.lock = (intake.root / 'controller.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.lock.close()
            raise ProductionError('Order controller already running') from exc

    def close(self):
        self.stop.set()
        self.ready.set()
        if self.thread.ident is not None:
            self.thread.join()
        self.lock.close()

    def run(self):
        try:
            with self.intake.connect() as db:
                db.execute("""UPDATE preparation_jobs SET status =
                    CASE WHEN attempts < 2 THEN 'queued' ELSE 'interrupted' END
                    WHERE status = 'running'""")
                db.execute("UPDATE preparation_jobs SET status='cancelled' WHERE status='cancelling'")
            while not self.stop.is_set():
                self.ready.clear()
                with self.intake.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    job = db.execute("""SELECT order_id FROM preparation_jobs
                        WHERE status='queued' ORDER BY rowid LIMIT 1""").fetchone()
                    if job:
                        db.execute("""UPDATE preparation_jobs SET status='running', attempts=attempts+1
                            WHERE order_id=?""", job)
                if job:
                    self.prepare(job[0])
                else:
                    self.ready.wait(1)
        except Exception:
            logging.exception('Order preparation controller failed')

    def prepare(self, ident):
        def cancelled():
            if self.stop.is_set():
                return True
            with self.intake.connect() as db:
                return db.execute('SELECT status FROM preparation_jobs WHERE order_id=?',
                                  (ident,)).fetchone()[0] == 'cancelling'

        try:
            receipt = prepare_order(self.intake.root, ident, should_cancel=cancelled, **self.options)
            status = ('awaiting_review' if receipt['status'] == 'prepared_for_review'
                      else receipt['status'])
        except Cancelled:
            status = 'timed_out'
        except Exception:
            logging.exception('Order preparation failed for %s', ident)
            status = 'failed'

        with self.intake.connect() as db:
            db.execute("""UPDATE preparation_jobs SET status=CASE
                WHEN status='cancelling' THEN 'cancelled'
                WHEN ? AND ?='timed_out' AND attempts < 2 THEN 'queued'
                ELSE ? END WHERE order_id=?""",
                (self.stop.is_set(), status, status, ident))
