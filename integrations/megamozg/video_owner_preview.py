"""Owner-only draft viewing. No acceptance, publication, rendering or model calls."""
import asyncio
import hashlib
import os
from pathlib import Path
import re
import stat
from aiohttp import web
from production.pult_link import binding, collect
from video_media import MAX_MEDIA_BYTES, interval

LABEL = 'Черновик, проверка не завершена'
FLAGS = {'status': 'draft', 'label': LABEL, 'finished_video_accepted': False,
         'ready_for_owner': False, 'publication_authorized': False}
KINDS = {'owner_draft_catalog', 'owner_draft_video'}


def _flags(packet):
    if any(packet.get(key) != value for key, value in FLAGS.items()):
        raise ValueError('invalid_draft_status')
    if any(packet.get(key) is not False for key in
           ('finished_video_accepted', 'ready_for_owner', 'publication_authorized')):
        raise ValueError('invalid_draft_acceptance')


def owner_draft_producer(root, link, request_id, allowed):
    """Trusted exact revision->SHA allowlist, separate from the candidate producer."""
    from production.scene_revision import revision_file
    root = Path(root); link = binding(link)
    if (not isinstance(allowed, dict) or not 1 <= len(allowed) <= 20
            or any(not isinstance(k, str) or not re.fullmatch('[a-f0-9]{64}', k)
                   or not isinstance(v, str) or not re.fullmatch('[a-f0-9]{64}', v)
                   for k, v in allowed.items())):
        raise ValueError('explicit_draft_allowlist_required')
    allowed = dict(allowed)

    def current(expected, revision):
        if expected != link or collect(root, link)['state'] != 'observed':
            raise ValueError('order_changed')
        if revision not in allowed:
            raise ValueError('unknown_draft_revision')
        return Path(revision_file(root, link['order_id'], request_id,
                                  revision, 'video')).absolute()

    def read_one(expected, revision):
        path = current(expected, revision)
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('media_link')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_MEDIA_BYTES:
                raise ValueError('media_size')
            chunks = []; remaining = before.st_size
            while remaining:
                chunk = os.read(fd, min(remaining, 1024 * 1024))
                if not chunk:
                    raise ValueError('media_short_read')
                chunks.append(chunk); remaining -= len(chunk)
            data = b''.join(chunks); after = os.fstat(fd)
            if ((before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size)
                    != (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)):
                raise ValueError('media_changed')
            sha = hashlib.sha256(data).hexdigest()
            if sha != allowed[revision]:
                raise ValueError('draft_sha_changed')
            again = current(expected, revision)
            if again != path:
                raise ValueError('media_path_changed')
            latest = again.stat()
            if ((latest.st_dev, latest.st_ino, latest.st_mtime_ns, latest.st_size)
                    != (before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size)):
                raise ValueError('media_changed')
            return data, sha
        finally:
            os.close(fd)

    def produce(expected, revision, kind):
        if kind == 'owner_draft_catalog':
            if revision is not None:
                raise ValueError('invalid_draft_revision')
            rows = []
            for item in sorted(allowed):
                data, sha = read_one(expected, item)
                rows.append({'revision': item, 'sha256': sha, 'bytes': len(data)})
            return {'binding': link, 'current': True, 'drafts': rows, **FLAGS}
        if kind != 'owner_draft_video':
            raise ValueError('invalid_draft_kind')
        data, sha = read_one(expected, revision)
        return {'binding': link, 'current': True, 'revision': revision, 'kind': kind,
                'sha256': sha, 'data': data, **FLAGS}
    return produce


