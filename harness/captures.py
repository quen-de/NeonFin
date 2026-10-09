"""Capture-only runs (screenshots, styles, glass, blue, contrast) side by side, one process per
CSS mode and plugin state. Nothing here is timed, so they share the machine; a timed run
waits for them and they wait for it (harness.lock).

usage: python -m harness.captures --label PREFIX [--css dist,vanilla] [--plugins STATE ...] [--jobs 4]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import subprocess
import sys


def slug(state: str) -> str:
    return "no-" + state.removeprefix("without:").replace(",", "-") if state.startswith("without:") else state


def commands(prefix: str, css_modes: list[str], states: list[str], extra: list[str]) -> list[tuple[str, list[str]]]:
    out = []
    for css in css_modes:
        for state in states:
            label = f"{prefix}-{css}-{slug(state)}"
            out.append(
                (label, [sys.executable, "-m", "harness.run", "--label", label, "--css", css, "--plugins", state, "--no-perf", *extra])
            )
    return out


def run_all(cmds: list[tuple[str, list[str]]], jobs: int) -> dict[str, tuple[int, str]]:
    """Exit code and output tail of every command, at most jobs at a time."""

    def one(argv):
        r = subprocess.run(argv, capture_output=True, text=True)
        return r.returncode, "\n".join((r.stdout + r.stderr).strip().splitlines()[-5:])

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {label: pool.submit(one, argv) for label, argv in cmds}
        return {label: f.result() for label, f in futures.items()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True, help="prefix; each run is PREFIX-CSS-STATE")
    ap.add_argument("--css", default="dist")
    ap.add_argument("--plugins", action="append", help="a plugin state, repeatable (default: all and none)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--profiles")
    ap.add_argument("--routes")
    ap.add_argument("--show-volatile", action="store_true")
    args = ap.parse_args(argv)
    states = args.plugins or ["all", "none"]
    extra = [*(["--profiles", args.profiles] if args.profiles else []), *(["--routes", args.routes] if args.routes else [])]
    extra += ["--show-volatile"] if args.show_volatile else []
    results = run_all(commands(args.label, args.css.split(","), states, extra), args.jobs)
    for label, (code, tail) in results.items():
        print(f"{'ok  ' if code == 0 else 'FAIL'} {label}")
        if code:
            print("     " + tail.replace("\n", "\n     "))
    return 1 if any(code for code, _ in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
