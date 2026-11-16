"""Preserve explicitly supplied fal reference images, without biometric analysis."""
from __future__ import annotations

import hashlib
import io
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .core import ProductionError, read_json, write_json


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def allowed_url(url):
    parsed=urlparse(url)
    host=parsed.hostname or ""
    if parsed.scheme!="https" or parsed.username or parsed.password or not (host=="fal.media" or host.endswith(".fal.media")):
        raise ProductionError("Only explicit HTTPS fal.media reference URLs are supported")
    return url


def fetch_references(index, output: Path):
    from PIL import Image
    characters=index.get("characters",[])
    if sum(len(c.get("references",[])) for c in characters)>200:
        raise ProductionError("Reference batch exceeds 200 images")
    output.mkdir(parents=True,exist_ok=False)
    (output/"images").mkdir()
    opener=urllib.request.build_opener(NoRedirect())
    result={"schema_version":1,"status":"technical_inventory_not_character_approval","characters":[],"errors":[]}
    total_bytes=0
    deadline=time.monotonic()+900
    exhausted=False
    for character in characters:
        row={"id":character["id"],"name":character["name"],"handle":character.get("handle"),"references":[]}
        result["characters"].append(row)
        for ref in character.get("references",[]):
            try:
                if exhausted or time.monotonic()>=deadline or total_bytes>=256*1024*1024:
                    exhausted=True
                    raise ProductionError("Reference batch limit reached; no further downloads")
                url=allowed_url(ref["url"])
                with opener.open(url,timeout=25) as response:
                    limit=min(12*1024*1024,256*1024*1024-total_bytes)
                    chunks=[];size=0
                    while size<=limit:
                        if time.monotonic()>=deadline:
                            exhausted=True
                            raise ProductionError("Reference batch deadline exceeded")
                        chunk=response.read(min(65536,limit-size+1))
                        if not chunk:break
                        chunks.append(chunk);size+=len(chunk)
                    raw=b"".join(chunks)
                total_bytes+=len(raw)
                if len(raw)>12*1024*1024:
                    raise ProductionError("Image exceeds 12 MiB")
                if total_bytes>256*1024*1024:
                    raise ProductionError("Reference batch exceeds 256 MiB")
                with Image.open(io.BytesIO(raw)) as im:
                    if im.width*im.height>40_000_000:
                        raise ProductionError("Image exceeds 40 megapixels")
                    if im.format not in {"JPEG","PNG","WEBP"} or getattr(im,"n_frames",1)!=1:
                        raise ProductionError("Expected a static JPEG, PNG or WEBP")
                    dims=[im.width,im.height];fmt=im.format;im.load()
                sha=hashlib.sha256(raw).hexdigest()
                suffix={"JPEG":"jpg","PNG":"png","WEBP":"webp"}[fmt]
                relative=f"images/{sha}.{suffix}"
                path=output/relative
                if not path.exists():path.write_bytes(raw)
                row["references"].append({"asset_id":ref["assetRecordId"],"file":relative,"sha256":sha,
                                           "width":dims[0],"height":dims[1],"bytes":len(raw),
                                           "visual_approval":"not_performed"})
            except Exception as exc:
                result["errors"].append({"character_id":character["id"],"asset_id":ref.get("assetRecordId"),
                                          "error":type(exc).__name__,"detail":str(exc)[:250]})
            write_json(output/"inventory.json",result)
    result["downloaded_references"]=sum(len(c["references"]) for c in result["characters"])
    result["unique_files"]=len(list((output/"images").iterdir()))
    result["bytes"]=sum(p.stat().st_size for p in (output/"images").iterdir())
    result["complete"]=not result["errors"]
    write_json(output/"inventory.json",result)
    return result


if __name__=="__main__":
    import argparse,json
    p=argparse.ArgumentParser()
    p.add_argument("index",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();r=fetch_references(read_json(a.index),a.output)
    print(json.dumps({k:v for k,v in r.items() if k!="characters"},ensure_ascii=False,indent=2))
