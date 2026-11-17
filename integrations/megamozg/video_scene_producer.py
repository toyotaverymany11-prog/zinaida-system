"""Trusted read-only adapter to PR2's immutable scene revisions.

For an isolated producer process that already has source access. Never grant the
public web service that access just to use this adapter. Configuration is trusted,
explicit and independent of browser parameters. No rendering or repair calls.
"""
import hashlib
import os
from pathlib import Path
import stat
from production.pult_link import binding,collect
from video_media import MAX_MEDIA_BYTES


def scene_producer(root,link,request_id,revisions):
    from production.scene_revision import revision_file
    root=Path(root);link=binding(link);revisions=frozenset(revisions)
    if len(revisions)>20:raise ValueError('too_many_media_versions')

    def current(expected,revision,kind):
        if expected!=link or collect(root,link)['state']!='observed':raise ValueError('order_changed')
        if revision not in revisions:raise ValueError('unknown_revision')
        return revision_file(root,link['order_id'],request_id,revision,kind)

    def produce(expected,revision,kind):
        if kind=='catalog':
            versions=[]
            for item in sorted(revisions):
                for k in ('video','project'):current(expected,item,k)
                versions.append({'revision':item,'kinds':['video','project']})
            return {'binding':link,'current':True,'versions':versions}
        if kind not in ('video','project'):raise ValueError('invalid_kind')
        path=Path(current(expected,revision,kind)).absolute()
        if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('media_link')
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=MAX_MEDIA_BYTES:raise ValueError('media_size')
            chunks=[];remaining=before.st_size
            while remaining:
                chunk=os.read(fd,min(remaining,1024*1024))
                if not chunk:raise ValueError('media_short_read')
                chunks.append(chunk);remaining-=len(chunk)
            data=b''.join(chunks);after=os.fstat(fd)
            if (before.st_mtime_ns,before.st_size)!=(after.st_mtime_ns,after.st_size):raise ValueError('media_changed')
            again=Path(current(expected,revision,kind))
            latest=again.stat()
            if (latest.st_dev,latest.st_ino,latest.st_mtime_ns,latest.st_size)!=(before.st_dev,before.st_ino,before.st_mtime_ns,before.st_size):raise ValueError('media_changed')
            return {'binding':link,'revision':revision,'kind':kind,'current':True,
                    'data':data,'sha256':hashlib.sha256(data).hexdigest()}
        finally:os.close(fd)
    return produce
