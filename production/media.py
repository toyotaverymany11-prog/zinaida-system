from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .core import ProductionError, Runtime, digest, probe, write_json
from .manifest import required_reviews, validate


def ffmpeg(*args):
    return ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y", *map(str, args)]


def inspect_video(source: Path, output: Path, runtime=None, max_samples=24):
    """Measured evidence only; no automatic semantic or identity verdict."""
    from PIL import Image, ImageDraw
    runtime = runtime or Runtime(600)
    if type(max_samples) is not int or not 2 <= max_samples <= 80:
        raise ProductionError("max_samples must be 2..80")
    source = source.resolve(strict=True)
    initial_hash = digest(source, runtime)
    info = probe(source, runtime)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if not video:
        raise ProductionError("No video stream")
    duration = float(info["format"].get("duration", 0))
    if not 0 < duration <= 900:
        raise ProductionError("Inspection duration must be 0..900 seconds")
    rate = video.get("avg_frame_rate", "0/1").split("/")
    fps = float(rate[0])/float(rate[1]) if float(rate[1]) else 0
    if not 0 < fps <= 240:
        raise ProductionError("Invalid frame rate")
    output.mkdir(parents=True, exist_ok=False)
    (output / "frames").mkdir()
    # Current FFmpeg removed -vsync; older supported installations lack -fps_mode.
    sync_option = "-fps_mode" if "-fps_mode" in runtime.run(ffmpeg("-h", "full")) else "-vsync"
    runtime.run(ffmpeg("-i", source, "-an", "-vf",
                        "format=rgb24,select='gt(scene,0.3)',metadata=print:file=cuts.txt", sync_option, "vfr",
                        "-f", "null", "-"), cwd=output)
    cuts = sorted(set(float(x) for x in re.findall(r"pts_time:([0-9.]+)",
                        (output / "cuts.txt").read_text()) if 0 < float(x) < duration))
    last = max(0, duration - 1/fps)
    uniform = [last*i/(max_samples-1) for i in range(max_samples)]
    # Sampled evidence is explicitly bounded. Cut boundaries are recorded even
    # when there are too many to include in the contact sheet.
    samples = sorted(set(round(x, 6) for x in [0, last, *uniform, *cuts]))
    if len(samples) > max_samples:
        samples = [samples[round(i*(len(samples)-1)/(max_samples-1))] for i in range(max_samples)]
    frames = []
    for i, when in enumerate(samples):
        target = output / "frames" / f"{i:03d}.jpg"
        runtime.run(ffmpeg("-ss", when, "-i", source, "-frames:v", 1,
                            "-vf", "scale=640:-2", "-q:v", 2, target))
        if not target.exists():
            raise ProductionError(f"Failed to extract frame at {when}")
        frames.append({"time_seconds": when, "path": f"frames/{target.name}", "sha256": digest(target, runtime)})
    cell_w, cell_h = 320, 210
    sheet = Image.new("RGB", (cell_w*4, cell_h*((len(frames)+3)//4)), "#151923")
    draw = ImageDraw.Draw(sheet)
    for i, f in enumerate(frames):
        with Image.open(output/f["path"]) as im:
            im = im.convert("RGB")
            im.thumbnail((312, 180))
            x, y = (i%4)*cell_w, (i//4)*cell_h
            sheet.paste(im, (x+(cell_w-im.width)//2, y))
            draw.text((x+8, y+186), f'{f["time_seconds"]:.3f} s', fill="white")
    sheet.save(output/"contact_sheet.jpg", quality=90)
    audio = any(s["codec_type"] == "audio" for s in info["streams"])
    if audio:
        runtime.run(ffmpeg("-i", source, "-map", "0:a:0", "-vn", "-ac", 1,
                            "-ar", 16000, "-c:a", "pcm_s16le", output/"analysis_audio.wav"))
    if digest(source, runtime) != initial_hash:
        raise ProductionError("Source changed during inspection")
    boundaries = [0, *cuts, duration]
    report = {"schema_version": 1, "source_sha256": initial_hash, "probe": info,
              "detected_shots": [{"start": a, "end": b} for a,b in zip(boundaries, boundaries[1:])],
              "frames": frames, "coverage": "bounded_samples_not_all_frames",
              "cut_detector": {"method": "ffmpeg RGB scene change", "threshold": 0.3},
              "audio_for_analysis": "analysis_audio.wav" if audio else None,
              "semantic_review": "not_performed", "identity_review": "not_performed",
              "limitations": ["Cut detection is a heuristic, not a semantic scene analysis.",
                              "Contact sheet does not prove temporal or character consistency."]}
    write_json(output/"analysis.json", report)
    return report


def export_otio(manifest, paths, target):
    import opentimelineio as otio
    fps = manifest["format"]["fps"]
    rt = lambda frames: otio.opentime.RationalTime(frames, fps)
    def clip(item):
        seconds = item.get("source_in_seconds", 0)
        return otio.schema.Clip(name=item.get("id", item["asset"]),
            media_reference=otio.schema.ExternalReference(target_url=paths[item["asset"]].as_uri()),
            source_range=otio.opentime.TimeRange(rt(seconds*fps), rt(item["duration_frames"])),
            metadata={"production": item})
    timeline = otio.schema.Timeline(name=manifest["project_id"], metadata={"production": {
        "revision": manifest["revision"], "format": manifest["format"],
        "limitations": "Overlay placement and gain are metadata; conform in the target editor."}})
    videos = otio.schema.Track(name="Picture", kind=otio.schema.TrackKind.Video)
    source_audio = otio.schema.Track(name="Source audio", kind=otio.schema.TrackKind.Audio)
    for i, c in enumerate(manifest["clips"]):
        incoming = manifest["clips"][i-1].get("transition_after", {}).get("duration_frames", 0) if i else 0
        outgoing = c.get("transition_after", {}).get("duration_frames", 0)
        adjusted = dict(c, source_in_seconds=c.get("source_in_seconds", 0) + (incoming//2)/fps,
                        duration_frames=c["duration_frames"] - incoming//2 - (outgoing-outgoing//2))
        videos.append(clip(adjusted))
        source_audio.append(clip(adjusted) if c["source_audio"] == "keep" else
                            otio.schema.Gap(source_range=otio.opentime.TimeRange(rt(0), rt(adjusted["duration_frames"]))))
        if outgoing:
            for track in (videos, source_audio):
                track.append(otio.schema.Transition(transition_type=otio.schema.TransitionTypes.SMPTE_Dissolve,
                    in_offset=rt(outgoing//2), out_offset=rt(outgoing-outgoing//2)))
    timeline.tracks.extend([videos, source_audio])
    for group, kind in (("audio", otio.schema.TrackKind.Audio), ("overlays", otio.schema.TrackKind.Video)):
        for i, c in enumerate(manifest.get(group, [])):
            track = otio.schema.Track(name=f'{c.get("role", group)} {i+1}', kind=kind)
            if c["start_frame"]:
                track.append(otio.schema.Gap(source_range=otio.opentime.TimeRange(rt(0), rt(c["start_frame"]))))
            track.append(clip(c))
            timeline.tracks.append(track)
    otio.adapters.write_to_file(timeline, str(target))
    restored = otio.adapters.read_from_file(str(target))
    if restored.name != timeline.name or len(restored.tracks) != len(timeline.tracks):
        raise ProductionError("OTIO roundtrip failed")


def render(manifest, root: Path, output: Path, runtime=None):
    runtime = runtime or Runtime(1800)
    checked = validate(manifest, root)
    paths = checked["paths"]
    fmt = manifest["format"]
    fps, width, height = fmt["fps"], fmt["width"], fmt["height"]
    # Worst-case bound for temporary lossless frames, plus overhead. Don't fill disk.
    need = width*height*3*checked["frames"] + 256*1024*1024
    if shutil.disk_usage(root).free < need:
        raise ProductionError("Insufficient disk for bounded lossless intermediate files")
    output.mkdir(parents=True, exist_ok=False)
    work = output/"intermediate"
    work.mkdir()
    write_json(output/"manifest.json", manifest)
    try:
        videos = []
        for i, c in enumerate(manifest["clips"]):
            source = paths[c["asset"]]
            info = probe(source, runtime)
            seconds = c["duration_frames"]/fps
            start = c.get("source_in_seconds", 0)
            streams = info["streams"]
            if not any(s["codec_type"] == "video" for s in streams):
                raise ProductionError(f'Clip {c["id"]} has no video')
            if float(info["format"].get("duration", 0)) + 0.001 < start+seconds:
                raise ProductionError(f'Clip {c["id"]} is shorter than its requested range')
            has_audio = any(s["codec_type"] == "audio" for s in streams)
            if c["source_audio"] == "keep" and not has_audio:
                raise ProductionError("Cannot keep absent source audio; specify mute explicitly")
            args = ["-ss", start, "-i", source]
            keep = has_audio and c["source_audio"] == "keep"
            if not keep:
                args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            vf = (f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease:"
                  f"force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p")
            target = work/f"{i:03d}.mkv"
            runtime.run(ffmpeg(*args, "-map", "0:v:0", "-map", "0:a:0" if keep else "1:a:0",
                "-vf", vf, "-af", "aresample=48000,aformat=channel_layouts=stereo,apad",
                "-t", seconds, "-c:v", "ffv1", "-level", 3, "-c:a", "pcm_s16le", target))
            videos.append(target)
        args = []
        for path in videos:
            args += ["-i", path]
        filters = ["".join(f"[{i}:v:0][{i}:a:0]" for i in range(len(videos))) +
                   f"concat=n={len(videos)}:v=1:a=1[basev][basea]"]
        if any(c.get("transition_after") for c in manifest["clips"]):
            filters = []
            for i in range(len(videos)):
                filters += [f"[{i}:v:0]setpts=PTS-STARTPTS,fps={fps},settb=AVTB[tv{i}]",
                            f"[{i}:a:0]asetpts=PTS-STARTPTS[ta{i}]"]
            current_v, current_a = "tv0", "ta0"
            elapsed = manifest["clips"][0]["duration_frames"]
            for i in range(1, len(videos)):
                overlap = manifest["clips"][i-1].get("transition_after", {}).get("duration_frames", 0)
                nv, na = f"jv{i}", f"ja{i}"
                if overlap:
                    filters += [f"[{current_v}][tv{i}]xfade=transition=fade:duration={overlap/fps:.9f}:"
                                f"offset={(elapsed-overlap)/fps:.9f}[{nv}]",
                                f"[{current_a}][ta{i}]acrossfade=ns={round(overlap*48000/fps)}:c1=tri:c2=tri[{na}]"]
                else:
                    filters.append(f"[{current_v}][{current_a}][tv{i}][ta{i}]concat=n=2:v=1:a=1[{nv}][{na}]")
                elapsed += manifest["clips"][i]["duration_frames"]-overlap
                filters.append(f"[{nv}]fps={fps},settb=AVTB[cv{i}]")
                current_v, current_a = f"cv{i}", na
            filters += [f"[{current_v}]format=yuv420p[basev]", f"[{current_a}]anull[basea]"]
        audio_labels = ["[basea]"]
        next_index = len(videos)
        for i, a in enumerate(manifest.get("audio", [])):
            source = paths[a["asset"]]
            info = probe(source, runtime)
            if not any(s["codec_type"] == "audio" for s in info["streams"]):
                raise ProductionError("Audio asset has no audio stream")
            length = a["duration_frames"]/fps
            start = a.get("source_in_seconds", 0)
            if float(info["format"].get("duration", 0))+0.001 < start+length:
                raise ProductionError("Audio asset is shorter than its requested range")
            args += ["-i", source]
            delay = round(a["start_frame"]*48000/fps)
            filters.append(f"[{next_index}:a:0]atrim=start={start}:duration={length},asetpts=PTS-STARTPTS,"
                           f"aresample=48000,aformat=channel_layouts=stereo,volume={a.get('gain_db',0)}dB,"
                           f"adelay={delay}S:all=1[a{i}]")
            audio_labels.append(f"[a{i}]")
            next_index += 1
        filters.append("".join(audio_labels)+f"amix=inputs={len(audio_labels)}:normalize=0:dropout_transition=0,"
                       f"apad,atrim=duration={checked['duration']}[mixed]")
        vlabel = "basev"
        for i, ov in enumerate(manifest.get("overlays", [])):
            from PIL import Image
            with Image.open(paths[ov["asset"]]) as im:
                if im.format != "PNG":
                    raise ProductionError("Overlay must be a static PNG")
                if getattr(im, "n_frames", 1) != 1:
                    raise ProductionError("Animated overlays require another renderer")
            args += ["-loop", "1", "-framerate", fps, "-i", paths[ov["asset"]]]
            filters.append(f"[{next_index}:v]scale={ov['width']}:{ov['height']}[ov{i}]")
            filters.append(f"[{vlabel}][ov{i}]overlay=x={ov['x']}:y={ov['y']}:"
                           f"enable='gte(n,{ov['start_frame']})*lt(n,{ov['start_frame']+ov['duration_frames']})'[v{i}]")
            vlabel = f"v{i}"
            next_index += 1
        master = output/"master.mp4"
        runtime.run(ffmpeg(*args, "-filter_complex_threads", 1, "-filter_complex", ";".join(filters),
            "-map", f"[{vlabel}]", "-map", "[mixed]", "-t", checked["duration"],
            "-r", fps, "-c:v", "libx264", "-crf", 18, "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", master))
        runtime.run(ffmpeg("-i", master, "-f", "null", "-"))
        info = probe(master, runtime)
        stream = next(s for s in info["streams"] if s["codec_type"] == "video")
        checks = {"decodes": True, "dimensions": (stream["width"],stream["height"]) == (width,height),
                  "frames": int(stream.get("nb_frames", -1)) == checked["frames"],
                  "duration": abs(float(info["format"]["duration"])-checked["duration"]) <= 1/fps+0.02,
                  "audio_stream": any(s["codec_type"] == "audio" for s in info["streams"])}
        if not all(checks.values()):
            raise ProductionError(f"Technical checks failed: {checks}")
        qr_checks = verify_qr(manifest, master, output/"qr_checks", runtime)
        checks["qr_payloads"] = all(q["matches"] for q in qr_checks)
        if not checks["qr_payloads"]:
            raise ProductionError("QR payload could not be read from the final MP4")
        validate(manifest, root)  # Detect input changes during rendering.
        export_otio(manifest, paths, output/"timeline.otio")
        report = {"schema_version": 1, "project_id": manifest["project_id"], "revision": manifest["revision"],
                  "manifest_sha256": checked["manifest_sha256"], "output_sha256": digest(master),
                  "output": "master.mp4", "technical_checks": checks, "status": "needs_review",
                  "required_reviews": required_reviews(manifest), "probe": info, "qr_checks": qr_checks,
                  "limitations": ["This is a deterministic cuts/audio/PNG renderer, not a professional finishing suite.",
                                   "Identity, meaning, sound quality and artistic quality have not been approved.",
                                   "OTIO roundtrip verified; target editor conform not verified."]}
        write_json(output/"render.json", report)
        shutil.rmtree(work)
        return report
    except BaseException as exc:
        write_json(output/"failure.json", {"status": "failed", "error": str(exc),
                                           "manifest_sha256": checked["manifest_sha256"]})
        raise


def verify_qr(manifest, master, directory, runtime):
    from PIL import Image
    import zxingcpp
    checks = []
    fps = manifest["format"]["fps"]
    for i, item in enumerate(manifest.get("overlays", [])):
        if item.get("role") != "qr":
            continue
        directory.mkdir(exist_ok=True)
        start, count = item["start_frame"], item["duration_frames"]
        for frame in sorted({start, start+count//2, start+count-1}):
            path=directory/f"{i}-{frame}.png"
            runtime.run(ffmpeg("-ss",frame/fps,"-i",master,"-frames:v",1,path))
            with Image.open(path) as image:
                # Crop to the specified QR region so unrelated QR codes cannot pass it.
                image=image.crop((item["x"],item["y"],item["x"]+item["width"],item["y"]+item["height"]))
                decoded=[x.text for x in zxingcpp.read_barcodes(image)]
            checks.append({"overlay_index":i,"frame":frame,"destination":item["destination"],
                           "decoded":decoded,"matches":item["destination"] in decoded})
    return checks


def release_check(manifest, root, output, decisions):
    """Validate evidence supplied by the caller. This does not authenticate a reviewer."""
    checked = validate(manifest, root)
    report = json.loads((output/"render.json").read_text())
    sha = digest(output/"master.mp4")
    if report["manifest_sha256"] != checked["manifest_sha256"] or report["output_sha256"] != sha:
        raise ProductionError("Stale render report")
    if not all(report.get("technical_checks", {}).get(x) is True
               for x in ("decodes", "dimensions", "frames", "duration", "audio_stream", "qr_payloads")):
        raise ProductionError("Technical checks incomplete")
    needed = set(required_reviews(manifest))
    found = set()
    if not isinstance(decisions, list):
        raise ProductionError("Reviews must be a list")
    for d in decisions:
        if not isinstance(d, dict) or d.get("category") not in {
                "content", "artistic", "identity", "source_preservation", "qr",
                "photorealism", "temporal", "contact_and_occlusion"}:
            raise ProductionError("Unknown review category")
        if (d.get("output_sha256") != sha or d.get("manifest_sha256") != checked["manifest_sha256"]
                or d.get("revision") != manifest["revision"]):
            raise ProductionError("Review refers to a different revision or bytes")
        if d.get("verdict") != "pass":
            raise ProductionError("A review did not pass")
        if not d.get("reviewer") or not d.get("evidence"):
            raise ProductionError("Reviewer and evidence are required")
        found.add(d.get("category"))
    missing = needed-found
    if missing:
        raise ProductionError("Missing reviews: " + ", ".join(sorted(missing)))
    return {"status": "evidence_complete", "output_sha256": sha,
            "manifest_sha256": checked["manifest_sha256"],
            "note": "Controller must authenticate reviewers and obtain user acceptance. No publication performed."}
