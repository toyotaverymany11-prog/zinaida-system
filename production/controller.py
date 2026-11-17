"""Single owner-local controller for durable, CPU-only order preparation."""
import fcntl
import logging
from threading import Event, Thread
from uuid import uuid4

from .core import Cancelled, ProductionError, number
from .preparation import prepare_order


class PreparationController:
    def __init__(self, intake, *, timeout=300, python=None, model_path=None, model='small',
                 planner=None, analysis_timeout=180):
        self.intake = intake
        self.options = dict(timeout=number(timeout, 'timeout', 0.1, 3600),
                            python=python, model_path=model_path, model=model)
        self.failure = None
        self.planner = planner
        self.analysis_timeout = number(analysis_timeout, 'analysis timeout', 0.1, 600)
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
                db.execute("UPDATE preparation_jobs SET analysis_status='recovering' WHERE analysis_status='running'")
                db.execute("UPDATE preparation_jobs SET analysis_status='cancelled' WHERE analysis_status='cancelling'")
            while not self.stop.is_set():
                self.ready.clear()
                with self.intake.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    job = db.execute("""SELECT order_id FROM preparation_jobs
                        WHERE status='queued' ORDER BY rowid LIMIT 1""").fetchone()
                    if job:
                        db.execute("""UPDATE preparation_jobs SET status='running', attempts=attempts+1
                            WHERE order_id=?""", job)
                    analysis = None
                    if not job and self.planner is not None:
                        analysis = db.execute("""SELECT order_id,analysis_request_id,analysis_status FROM preparation_jobs
                            WHERE analysis_status IN ('queued','recovering') ORDER BY rowid LIMIT 1""").fetchone()
                        if analysis:
                            db.execute("UPDATE preparation_jobs SET analysis_status='running' WHERE order_id=?", (analysis[0],))
                if job:
                    self.prepare(job[0])
                elif analysis:
                    self.analyze(*analysis)
                else:
                    self.ready.wait(1)
        except Exception:
            self.failure = 'Подготовка остановилась из-за ошибки контроллера. Требуется перезапуск локального окна.'
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
            if status == 'awaiting_review' and self.planner is not None:
                row = db.execute('SELECT analysis_status,status FROM preparation_jobs WHERE order_id=?',(ident,)).fetchone()
                if row == ('not_requested','awaiting_review'):
                    request_id = str(uuid4())
                    db.execute('INSERT INTO analysis_requests VALUES (?,?)',(request_id,ident))
                    db.execute("UPDATE preparation_jobs SET analysis_status='queued',analysis_request_id=? WHERE order_id=?",
                               (request_id,ident))

    def analyze(self, ident, request_id, previous_status):
        from .analysis import analyze_order, OutcomeUnknown
        def cancelled():
            with self.intake.connect() as db:
                row = db.execute('SELECT analysis_status FROM preparation_jobs WHERE order_id=?',(ident,)).fetchone()
            return self.stop.is_set() or row[0] == 'cancelling'
        error = None
        try:
            analyze_order(self.intake.root, ident, request_id, self.planner,
                          timeout=self.analysis_timeout, should_cancel=cancelled,
                          recover_only=previous_status == 'recovering')
            status = 'needs_review'
        except OutcomeUnknown:
            status, error = 'interrupted', 'Разбор прерван. Автоматический повтор отключён; можно явно повторить.'
        except Cancelled:
            status, error = 'timed_out', 'Разбор остановлен по ограничению времени или остановке окна.'
        except Exception:
            status, error = 'failed', 'Не получен корректный план. Материалы сохранены, доступен явный повтор разбора.'
            logging.exception('Visual analysis failed for %s',ident)
        with self.intake.connect() as db:
            db.execute("""UPDATE preparation_jobs SET analysis_status=CASE
                WHEN analysis_status='cancelling' THEN 'cancelled' ELSE ? END, analysis_error=? WHERE order_id=?""",
                (status,error,ident))
