"""Prepare one explicit binding from a read-only pult DB; never create a task.

Run as the trusted operator, not as a browser handler. Publication/installation
is separate and must revalidate the task revision through video_routes.
"""
from contextlib import closing
from pathlib import Path
import sqlite3
from production.pult_link import binding


def prepare(database, *, task_id, task_revision, owner_id, order_id, order_fingerprint):
    link=binding(dict(task_id=task_id,task_revision=task_revision,owner_id=owner_id,
                      order_id=order_id,order_fingerprint=order_fingerprint))
    path=Path(database).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():
        raise ValueError('untrusted_database')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=0.5)) as db:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        user=db.execute('SELECT role,active FROM users WHERE id=?',(owner_id,)).fetchone()
        row=db.execute('SELECT revision,created_by,assignee_user_id,assignee_kind FROM team_tasks WHERE id=?',(task_id,)).fetchone()
        if not user or user[0]!='owner' or user[1]!=1:
            raise ValueError('active_owner_required')
        if not row or row[0]!=task_revision or row[1]!=owner_id:
            raise ValueError('task_binding_mismatch')
        if row[2]!=owner_id or row[3]!='human':
            raise ValueError('owner_human_task_required')
    return link
