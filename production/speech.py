"""Prepare immutable speech takes. No network calls, purchases or voice fallback."""
from datetime import datetime, timezone
import re

from .core import ProductionError, number, object_digest
from .costs import money


MODELS = {"s2.1-pro-free", "s2.1-pro", "s2-pro", "drama-3"}
FREE_UNTIL = datetime(2026, 12, 1, tzinfo=timezone.utc)


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("Timezone required")
        return result
    except (AttributeError, TypeError, ValueError) as exc:
        raise ProductionError("Quote needs an explicit timestamp with timezone") from exc


def prepare_batch(spec, *, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ProductionError("Current time must include timezone")
    if spec.get("schema_version") != 1:
        raise ProductionError("Unsupported speech specification")
    model = spec.get("model")
    if model not in MODELS:
        raise ProductionError("Unknown speech model; provider defaults may be chargeable")
    quote = spec["quote"]
    checked, until = timestamp(quote["checked_at"]), timestamp(quote["valid_until"])
    if not checked <= now < until:
        raise ProductionError("Missing, future or expired price verification")
    if quote.get("model") != model or quote.get("unit") != "million_utf8_bytes":
        raise ProductionError("Quote must match model and UTF-8 byte billing")
    if not quote.get("source"):
        raise ProductionError("Price source is required")
    rate = money(quote["usd_per_unit"])
    if model == "s2.1-pro-free":
        if rate != 0 or now >= FREE_UNTIL or until > FREE_UNTIL:
            raise ProductionError("Free promotion is unverified or outside its verified window")
    elif rate <= 0:
        raise ProductionError("Paid models cannot be treated as included subscription usage")
    voices, lines = spec["voices"], spec["lines"]
    if not isinstance(voices, dict) or not isinstance(lines, list) or not 1 <= len(lines) <= 32:
        raise ProductionError("Expected voice registry and 1 to 32 speech takes")
    takes, ids, total_bytes = [], set(), 0
    for line in lines:
        take_id = line["id"]
        if not isinstance(take_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", take_id) or take_id in ids:
            raise ProductionError("Missing, unsafe or duplicate take ID")
        ids.add(take_id)
        voice = voices[line["voice"]]
        reference = voice["provider_voice_id"]
        if not isinstance(reference, str) or not re.fullmatch(r"[a-f0-9]{28,40}", reference):
            raise ProductionError("Explicit provider voice ID required; no default voice")
        if not voice.get("version") or not re.fullmatch(r"[a-f0-9]{64}", voice.get("sample_sha256", "")):
            raise ProductionError("Voice version and approved sample hash required")
        spoken, directed = line["spoken_text"], line["directed_text"]
        if not isinstance(spoken, str) or not isinstance(directed, str) or not spoken.strip():
            raise ProductionError("Spoken and directed text required")
        # This single-speaker worker accepts bracket cues, not embedded dialogue or XML.
        if any(c in directed for c in "<>"):
            raise ProductionError("Use bracket delivery cues for single-speaker takes")
        without_cues = re.sub(r"\[[^\[\]\r\n]{1,300}\]", "", directed)
        if "[" in without_cues or "]" in without_cues:
            raise ProductionError("Malformed speech direction")
        if " ".join(without_cues.split()) != " ".join(spoken.split()):
            raise ProductionError("Delivery direction must preserve the approved spoken text")
        size = len(directed.encode("utf-8"))
        if not 1 <= size <= 6000:
            raise ProductionError("Speech take exceeds 6000 UTF-8 bytes")
        temperature = number(line.get("temperature", 0.4), "temperature", 0, 1)
        speed = number(line.get("speed", 1), "speed", 0.5, 2)
        body = {"text": directed, "reference_id": reference, "format": "mp3",
                "temperature": temperature, "prosody": {"speed": speed}, "latency": "normal"}
        identity = {"provider": "fish_audio", "model": model, "body": body,
                    "voice_version": voice["version"], "sample_sha256": voice["sample_sha256"]}
        takes.append({"id": take_id, "voice": line["voice"], "spoken_text": spoken,
                      "request": {"method": "POST", "url": "https://api.fish.audio/v1/tts",
                                  "headers": {"model": model, "Content-Type": "application/json"}, "json": body},
                      "utf8_bytes": size, "estimated_usd": str(rate * size / 1000000),
                      "cache_key": object_digest(identity)})
        total_bytes += size
    return {"schema_version": 1, "status": "prepared_not_submitted", "model": model,
            "spec_sha256": object_digest(spec), "quote": quote, "takes": takes,
            "total_utf8_bytes": total_bytes, "estimated_usd": str(rate * total_bytes / 1000000),
            "external_requests_sent": 0, "requires_review": ["voice_identity", "words", "pronunciation", "acting"],
            "note": "Estimate is per attempt, not account balance or spending permission. No automatic model or voice substitution."}
