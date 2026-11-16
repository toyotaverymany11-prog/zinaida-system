"""Make an explicitly synthetic technical fixture, never an artistic pilot."""
from pathlib import Path

from .core import Runtime, digest, write_json
from .media import ffmpeg


def make_fixture(root: Path):
    import qrcode
    root.mkdir(parents=True, exist_ok=False)
    rt = Runtime(90)
    rt.run(ffmpeg("-f", "lavfi", "-i", "color=c=red:s=320x180:r=24:d=2",
                  "-c:v", "libx264", "-pix_fmt", "yuv420p", root/"red.mp4"))
    rt.run(ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=320x180:r=24:d=2",
                  "-c:v", "libx264", "-pix_fmt", "yuv420p", root/"blue.mp4"))
    rt.run(ffmpeg("-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000:duration=4",
                  "-c:a", "pcm_s16le", root/"tone.wav"))
    url = "https://example.com/technical-test"
    qrcode.make(url, border=4, box_size=10).save(root/"qr.png")
    assets = {k:{"path":v,"sha256":digest(root/v)} for k,v in {
        "red":"red.mp4","blue":"blue.mp4","tone":"tone.wav","qr":"qr.png"}.items()}
    manifest = {"schema_version":1,"project_id":"technical-fixture","revision":"r1",
        "format":{"width":320,"height":180,"fps":24},"assets":assets,"characters":{},
        "clips":[{"id":"a","route":"existing","purpose":"Technical red cut fixture",
                  "asset":"red","duration_frames":48,"source_audio":"mute"},
                 {"id":"b","route":"existing","purpose":"Technical blue cut fixture",
                  "asset":"blue","duration_frames":48,"source_audio":"mute"}],
        "audio":[{"asset":"tone","role":"voice","start_frame":0,"duration_frames":96,"gain_db":-6}],
        "overlays":[{"asset":"qr","role":"qr","destination":url,"start_frame":24,
                     "duration_frames":48,"x":4,"y":4,"width":160,"height":160}],
        "note":"Synthetic technical test. Not a produced customer video or artistic acceptance."}
    write_json(root/"manifest.json",manifest)
    return manifest


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("directory",type=Path)
    a=p.parse_args()
    make_fixture(a.directory)
