"""Optional owner-only video observation for the existing Megamozg workboard.

Install in a reviewed app instance. No worker, schema migration or background task.
bindings and loader are trusted server dependencies, never request body fields.
"""
import asyncio
from aiohttp import web
from production.pult_link import binding, view


def install(app, store, bindings, loader):
    from team import active_request
    links = {key: binding(value) for key, value in bindings.items()}
    if any(key != value['task_id'] for key, value in links.items()):
        raise ValueError('invalid_task_binding')
    pending = None

    async def load_bounded(link):
        # wait_for cannot terminate a blocking filesystem thread. Keep the same
        # single-flight slot occupied after timeout until that read really ends.
        # Busy callers receive unavailable; never queue more background reads.
        nonlocal pending
        if pending is not None and not pending.done():
            return None
        if pending is not None:
            pending.exception()  # retrieve an error from a previously timed-out read
        pending = asyncio.create_task(asyncio.to_thread(loader, link))
        return await asyncio.wait_for(asyncio.shield(pending), timeout=1.5)

    async def observe(request):
        with store.db() as db:
            user = active_request(db, request)
            if user['role'] not in {'owner','employee'} or request.get('agent_authenticated'):
                raise web.HTTPForbidden(text='owner_required')
            row = db.execute('SELECT id,revision,created_by,assignee_user_id,assignee_kind FROM team_tasks WHERE id=?',
                             (request.match_info['id'],)).fetchone()
            if not row:
                raise web.HTTPNotFound(text='work_item_not_found')
            link = links.get(row['id'])
            if link is None:
                return web.json_response({'state': 'not_bound', 'read_only': True, 'can_execute': False})
            if row['created_by'] != link['owner_id'] or not (
                    (user['role']=='owner' and link['owner_id']==user['id']) or
                    (user['role']=='employee' and row['assignee_kind']=='human' and row['assignee_user_id']==user['id'])):
                raise web.HTTPForbidden(text='owner_required')
            if link['task_revision'] != row['revision']:
                return web.json_response({'state': 'binding_stale', 'read_only': True, 'can_execute': False})
        try:
            snapshot = await load_bounded(link)
        except asyncio.CancelledError:
            raise
        except Exception:
            snapshot = None
        # Revalidate identity and revision after the bounded asynchronous read.
        with store.db() as db:
            current = active_request(db, request)
            row = db.execute('SELECT revision,created_by,assignee_user_id,assignee_kind FROM team_tasks WHERE id=?', (link['task_id'],)).fetchone()
            if not row or row['created_by']!=link['owner_id'] or not (
                    (current['role']=='owner' and current['id']==link['owner_id']) or
                    (current['role']=='employee' and row['assignee_kind']=='human' and row['assignee_user_id']==current['id'])):
                raise web.HTTPForbidden(text='owner_required')
            if row['revision'] != link['task_revision']:
                return web.json_response({'state': 'binding_stale', 'read_only': True, 'can_execute': False})
        return web.json_response(view(snapshot, link), headers={'Cache-Control': 'no-store'})

    app.router.add_get('/api/workboard/tasks/{id}/video', observe)
