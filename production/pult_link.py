"""Read-only, bounded projection of one explicitly bound video order.

Never construct Intake here: its constructor migrates the source database.
The trusted exporter supplies roots and bindings; browser input supplies neither.
This projection is not a second queue and cannot authorize or accept production.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from uuid import UUID

SCHEMA = 'video.order-observation.v1'
MAX_BYTES = 65536
STATES = {'queued', 'running', 'recovering', 'cancelling', 'cancelled', 'failed',
          'blocked', 'awaiting_review', 'not_requested', 'ready', 'unavailable'}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def binding(value):
    fields = {'task_id', 'task_revision', 'owner_id', 'order_id', 'order_fingerprint'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('invalid_binding')
    for name in ('task_id', 'order_id'):
        if str(UUID(value[name])) != value[name]:
            raise ValueError('invalid_binding')
    if type(value['task_revision']) is not int or value['task_revision'] < 1:
        raise ValueError('invalid_binding')
    if not isinstance(value['owner_id'], str) or not 1 <= len(value['owner_id']) <= 100:
        raise ValueError('invalid_binding')
    if not re.fullmatch('[a-f0-9]{64}', value['order_fingerprint']):
        raise ValueError('invalid_binding')
    return dict(value)


def decode(raw):
    if not isinstance(raw, (str, bytes)) or len(raw) > MAX_BYTES:
        raise ValueError('invalid_source')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid_number')))


def collect(root, link, *, now=None):
    """Read one SQLite transaction. Errors never become a successful empty order."""
    link = binding(link)
    now = time.time() if now is None else now
    result = {'schema': SCHEMA, 'binding': link, 'observed_at': now,
              'state': 'unavailable', 'preparation': 'unavailable',
              'analysis': 'unavailable', 'preview': 'unavailable',
              'plan_revision': None, 'plan_review': 'not_observed',
              'read_only': True, 'finished_video_accepted': False}
    path = Path(root).absolute() / 'intake.sqlite3'
    try:
        # Roots are trusted configuration, but reject links rather than following them.
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            return result
        before = path.stat()
        deadline = time.monotonic() + 0.75
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=0.5)) as db:
            db.execute('PRAGMA query_only=ON')
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            db.execute('BEGIN')
            row = db.execute('SELECT fingerprint,data FROM orders WHERE id=?', (link['order_id'],)).fetchone()
            if not row or row[0] != link['order_fingerprint']:
                return dict(result, state='binding_mismatch')
            order = decode(row[1])
            original = {k: v for k, v in order.items() if k != 'created_at'}
            if order.get('id') != link['order_id'] or fingerprint(original) != row[0]:
                return dict(result, state='binding_mismatch')
            job = db.execute('SELECT status,analysis_status,preview_status FROM preparation_jobs WHERE order_id=?',
                             (link['order_id'],)).fetchone()
            if job:
                for key, value in zip(('preparation', 'analysis', 'preview'), job):
                    result[key] = value if value in STATES else 'unavailable'
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'scene_plans' in tables:
                plan = db.execute('SELECT revision,data FROM scene_plans WHERE order_id=? ORDER BY revision DESC LIMIT 1',
                                  (link['order_id'],)).fetchone()
                if plan:
                    data = decode(plan[1])
                    if type(plan[0]) is not int or plan[0] < 1 or data['order_id'] != link['order_id'] or data['revision'] != plan[0]:
                        raise ValueError('invalid_plan')
                    result.update(plan_revision=plan[0], plan_review='pending')
                    if 'plan_reviews' in tables:
                        review = db.execute('SELECT data FROM plan_reviews WHERE order_id=? AND revision=? ORDER BY rowid DESC LIMIT 1',
                                            (link['order_id'], plan[0])).fetchone()
                        if review:
                            decision = decode(review[0])
                            if (decision.get('order_id') == link['order_id'] and decision.get('revision') == plan[0]
                                    and decision.get('packet_sha256') == data.get('packet_sha256')):
                                # The exporter does not hash all current evidence/media.
                                # Report only the recorded decision, never current approval.
                                result['plan_review'] = {'accept_plan': 'recorded_acceptance_unverified', 'request_changes': 'changes_requested'}.get(decision.get('decision'), 'pending')
        after = path.stat()
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError('database_replaced')
        result['state'] = 'observed'
        return result
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        return dict(result, state='unavailable', preparation='unavailable', analysis='unavailable',
                    preview='unavailable', plan_revision=None, plan_review='not_observed')


def view(snapshot, link, *, now=None, max_age=180):
    """Whitelist only. No source paths, briefs, tokens, media URLs or review notes."""
    link = binding(link)
    now = time.time() if now is None else now
    empty = {'state': 'unavailable', 'observed_at': None, 'age_seconds': None,
             'preparation': 'unavailable', 'analysis': 'unavailable', 'preview': 'unavailable',
             'plan_revision': None, 'plan_review': 'not_observed',
             'read_only': True, 'finished_video_accepted': False, 'can_execute': False,
             'evidence_current': False}
    if not isinstance(snapshot, dict) or snapshot.get('schema') != SCHEMA or snapshot.get('binding') != link:
        return empty
    stamp = snapshot.get('observed_at')
    if type(stamp) not in (int, float) or not 0 < stamp <= now + 5:
        return empty
    state = snapshot.get('state')
    if state not in {'observed', 'unavailable', 'binding_mismatch'}:
        return empty
    if snapshot.get('read_only') is not True or snapshot.get('finished_video_accepted') is not False:
        return empty
    if state != 'observed':
        return dict(empty, state=state, observed_at=stamp, age_seconds=max(0, int(now-stamp)))
    if any(snapshot.get(key) not in STATES for key in ('preparation', 'analysis', 'preview')):
        return empty
    revision = snapshot.get('plan_revision')
    if revision is not None and (type(revision) is not int or revision < 1):
        return empty
    review = snapshot.get('plan_review')
    if review not in {'not_observed', 'pending', 'recorded_acceptance_unverified', 'changes_requested'}:
        return empty
    return dict(empty, state='stale' if now-stamp > max_age else 'observed', observed_at=stamp,
                age_seconds=max(0, int(now-stamp)), plan_revision=revision, plan_review=review,
                **{k: snapshot[k] for k in ('preparation', 'analysis', 'preview')})
