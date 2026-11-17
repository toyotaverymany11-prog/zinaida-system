import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from production.controller import PreparationController
from production.core import Cancelled, ProductionError
from production.intake import Intake


class ControllerTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.intake = Intake(Path(folder.name), enqueue=True)

    def order(self):
        data = {'request_id': str(uuid4()), 'mode': 'new_video', 'brief': 'Проверка'}
        self.assertEqual(self.intake.create(data), self.intake.create(data))
        return data['request_id']

    def state(self, ident):
        with self.intake.connect() as db:
            return db.execute('SELECT status, attempts FROM preparation_jobs WHERE order_id=?',
                              (ident,)).fetchone()

    def start(self):
        controller = PreparationController(self.intake, timeout=2)
        self.addCleanup(controller.close)
        controller.thread.start()
        return controller

    def test_recovery_claims_once_and_reaches_review(self):
        ident = self.order()
        with self.intake.connect() as db:
            db.execute("UPDATE preparation_jobs SET status='running', attempts=1")
        controller = self.start()
        with self.assertRaisesRegex(ProductionError, 'already running'):
            PreparationController(self.intake)
        self.wait_state(ident, 'awaiting_review')
        self.assertEqual(self.state(ident), ('awaiting_review', 2))
        controller.close()

    def wait_state(self, ident, expected):
        for _ in range(100):
            if self.state(ident)[0] == expected:
                return
            Event().wait(0.02)
        self.fail(f'Expected {expected}, got {self.state(ident)}')

    def test_cancel_queued_and_active_orders(self):
        queued = self.order()
        self.assertEqual(self.intake.cancel_preparation(queued)['status'], 'cancelled')
        active = self.order()
        entered = Event()
        resume = Event()

        def prepare(root, ident, *, should_cancel, **options):
            self.assertEqual(ident, active)
            entered.set()
            if resume.wait(2) and should_cancel():
                raise Cancelled()
            raise AssertionError('Active preparation was not cancelled')

        with patch('production.controller.prepare_order', side_effect=prepare) as worker:
            controller = self.start()
            try:
                self.assertTrue(entered.wait(2))
                self.assertEqual(self.intake.cancel_preparation(active)['status'], 'cancelling')
                resume.set()
                self.wait_state(active, 'cancelled')
            finally:
                resume.set()
                controller.close()
        self.assertEqual(worker.call_count, 1)
        self.assertEqual(self.state(queued), ('cancelled', 0))
        self.assertEqual(self.state(active), ('cancelled', 1))

    def test_timeout_is_terminal(self):
        ident = self.order()
        with patch('production.controller.prepare_order', side_effect=Cancelled) as worker:
            controller = self.start()
            try:
                self.wait_state(ident, 'timed_out')
            finally:
                controller.close()
        self.assertEqual(worker.call_count, 1)

    def test_explicit_retry_is_durable_and_does_not_rearm_completed_work(self):
        ident = self.order()
        self.intake.cancel_preparation(ident)
        request = str(uuid4())
        self.intake.retry_preparation(ident, request)
        controller = self.start()
        self.wait_state(ident, 'awaiting_review')
        controller.close()
        self.intake.retry_preparation(ident, request)
        self.assertEqual(self.state(ident), ('awaiting_review', 1))
