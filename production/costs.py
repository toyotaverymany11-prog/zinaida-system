from decimal import Decimal, InvalidOperation

from .core import ProductionError


def money(value):
    try:
        value = Decimal(str(value))
    except InvalidOperation as exc:
        raise ProductionError("Invalid cost") from exc
    if not value.is_finite() or value < 0:
        raise ProductionError("Costs and durations must be finite and nonnegative")
    return value


def summarize(attempts, overhead_usd=0):
    total = money(overhead_usd)
    accepted_seconds = Decimal(0)
    accepted_scenes, ids = set(), set()
    rejected = 0
    for a in attempts:
        if not a.get("attempt_id") or a["attempt_id"] in ids:
            raise ProductionError("Duplicate or missing attempt ID")
        ids.add(a["attempt_id"])
        for field in ("compute_usd", "storage_usd", "transfer_usd", "review_usd", "manual_usd", "training_usd"):
            total += money(a.get(field, 0))
        if a.get("accepted") is True:
            scene = a.get("scene_id")
            if not scene or scene in accepted_scenes:
                raise ProductionError("Count only one accepted result per benchmark scene")
            accepted_scenes.add(scene)
            duration = money(a.get("accepted_seconds", 0))
            if not duration:
                raise ProductionError("Accepted result must have positive duration")
            accepted_seconds += duration
        else:
            rejected += 1
    return {"attempts": len(attempts), "accepted_scenes": len(accepted_scenes), "rejected_attempts": rejected,
            "total_usd": str(total), "accepted_seconds": str(accepted_seconds),
            "usd_per_accepted_second": str(total/accepted_seconds) if accepted_seconds else None,
            "note": "Compare only quality-matched accepted material; this is not a forecast."}
