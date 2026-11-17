"""Read a YouTube Analytics video report against an explicit publication receipt."""
import argparse
from datetime import date
import json
import math
from pathlib import Path
import re

from .core import ProductionError, digest, read_json, write_json


METRICS = {
    "views": "count",
    "engagedViews": "count",
    "estimatedMinutesWatched": "minutes",
    "averageViewDuration": "seconds",
    "averageViewPercentage": "percent",
    "likes": "count",
    "comments": "count",
    "shares": "count",
}


def summarize(report, publication, request):
    """Require the channel, time window and video to come from caller evidence."""
    video_id = publication.get("video_id", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ProductionError("Publication receipt needs a YouTube video ID")
    channel_id = publication.get("channel_id", "")
    if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel_id):
        raise ProductionError("Publication receipt needs a canonical channel ID")
    if not re.fullmatch(r"[a-f0-9]{64}", publication.get("output_sha256", "")):
        raise ProductionError("Publication receipt needs the exact master SHA-256")
    if request.get("ids") != "channel==" + channel_id or request.get("filters") != "video==" + video_id:
        raise ProductionError("Report query does not identify the receipt's channel and video")
    start = date.fromisoformat(request["startDate"])
    end = date.fromisoformat(request["endDate"])
    if end < start:
        raise ProductionError("Reversed analytics window")
    headers = report.get("columnHeaders", [])
    names = [h["name"] for h in headers]
    if len(set(names)) != len(names) or "video" not in names:
        raise ProductionError("Expected distinct columns and a video dimension")
    metrics = set(names) - {"video"}
    if not metrics or not metrics.issubset(METRICS):
        raise ProductionError("Expected one total row per video with supported metrics")
    if request.get("dimensions") != "video" or set(request.get("metrics", "").split(",")) != metrics:
        raise ProductionError("Report columns do not match the captured query")
    for h in headers:
        expected = "DIMENSION" if h["name"] == "video" else "METRIC"
        if h.get("columnType") != expected:
            raise ProductionError("Incorrect analytics column type")
    rows = report.get("rows", [])
    if not isinstance(rows, list) or len(rows) > 1:
        raise ProductionError("Expected at most one matching video row")
    values = {}
    if rows:
        row = rows[0]
        if not isinstance(row, list) or len(row) != len(names):
            raise ProductionError("Malformed analytics row")
        data = dict(zip(names, row))
        if data.pop("video") != video_id:
            raise ProductionError("Analytics returned a different video")
        for name, value in data.items():
            if value is None:
                continue
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ProductionError("Invalid metric value")
            if METRICS[name] == "count" and int(value) != value:
                raise ProductionError("Fractional count")
            values[name] = {"value": value, "unit": METRICS[name]}
    return {
        "platform": "youtube", "video_id": video_id, "channel_id": channel_id,
        "output_sha256": publication["output_sha256"], "start_date": start.isoformat(),
        "end_date": end.isoformat(), "metrics": values,
        "missing_metrics": sorted(metrics - set(values)),
        "status": "observed" if values else "no_observations",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--publication", type=Path, required=True)
    parser.add_argument("--query", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = summarize(read_json(args.report), read_json(args.publication), read_json(args.query))
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit("Invalid analytics input") from exc
    result["input_sha256"] = {name: digest(getattr(args, name)) for name in ("report", "publication", "query")}
    write_json(args.output, result)
    print(json.dumps({"status": result["status"], "metric_count": len(result["metrics"])}))