def install(app, store, bindings, producer, *, _imported=False):
    """Explicit opt-in only. Existing video/catalog/project routes are unchanged."""
    from team import active_request
    id_key = 'artifact_id' if _imported else 'revision'
    catalog_kind = 'owner_imported_draft_catalog' if _imported else 'owner_draft_catalog'
    video_kind = 'owner_imported_draft_video' if _imported else 'owner_draft_video'
    row_keys = {id_key,'sha256','bytes'} | ({'title','source_kind','project_id','duration_seconds'} if _imported else set())
    links = {key: binding(value) for key, value in bindings.items()}
    if any(key != value['task_id'] for key, value in links.items()):
        raise ValueError('invalid_task_binding')
    pending = None

    def authorize(request, link):
        if not request.get('user'):
            raise web.HTTPUnauthorized(text='authentication_required')
        if request.get('agent_authenticated'):
            raise web.HTTPForbidden(text='owner_session_required')
        with store.db() as db:
            user = active_request(db, request, owner=True)
            row = db.execute('SELECT revision,created_by FROM team_tasks WHERE id=?',
                             (link['task_id'],)).fetchone()
            if (not row or row['created_by'] != link['owner_id']
                    or user['role'] != 'owner' or user['id'] != link['owner_id']):
                raise web.HTTPForbidden(text='owner_draft_access_denied')
            if row['revision'] != link['task_revision']:
                raise web.HTTPConflict(text='video_binding_stale')

    def selected(request):
        link = links.get(request.match_info['id'])
        if link is None:
            raise web.HTTPNotFound()
        authorize(request, link)
        return link

    async def load(link, revision, kind):
        nonlocal pending
        if producer is None:
            raise web.HTTPServiceUnavailable(text='draft_producer_not_installed')
        if pending is not None and not pending.done():
            raise web.HTTPServiceUnavailable(text='draft_read_busy')
        if pending is not None:
            pending.exception()
        pending = asyncio.create_task(asyncio.to_thread(producer, link, revision, kind))
        try:
            return await asyncio.wait_for(asyncio.shield(pending), timeout=5)
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            raise web.HTTPServiceUnavailable(text='draft_read_timeout') from None
        except Exception:
            raise web.HTTPConflict(text='draft_not_current') from None

    async def catalog(request):
        link = selected(request)
        packet = await load(link, None, catalog_kind)
        authorize(request, link)
        try:
            _flags(packet)
            if (set(packet) != {'binding','current','drafts',*FLAGS}
                    or packet['binding'] != link or packet['current'] is not True
                    or not isinstance(packet['drafts'], list) or len(packet['drafts']) > 20):
                raise ValueError('invalid_draft_catalog')
            rows = []; seen = set()
            for row in packet['drafts']:
                if (not isinstance(row, dict) or set(row) != row_keys
                        or not isinstance(row[id_key], str)
                        or not re.fullmatch('[a-f0-9]{64}', row[id_key])
                        or row[id_key] in seen or not isinstance(row['sha256'], str)
                        or not re.fullmatch('[a-f0-9]{64}', row['sha256'])
                        or type(row['bytes']) is not int
                        or not 0 < row['bytes'] <= MAX_MEDIA_BYTES):
                    raise ValueError('invalid_draft_catalog')
                if _imported and (row['source_kind']!='imported_film'
                        or not isinstance(row['title'],str) or not 1<=len(row['title'])<=200
                        or not isinstance(row['project_id'],str) or not 1<=len(row['project_id'])<=100
                        or type(row['duration_seconds']) not in (int,float)
                        or not 0<row['duration_seconds']<=86400):
                    raise ValueError('invalid_imported_draft_metadata')
                seen.add(row[id_key]); rows.append(dict(row))
        except (TypeError, ValueError, KeyError, AttributeError):
            raise web.HTTPConflict(text='draft_not_current') from None
        return web.json_response({'drafts': rows, **FLAGS},
                                 headers={'Cache-Control':'no-store, private'})

    async def serve(request):
        link = selected(request)
        revision = request.match_info[id_key]
        if not re.fullmatch('[a-f0-9]{64}', revision):
            raise web.HTTPNotFound()
        packet = await load(link, revision, video_kind)
        try:
            _flags(packet)
            data = packet['data']
            if (set(packet) != {'binding','current',id_key,'kind','sha256','data',*FLAGS}
                    or packet['binding'] != link or packet['current'] is not True
                    or packet[id_key] != revision or packet['kind'] != video_kind
                    or type(data) is not bytes or not 0 < len(data) <= MAX_MEDIA_BYTES
                    or hashlib.sha256(data).hexdigest() != packet['sha256']):
                raise ValueError('invalid_draft_media')
        except (TypeError, ValueError, KeyError, AttributeError):
            raise web.HTTPConflict(text='draft_not_current') from None
        authorize(request, link)
        headers = {'Cache-Control':'no-store, private',
                   'X-Content-Type-Options':'nosniff', 'Accept-Ranges':'bytes',
                   'ETag':'"' + packet['sha256'] + '"',
                   'X-Video-Status':'draft', 'X-Video-Accepted':'false',
                   'Content-Disposition':'inline; filename="draft-' + revision + '.mp4"'}
        try:
            start, end, partial = interval(request.headers.get('Range'), len(data))
        except ValueError:
            raise web.HTTPRequestRangeNotSatisfiable(
                headers={'Content-Range':'bytes */' + str(len(data))}) from None
        if partial:
            headers['Content-Range'] = f'bytes {start}-{end}/{len(data)}'
        return web.Response(body=data[start:end+1], status=206 if partial else 200,
                            content_type='video/mp4', headers=headers)

    prefix='/api/workboard/tasks/{id}/video/'+('imported-drafts' if _imported else 'drafts')
    app.router.add_get(prefix, catalog)
    app.router.add_get(prefix+'/{'+id_key+'}/video', serve)


def install_imported(app, store, bindings, producer):
    return install(app, store, bindings, producer, _imported=True)
