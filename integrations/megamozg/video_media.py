"""Protected exact-version bytes. A trusted producer must validate the current
source plan on every request. No browser path, renderer, or provider operation.
"""
import asyncio
import hashlib
import re
from aiohttp import web
from production.pult_link import binding

MAX_MEDIA_BYTES=32*1024*1024


def interval(header,size):
    if header is None:return 0,size-1,False
    match=re.fullmatch(r'bytes=(\d*)-(\d*)',header)
    if not match or not any(match.groups()):raise ValueError('invalid_range')
    first,last=match.groups()
    if first:
        start=int(first);end=min(int(last),size-1) if last else size-1
    else:
        count=int(last)
        if count<1:raise ValueError('invalid_range')
        start=max(0,size-count);end=size-1
    if start>=size or end<start:raise ValueError('invalid_range')
    return start,end,True


def validate(packet,link,revision,kind):
    if not isinstance(packet,dict) or set(packet)!={'binding','revision','kind','sha256','data','current'}:
        raise ValueError('invalid_media')
    data=packet['data']
    if (packet['binding']!=link or packet['revision']!=revision or packet['kind']!=kind
            or packet['current'] is not True or type(data) is not bytes
            or not 0<len(data)<=MAX_MEDIA_BYTES
            or hashlib.sha256(data).hexdigest()!=packet['sha256']):
        raise ValueError('invalid_media')
    return data


def install(app,store,bindings,producer):
    from team import active_request
    links={key:binding(value) for key,value in bindings.items()}
    if any(key!=value['task_id'] for key,value in links.items()):raise ValueError('invalid_task_binding')
    pending=None

    async def load(link,revision,kind):
        nonlocal pending
        if producer is None:raise web.HTTPServiceUnavailable(text='video_producer_not_installed')
        if pending is not None and not pending.done():raise web.HTTPServiceUnavailable(text='video_read_busy')
        if pending is not None:pending.exception()
        pending=asyncio.create_task(asyncio.to_thread(producer,link,revision,kind))
        try:return await asyncio.wait_for(asyncio.shield(pending),timeout=5)
        except asyncio.CancelledError:raise
        except asyncio.TimeoutError:raise web.HTTPServiceUnavailable(text='video_read_timeout') from None
        except Exception:raise web.HTTPConflict(text='video_not_current') from None

    def authorize(request,link):
        with store.db() as db:
            user=active_request(db,request)
            row=db.execute('SELECT revision,created_by,assignee_user_id,assignee_kind FROM team_tasks WHERE id=?',(link['task_id'],)).fetchone()
            if (request.get('agent_authenticated') or not row or row['created_by']!=link['owner_id']
                    or not ((user['role']=='owner' and user['id']==link['owner_id'])
                            or (user['role']=='employee' and row['assignee_kind']=='human' and row['assignee_user_id']==user['id']))):
                raise web.HTTPForbidden(text='video_access_denied')
            if row['revision']!=link['task_revision']:raise web.HTTPConflict(text='video_binding_stale')

    async def catalog(request):
        link=links.get(request.match_info['id'])
        if link is None:raise web.HTTPNotFound()
        authorize(request,link)
        packet=await load(link,None,'catalog');authorize(request,link)
        if (not isinstance(packet,dict) or packet.get('binding')!=link or packet.get('current') is not True
                or not isinstance(packet.get('versions'),list) or len(packet['versions'])>20):
            raise web.HTTPConflict(text='video_not_current')
        versions=[]
        for item in packet['versions']:
            if (not isinstance(item,dict) or set(item)!={'revision','kinds'}
                    or not isinstance(item['revision'],str) or not re.fullmatch('[a-f0-9]{64}',item['revision'])
                    or not isinstance(item['kinds'],list) or not item['kinds'] or len(item['kinds'])>2
                    or any(x not in ('video','project') for x in item['kinds'])):
                raise web.HTTPConflict(text='video_not_current')
            versions.append(item)
        return web.json_response({'versions':versions,'finished_video_accepted':False},headers={'Cache-Control':'no-store'})

    async def serve(request):
        link=links.get(request.match_info['id'])
        if link is None:raise web.HTTPNotFound()
        authorize(request,link)
        revision=request.match_info['revision'];kind=request.match_info['kind']
        if not re.fullmatch('[a-f0-9]{64}',revision) or kind not in {'video','project'}:raise web.HTTPNotFound()
        packet=await load(link,revision,kind)
        try:
            data=validate(packet,link,revision,kind)
        except Exception:raise web.HTTPConflict(text='video_not_current') from None
        authorize(request,link)
        headers={'Cache-Control':'no-store, private','X-Content-Type-Options':'nosniff',
                 'Accept-Ranges':'bytes','ETag':'"'+packet['sha256']+'"',
                 'Content-Disposition':('inline' if kind=='video' else 'attachment')+'; filename="'+kind+'-'+revision+('.mp4' if kind=='video' else '.zip')+'"'}
        try:start,end,partial=interval(request.headers.get('Range'),len(data))
        except ValueError:raise web.HTTPRequestRangeNotSatisfiable(headers={'Content-Range':'bytes */'+str(len(data))}) from None
        if partial:headers['Content-Range']=f'bytes {start}-{end}/{len(data)}'
        return web.Response(body=data[start:end+1],status=206 if partial else 200,
                            content_type='video/mp4' if kind=='video' else 'application/zip',headers=headers)

    app.router.add_get('/api/workboard/tasks/{id}/video/media',catalog)
    app.router.add_get('/api/workboard/tasks/{id}/video/media/{revision}/{kind}',serve)
