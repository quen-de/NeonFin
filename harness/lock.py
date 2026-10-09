"""Timed trials run alone: a timed run holds the timing lock exclusively, untimed captures
share it. Two timed runs, or a timed run and a capture, never overlap on this machine, from
any checkout of the repo. Systems without flock (Windows) get a notice instead."""

from __future__ import annotations

import contextlib
import pathlib
import tempfile

try:
    import fcntl
except ImportError:  # Windows: no flock, so nothing stops overlap there
    fcntl = None

LOCK = pathlib.Path(tempfile.gettempdir()) / "neonfin-harness-timing.lock"


@contextlib.contextmanager
def hold(timed: bool, path: pathlib.Path = LOCK, notify=print):
    if fcntl is None:
        notify("no file locks on this system: timed runs may overlap other harness runs")
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
