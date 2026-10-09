"""Timed trials run alone: a timed run holds the timing lock exclusively, untimed captures
share it. Two timed runs, or a timed run and a capture, never overlap on this machine."""

from __future__ import annotations

import contextlib
import pathlib

try:
    import fcntl
except ImportError:  # Windows: no flock, so nothing stops overlap there
    fcntl = None

LOCK = pathlib.Path(__file__).resolve().parent / "runs" / ".timing.lock"


@contextlib.contextmanager
def hold(timed: bool, path: pathlib.Path = LOCK, notify=print):
    if fcntl is None:
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = fcntl.LOCK_EX if timed else fcntl.LOCK_SH
    with open(path, "a") as f:
        try:
            fcntl.flock(f, mode | fcntl.LOCK_NB)
        except BlockingIOError:
            notify("waiting for other harness runs to finish" if timed else "waiting for a timed run to finish")
            fcntl.flock(f, mode)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
