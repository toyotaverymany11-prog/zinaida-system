from __future__ import annotations

import re
from pathlib import Path

from .core import ProductionError, digest, local_asset, number, object_digest


ROUTES = {"existing", "code", "cinematic", "character_series", "video_recast"}
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")


def validate(manifest: dict, root: Path) -> dict:
    if manifest.get("schema_version") != 1:
        raise ProductionError("Unsupported manifest schema_version")
    if manifest.get('quality_profile', 'photorealistic') not in {'photorealistic', 'stylized', 'source_matched'}:
        raise ProductionError('Unknown quality_profile')
    for key in ("project_id", "revision"):
        if not ID.fullmatch(str(manifest.get(key, ""))):
            raise ProductionError(f"Invalid {key}")
    fmt = manifest.get("format", {})
    for key in ("width", "height"):
        n = number(fmt.get(key), key, 64, 4096)
        if not isinstance(n, int) or n % 2:
            raise ProductionError(f"{key} must be an even integer")
    fps = fmt.get("fps")
    if type(fps) is not int or fps not in {24, 25, 30, 48, 50, 60}:
        raise ProductionError("fps must be 24, 25, 30, 48, 50 or 60")
    assets = manifest.get("assets", {})
    if not isinstance(assets, dict) or not assets or len(assets) > 256:
        raise ProductionError("Expected 1..256 assets")
    paths = {}
    for key, a in assets.items():
        if not ID.fullmatch(key):
            raise ProductionError("Invalid asset ID")
        p = local_asset(root, a["path"])
        expected = a.get("sha256", "")
        if not re.fullmatch("[0-9a-f]{64}", expected) or digest(p) != expected:
            raise ProductionError(f"Asset hash mismatch: {key}")
        paths[key] = p
    characters = manifest.get("characters", {})
    for key, c in characters.items():
        if not ID.fullmatch(key) or not c.get("version") or not c.get("reference_assets"):
            raise ProductionError("Character needs ID, version and reference assets")
        if any(a not in assets for a in c["reference_assets"]):
            raise ProductionError("Unknown character reference asset")
    clips = manifest.get("clips", [])
    if not clips or len(clips) > 100:
        raise ProductionError("Expected 1..100 clips")
    ids = set()
    total = 0
    for c in clips:
        if not ID.fullmatch(str(c.get("id", ""))) or c["id"] in ids:
            raise ProductionError("Missing or duplicate clip ID")
        ids.add(c["id"])
        if c.get("route") not in ROUTES or not c.get("purpose"):
            raise ProductionError("Clip needs route and purpose")
        if c.get("asset") not in assets:
            raise ProductionError("Clip material is missing; generation has not been completed")
        frames = c.get("duration_frames")
        if type(frames) is not int or frames < 1:
            raise ProductionError("duration_frames must be a positive integer")
        total += frames
        number(c.get("source_in_seconds", 0), "source_in_seconds", 0)
        if c.get("source_audio") not in {"keep", "mute"}:
            raise ProductionError("source_audio must explicitly be keep or mute")
        for ch in c.get("characters", []):
            if ch not in characters:
                raise ProductionError("Unknown character")
        if c["route"] == "character_series" and not c.get("characters"):
            raise ProductionError("character_series needs a character")
        if c["route"] == "video_recast":
            if c.get("original_asset") not in assets or not c.get("characters") or not c.get("target"):
                raise ProductionError("video_recast needs original, target and character")
    overlaps = []
    for i, c in enumerate(clips):
        transition = c.get("transition_after")
        if transition is None:
            overlaps.append(0)
            continue
        if not isinstance(transition, dict) or set(transition) != {"type", "duration_frames"}:
            raise ProductionError("Transition requires only type and duration_frames")
        count = transition["duration_frames"]
        if transition["type"] != "dissolve" or type(count) is not int or count <= 0:
            raise ProductionError("Only a positive-frame dissolve is supported")
        if i == len(clips)-1 or count >= min(c["duration_frames"], clips[i+1]["duration_frames"]):
            raise ProductionError("Transition needs two clips with unused frames")
        overlaps.append(count)
    for i, c in enumerate(clips):
        if (overlaps[i-1] if i else 0) + overlaps[i] >= c["duration_frames"]:
            raise ProductionError("Transitions must not consume or triple-overlap a clip")
    total -= sum(overlaps)
    if total / fps > 900:
        raise ProductionError("This worker is bounded to 15 minutes per render")
    for key in ("audio", "overlays"):
        entries = manifest.get(key, [])
        if not isinstance(entries, list) or len(entries) > 64:
            raise ProductionError(f"Invalid {key} list")
        for a in entries:
            if a.get("asset") not in assets:
                raise ProductionError(f"Unknown {key} asset")
            start, dur = a.get("start_frame"), a.get("duration_frames")
            if type(start) is not int or type(dur) is not int or start < 0 or dur <= 0 or start+dur > total:
                raise ProductionError(f"Invalid {key} interval")
            if key == "audio":
                number(a.get("source_in_seconds", 0), "audio source_in_seconds", 0)
                number(a.get("gain_db", 0), "gain_db", -96, 12)
                if a.get("role") not in {"voice", "music", "sfx", "ambience"}:
                    raise ProductionError("Audio role missing")
            else:
                for field in ("x", "y", "width", "height"):
                    if type(a.get(field)) is not int or a[field] < (1 if field in {"width", "height"} else 0):
                        raise ProductionError("Overlay coordinates must be nonnegative integers")
                if a["x"]+a["width"] > fmt["width"] or a["y"]+a["height"] > fmt["height"]:
                    raise ProductionError("Overlay exceeds frame")
                if a.get("role") == "qr" and not a.get("destination"):
                    raise ProductionError("QR destination is required for independent review")
    return {"paths": paths, "frames": total, "duration": total/fps,
            "manifest_sha256": object_digest(manifest)}


def required_reviews(manifest):
    reviews = {"content", "artistic"}
    if any(c['route'] in {'cinematic', 'character_series', 'video_recast'} for c in manifest['clips']):
        reviews.add('temporal')
        if manifest.get('quality_profile', 'photorealistic') == 'photorealistic':
            reviews.add('photorealism')
    if any(c.get("characters") for c in manifest["clips"]):
        reviews.add("identity")
    if any(c["route"] == "video_recast" for c in manifest["clips"]):
        reviews.add("source_preservation")
        reviews.add('contact_and_occlusion')
    if any(a.get("role") == "qr" for a in manifest.get("overlays", [])):
        reviews.add("qr")
    return sorted(reviews)
