"""Owner-operated terminal setup. Never accept a credential from chat or argv."""
import argparse
import getpass
import json
import os
from pathlib import Path
import stat
import sys
import urllib.request

from .rental import NoRedirect

def main():
    p=argparse.ArgumentParser(description='Read a Runpod key privately in your SSH terminal and verify read access')
    p.add_argument('--credential-file',type=Path,required=True);a=p.parse_args()
    path=a.credential_file.absolute()
    if not sys.stdin.isatty():raise ValueError('Run interactively in your own SSH terminal')
    if path.exists() or path.is_symlink():raise ValueError('Existing credential will not be overwritten')
    if path.parent.is_symlink():raise ValueError('Credential directory cannot be a symlink')
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    info=path.parent.stat()
    if info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)&0o077:
        raise ValueError('Use an owner-only credential directory')
    token=getpass.getpass('Runpod API key (hidden, never send it to chat): ').strip()
    if not token or len(token)>4096 or any(c.isspace() for c in token):raise ValueError('Invalid credential format')
    req=urllib.request.Request('https://api.runpod.io/v2/pods?limit=1',
        headers={'Authorization':'Bearer '+token,'Accept':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=15) as response:
        # Only the status is needed. Never print account contents or the token.
        if response.status!=200:raise ValueError('Read verification failed')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'w') as out:out.write(token+'\n');out.flush();os.fsync(out.fileno())
    except BaseException:
        path.unlink(missing_ok=True);raise
    print(json.dumps({'configured':True,'read_access_verified':True,
                      'delete_access_verified':False,'resources_created':0}))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'configured':False,'error_type':type(exc).__name__}));sys.exit(2)
