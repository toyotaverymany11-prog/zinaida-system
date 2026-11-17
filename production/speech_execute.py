"""Execute and verify an explicitly authorized, zero-price Fish Audio batch."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import subprocess
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError

from .core import ProductionError, digest, read_json, write_json
from .rental_guard import private_token
from .speech import prepare_batch, timestamp

MAX_BYTES = 4 * 1024 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _send(request, token):
    headers = dict(request["headers"], Authorization="Bearer " + token)
    wire = Request(request["url"], data=json.dumps(request["json"]).encode(),
                   headers=headers, method="POST")
    with build_opener(_NoRedirect()).open(wire, timeout=18) as response:
        if response.status != 200 or response.headers.get_content_type() not in {
            "audio/mpeg", "audio/mp3", "application/octet-stream"
        }:
            raise ProductionError("Unexpected speech response")
        data = response.read(MAX_BYTES + 1)
    if not 0 < len(data) <= MAX_BYTES:
        raise ProductionError("Speech response exceeds bounds")
    return data


def _read_take(root, take):
    ident = take["id"]
    marker = root / (ident + ".intent.json")
    outcome = root / (ident + ".receipt.json")
    if not marker.exists() and not outcome.exists():
        return None
    key = take["cache_key"]
    if not marker.exists() or read_json(marker).get("cache_key") != key:
        raise ProductionError("Speech take is already bound to different input")
    if not outcome.exists():
        return {"take": ident, "cache_key": key, "status": "unknown_do_not_retry"}
    receipt = read_json(outcome)
    if receipt.get("cache_key") != key:
        raise ProductionError("Speech receipt does not match its request")
    if receipt["status"] == "decoded_needs_listening":
        result = root / (ident + ".mp3")
        if not result.is_file() or digest(result) != receipt["sha256"]:
            raise ProductionError("Saved audio changed")
    return receipt


def _execute_take(root, take, token):
    ident, key = take["id"], take["cache_key"]
    write_json(root / (ident + ".intent.json"), {"cache_key": key})
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    receipt = {"take": ident, "cache_key": key}
    temp = root / (ident + ".partial.mp3")
    try:
        temp.write_bytes(_send(take["request"], token))
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror",
                        "-i", str(temp), "-f", "null", "-"], check=True,
                       capture_output=True, timeout=10)
        final = root / (ident + ".mp3")
        temp.replace(final)
        receipt.update(status="decoded_needs_listening", sha256=digest(final),
                       bytes=final.stat().st_size)
    except HTTPError as exc:
        receipt.update(status="provider_refused", http_status=exc.code)
    except Exception as exc:
        receipt.update(status="unknown_or_invalid", error_type=type(exc).__name__)
    finally:
        temp.unlink(missing_ok=True)
    write_json(root / (ident + ".receipt.json"), receipt)
    return receipt


def execute(spec, root, credential=None, *, submit_authorized=False):
    """Serialize a private batch and never repeat a take with a durable intent."""
    root = Path(root)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (root / "execution.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProductionError("Speech batch is already running") from exc
        # Quote validation for new provider calls happens against the live clock.
        # A completed historical result can still be read after the quote expires.
        prepared = prepare_batch(spec, now=timestamp(spec["quote"]["checked_at"]))
        if prepared["model"] != "s2.1-pro-free":
            raise ProductionError("This executor only supports the explicit free model")
        batch_path = root / "prepared.json"
        if batch_path.exists() and read_json(batch_path) != prepared:
            raise ProductionError("Speech batch directory is bound to a different spec")
        takes = prepared["takes"]
        states = [_read_take(root, take) for take in takes]
        pending = [i for i, state in enumerate(states) if state is None]
        if pending:
            if not submit_authorized or credential is None:
                raise ProductionError("Speech submission requires explicit authorization and credential")
            prepare_batch(spec)
            token = private_token(Path(credential))
            if not batch_path.exists():
                write_json(batch_path, prepared)
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {i: pool.submit(_execute_take, root, takes[i], token) for i in pending}
                for i, future in futures.items():
                    states[i] = future.result()
        result = {"model": prepared["model"], "spec_sha256": prepared["spec_sha256"],
                  "estimated_usd": prepared["estimated_usd"], "takes": states,
                  "external_requests_sent_this_call": len(pending)}
        write_json(root / "result.json", result)
        return result


if __name__ == "__main__":
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument("--root", type=Path, required=True)
    argp.add_argument("--spec", type=Path, required=True)
    argp.add_argument("--credential-file", type=Path)
    argp.add_argument("--submit-authorized", action="store_true")
    args = argp.parse_args()
    print(json.dumps(execute(read_json(args.spec), args.root,
                             args.credential_file, submit_authorized=args.submit_authorized)))
