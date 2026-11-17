"""Finite trusted metadata refresh; no installed timer and no production dispatch.

Stop at the first revoked/changed binding. The snapshot is immediately removed
on that failure, rather than being made current by a successful file read.
"""
import argparse
import json
import sqlite3
from pathlib import Path
import time
from production.pult_export import export_once,name_for
from production.pult_link import binding
from video_binding import prepare


def refresh_once(pult_database,source_root,cache,link):
    link=binding(link)
    try:prepare(pult_database,**link)
    except (ValueError,OSError,sqlite3.Error):
        (Path(cache)/name_for(link)).unlink(missing_ok=True)
        raise
    result=export_once(source_root,cache,link)
    try:prepare(pult_database,**link)
    except (ValueError,OSError,sqlite3.Error):
        (Path(cache)/name_for(link)).unlink(missing_ok=True)
        raise
    if result['state']!='observed':raise ValueError('source_not_current')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ['pult-database','source-root','cache','binding']:
        parser.add_argument('--'+field,type=Path,required=True)
    parser.add_argument('--cycles',type=int,default=1);parser.add_argument('--interval',type=float,default=30)
    args=parser.parse_args()
    if not 1<=args.cycles<=20 or not 5<=args.interval<=30:parser.error('finite limits:1..20 cycles,5..30 seconds')
    link=binding(json.loads(args.binding.read_text()));started=time.monotonic()
    for index in range(args.cycles):
        if time.monotonic()-started>600:raise TimeoutError('refresh_deadline')
        print(json.dumps(refresh_once(args.pult_database,args.source_root,args.cache,link)),flush=True)
        if index+1<args.cycles:time.sleep(args.interval)


if __name__=='__main__':main()
