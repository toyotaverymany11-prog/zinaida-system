from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path


class ProductionError(Exception):
    pass


class Cancelled(ProductionError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def object_digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def read_json(path: Path):
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ProductionError("JSON input exceeds 8 MiB")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def local_asset(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ProductionError("Asset must have a nonempty relative local path")
    if ":" in relative or "\\" in relative or ".." in Path(relative).parts:
        raise ProductionError("URLs and parent traversal are not asset paths")
    resolved = (root / relative).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ProductionError("Asset leaves project root or is not a file")
    return resolved


def number(value, name: str, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProductionError(f"{name}: expected a finite number")
    if value < minimum or (maximum is not None and value > maximum):
        raise ProductionError(f"{name}: out of range")
    return value


class Runtime:
    """One deadline across all subprocesses. Cancellation kills our process group only."""

    def __init__(self, seconds=900, cancel_file: Path | None = None):
        self.deadline = time.monotonic() + number(seconds, "timeout", 0.1, 86400)
        self.cancel_file = cancel_file

    def check(self):
        if self.cancel_file and self.cancel_file.exists():
            raise Cancelled("Cancellation requested")
        if time.monotonic() >= self.deadline:
            raise Cancelled("Worker deadline exceeded")

    def run(self, args: list[str], *, cwd=None, stderr=False) -> str:
        self.check()
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            proc = subprocess.Popen(args, cwd=cwd, stdin=subprocess.DEVNULL,
                                    stdout=out, stderr=err, start_new_session=True)
            try:
                while proc.poll() is None:
                    self.check()
                    time.sleep(0.05)
            except BaseException:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=2)
                except ProcessLookupError:
                    pass
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                raise
            out.seek(0)
            text = out.read(8 * 1024 * 1024 + 1)
            if len(text) > 8 * 1024 * 1024:
                raise ProductionError("Command output exceeded limit")
            if proc.returncode:
                err.seek(0, 2)
                err.seek(max(0, err.tell() - 3000))
                raise ProductionError(f"{Path(args[0]).name} failed ({proc.returncode}): "
                                      + err.read().decode(errors="replace"))
            if stderr:
                err.seek(0)
                text = err.read(8 * 1024 * 1024 + 1)
                if len(text) > 8 * 1024 * 1024:
                    raise ProductionError("Command stderr exceeded limit")
            return text.decode(errors="replace")


def probe(path: Path, runtime: Runtime | None = None):
    runtime = runtime or Runtime(30)
    return json.loads(runtime.run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                                   "-of", "json", str(path.resolve())]))
