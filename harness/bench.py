"""Paired speed bench: vanilla and skin trials alternate in one process, so drift lands on
both sides alike, and each cell stops as soon as its verdict is clear (harness.gates.decide).

usage: python -m harness.bench --label NAME [--plugins STATE ...] [--profiles desktop,phone]
       [--routes home,movies,series,movie] [--trials 7] [--css dist|live]

A cell is one plugin state, profile and route. Writes harness/runs/NAME/bench.json and
prints each cell's ratios and verdict; judge it with python -m harness.gates --bench.
"""

from __future__ import annotations

import argparse
import datetime
import json
import statistics
import sys
import time

from playwright.sync_api import sync_playwright

import build
from harness import config, gates, lock, perf, plugins, session
from harness.profiles import PERF_ROUTES, PROFILES, ROUTES
from harness.run import RUNS, prepare_outdir, server_version


def cells(states: list[str], profiles: list[str], routes: list[str]) -> list[tuple[str, str, str]]:
    return [(s, p, r) for s in states for p in profiles for r in routes]


def order(i: int) -> tuple[str, str]:
    """Which side goes first in pair i: alternating, so neither always runs on a warmer machine."""
    return ("vanilla", "skin") if i % 2 else ("skin", "vanilla")


def run_cell(trial, lim: dict[str, float], max_pairs: int) -> list[dict]:
    """Pairs of trial(side, i) results; pair 0 warms caches and is dropped."""
    pairs: list[dict] = []
    for i in range(max_pairs + 1):
        pair = {side: trial(side, i) for side in order(i)}
        if not i:
            continue
        pairs.append(pair)
        if gates.decide(pairs, lim) is not None:
            break
    return pairs


def describe(cell: str, pairs: list[dict], lim: dict[str, float]) -> str:
    med = {side: {m: statistics.median(p[side][m] for p in pairs) for m in (*lim, "anchor_ms")} for side in ("vanilla", "skin")}
    v, s = med["vanilla"], med["skin"]
    ratios = "  ".join(f"{m.removesuffix('_ms')} {v[m]:.1f}->{s[m]:.1f} ({gates._ratio(s[m], v[m]):.2f}x)" for m in lim)
    verdict = gates.decide(pairs, lim) or "judged on medians"
    return f"{cell:34} {len(pairs)} pairs  {ratios}  ready {v['anchor_ms']:.0f}->{s['anchor_ms']:.0f}  {verdict}"


def run_cells(todo, trial_for, out: dict, save) -> None:
    """Bench each (state, profile, route) and save after every cell, so a failure later on
    keeps the cells already measured."""
    for state, prof_name, route_name in todo:
        cell = f"{state}/{prof_name}/{route_name}"
        lim = gates.limits(state, prof_name, route_name)
        pairs = run_cell(trial_for(state, prof_name, route_name), lim, out["max_pairs"])
        out["cells"][cell] = {"pairs": pairs}
        save(out)
        print(describe(cell, pairs, lim), flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--plugins", action="append", help="a plugin state, repeatable (default: all)")
    ap.add_argument("--profiles", default="desktop,phone")
    ap.add_argument("--routes", default=",".join(PERF_ROUTES))
    ap.add_argument("--trials", type=int, default=gates.MIN_TRIALS, help="most pairs per cell")
    ap.add_argument("--css", choices=("dist", "live"), default="dist")
    args = ap.parse_args(argv)
    states = args.plugins or ["all"]
    try:
        offs = {s: plugins.parse_state(s) for s in states}
    except plugins.PluginStateError as e:
        ap.error(str(e))
    unknown = set(args.routes.split(",")) - set(PERF_ROUTES)
    if unknown:
        ap.error(f"no scroll trial for {', '.join(sorted(unknown))}; routes: {', '.join(PERF_ROUTES)}")

    cfg = config.load()
    outdir = prepare_outdir(RUNS, args.label)
    by_name = {r.name: r for r in ROUTES}
    if args.css == "dist":
        served = build.build()
        sha, dirty = build.parse_header(served)
        skin = session.Override(served)
    else:
        skin, sha, dirty = None, None, None
    vanilla = session.Override("")
    out = {
        "label": args.label,
        "css_mode": args.css,
        "date": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "skin_sha": sha,
        "skin_dirty": dirty,
        "server_version": server_version(cfg.url),
        "max_pairs": args.trials,
        "cells": {},
    }
    t0 = time.monotonic()

    def save(o):
        o["seconds"] = round(time.monotonic() - t0)
        o["intercept_hits"] = skin.hits if skin else None
        (outdir / "bench.json").write_text(json.dumps(o, indent=1) + "\n")

    with lock.hold(timed=True), sync_playwright() as pw:
        browser = session.launch(pw)
        out["browser_version"] = browser.version
        logins = {}
        sides = {"vanilla": vanilla, "skin": skin}

        def trial_for(state, prof_name, route_name):
            prof, route = PROFILES[prof_name], by_name[route_name]
            if prof_name not in logins:
                logins[prof_name] = session.login_state(browser, cfg, prof)
            return lambda side, i: perf.page_trial(browser, cfg, prof, route, logins[prof_name], sides[side], offs[state])

        run_cells(cells(states, args.profiles.split(","), args.routes.split(",")), trial_for, out, save)
        browser.close()
    save(out)
    fails = gates.evaluate_bench(out)
    for f in fails:
        print("FAIL", f)
    print(
        f"{outdir}: {len(out['cells'])} cells in {out['seconds']} s; "
        + ("speed gates: pass" if not fails else f"speed gates: {len(fails)} failure(s)")
    )
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
