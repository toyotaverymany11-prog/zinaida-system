"""Pack an existing verified film render and its editable media for review."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

import opentimelineio as otio

from .core import ProductionError, digest, object_digest, read_json
from .manifest import validate

REQUIRED_CHECKS = ("decodes", "dimensions", "frames", "duration", "audio_stream", "qr_payloads")


def package(manifest_path, root, render_dir, output, subtitles=None):
    root, render_dir, output = Path(root).resolve(), Path(render_dir).resolve(), Path(output)
    manifest = read_json(Path(manifest_path))
    checked = validate(manifest, root)
    report = read_json(render_dir / "render.json")
    master = render_dir / "master.mp4"
    checks = report.get("technical_checks", {})
    if (report.get("output_sha256") != digest(master)
            or report.get("manifest_sha256") != checked["manifest_sha256"]
            or not all(checks.get(k) is True for k in REQUIRED_CHECKS)):
        raise ProductionError("Render and current project must pass technical checks")
    sources = {"review.mp4": master, "manifest.json": Path(manifest_path)}
    if subtitles is not None:
        sources["subtitles.srt"] = Path(subtitles)
    media = {}
    for key, source in checked["paths"].items():
        rel = Path(manifest["assets"][key]["path"])
        if rel.is_absolute() or ".." in rel.parts or rel.parts[0] != "assets":
            raise ProductionError("Portable media must be below assets/")
        member = rel.as_posix()
        sources[member] = source
        media[source.as_uri()] = member
    timeline = otio.adapters.read_from_file(str(render_dir / "timeline.otio"))
    for clip in timeline.find_clips():
        ref = clip.media_reference
        uri = getattr(ref, "target_url", None)
        if uri not in media:
            raise ProductionError("Timeline contains media outside the verified manifest")
        ref.target_url = media[uri]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".part", delete=False) as file:
        part = Path(file.name)
    try:
        with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
            for name, path in sources.items():
                z.write(path, name)
            z.writestr("timeline.otio", otio.adapters.write_to_string(timeline, adapter_name="otio_json"))
            z.writestr("review.json", json.dumps({
                "status": "awaiting_independent_review", "revision": manifest["revision"],
                "output_sha256": report["output_sha256"], "manifest_sha256": checked["manifest_sha256"],
                "technical_checks": checks, "required_reviews": report["required_reviews"],
            }, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(part) as z:
            if z.testzip() is not None:
                raise ProductionError("Corrupted film package")
            with z.open("manifest.json") as file:
                if object_digest(json.load(file)) != checked["manifest_sha256"]:
                    raise ProductionError("Manifest changed during packaging")
            expected = {"review.mp4": report["output_sha256"]}
            expected.update({a["path"]: a["sha256"] for a in manifest["assets"].values()})
            for name, sha in expected.items():
                with z.open(name) as file:
                    if hashlib.file_digest(file, "sha256").hexdigest() != sha:
                        raise ProductionError("Packaged bytes differ from verified input")
        os.link(part, output)
    finally:
        with contextlib.suppress(FileNotFoundError):
            part.unlink()
    return {"file": output.name, "sha256": digest(output), "bytes": output.stat().st_size,
            "status": "awaiting_independent_review"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("manifest", "root", "render", "output"):
        parser.add_argument("--" + arg, type=Path, required=True)
    parser.add_argument("--subtitles", type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.manifest, args.root, args.render, args.output, args.subtitles)))
