"""Whether the skin meets the spec's gates against vanilla Jellyfin (spec section 5).

usage: python -m harness.gates VANILLA_RUN SKIN_RUN [--scope home,movies]
       python -m harness.gates --bench BENCH_RUN [--bench BENCH_RUN ...] [SKIN_CAPTURE_RUN ...] [--scope home,movies]

Performance and glass apply to every route captured; Jellyfin blue and text
contrast apply only to the routes in scope (the pages the milestone styles);
--scope all checks every route.
A bench run (harness.bench) carries paired vanilla and skin trials; capture
runs next to it carry the glass, blue and contrast checks. Every benched state needs its
captures, every route captured, and all plugins on and off need every speed cell benched,
all from one clean build. Several benches
of that build pool their pairs, so a borderline cell can be measured further without
re-running the rest and without dropping the pairs it already has.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys

from harness import plugins
from harness.profiles import PERF_ROUTES, PROFILES, ROUTES

GLASS_BUDGET = {"desktop": 3, "phone": 0}
# Speed is gated with every plugin on and every plugin off (spec 7.2); a state with one
# plugin removed is checked by captures alone.
SPEED_STATES = {"all", "none"}
MENU_STATES = {"usermenu", "select", "actionsheet"}
RECALC_RATIO = 1.3
TASK_RATIO = 1.15
MIN_TRIALS = 7
# Floors, 2026-10-24, owner-approved: a ratio fails only when the skin's excess over vanilla is
# also above its floor, and page ready may run a little past vanilla's slowest load. On a page
# that does little work a fixed few milliseconds read as a large ratio: the demo server's ten-film
# grids scroll in about 20 ms, and the skin's 13 to 22 ms more measured 1.7x with frames
# unchanged, where large libraries measure 0.9x. Its phone pages, served from the same machine,
# vary so little that page ready landed 9 to 30 ms past vanilla's slowest.
FLOORS = {"task_ms": 25.0}
ANCHOR_FLOOR_MS = 50.0
# Accepted exceptions, keyed by (plugin state, profile, route), with their own ceilings so
# they cannot drift further unnoticed.
# 2026-10-09: a plugin-built desktop home restyles 1.6x to 1.8x vanilla while scrolling (the
# card ring and lift, a taller page, about 12% more per restyled element) with frames
# unchanged: 0 dropped, p95 16.7 ms. Cutting the card treatment only reaches 1.29x.
# The ceilings sit about 7% above the worst medians measured (1.77x, 1.18x): close enough to
# catch a real step up, far enough that run-to-run spread (1.61x to 1.77x) does not trip it.
# 2026-10-24, owner-approved: on the demo server's short home (ten films under Media Bar
# Enhanced's hero) the task ratio measured 1.52x and 1.10x in two benches, 1.35x pooled over 20
# pairs, frames unchanged: p95 16.7 ms, at most 2 dropped on either side. The task ceiling sits
# about 7% above the worst median, 1.52x.
# 2026-10-10: with plugins off, desktop home is short, and hiding the My Media title (55px)
# moves where the bench's mid-screen cursor stops: it now ends the scroll over a card, whose
# hover animations (Jellyfin's overlay buttons, the skin's ring) restyle every frame. Moving
# the page 55px without hiding anything costs the same (1.59x); hiding the title without
# moving anything costs nothing (1.07x). Frames unchanged: 0 dropped, p95 16.7 ms. The
# ceilings sit about 7% above the worst medians measured (1.51x, 1.28x).
# 2026-10-10, owner-approved: title pages restyle about 1.35x vanilla and run about 1.2x its
# main-thread work while scrolling (pooled medians over four benches: 1.36x and 1.21x with
# plugins on desktop, 1.34x and 1.17x on phones), with frames unchanged (p95 16.7 ms) and
# page-ready unaffected. The milestone 1 skin alone measured about 1.1x here; benching the
# milestone 2 commits one by one found no single cause (the blurred backdrop copy costs
# nothing measurable, the palette about 1 ms a scroll). One ceiling for every title page cell.
TITLE_PAGE = {"recalc_style_ms": 1.4, "task_ms": 1.25}
EXCEPTIONS = {
    ("all", "desktop", "home"): {"recalc_style_ms": 1.9, "task_ms": 1.62},
    ("none", "desktop", "home"): {"recalc_style_ms": 1.62, "task_ms": 1.37},
} | {(plugins, profile, "movie"): TITLE_PAGE for plugins in ("all", "none") for profile in ("desktop", "phone")}
# Early decisions in paired benches, after MIN_DECIDED pairs: a cell fails once every pair is
# over a limit and the median pair over it by MARGIN; it passes once, on every metric, every
# pair is within the limit and the median pair within it by MARGIN. Were the true ratio on
# the line, four pairs would all land on one side one time in sixteen.
MIN_DECIDED = 4
MARGIN = 1.1


def limits(plugins: str, profile: str, route: str) -> dict[str, float]:
    """The speed ratios a cell must stay within."""
    return {"recalc_style_ms": RECALC_RATIO, "task_ms": TASK_RATIO} | EXCEPTIONS.get((plugins, profile, route), {})


def _ratio(skin: float, vanilla: float) -> float:
    return skin / vanilla if vanilla else (1.0 if not skin else float("inf"))


def _judged(metric: str, skin: float, vanilla: float) -> float:
    """The skin's ratio to vanilla, counted as even when the excess is within the metric's floor."""
    if metric in FLOORS and skin - vanilla <= FLOORS[metric]:
        return 1.0
    return _ratio(skin, vanilla)


def decide(pairs: list[dict], lim: dict[str, float]) -> str | None:
    """'fail' or 'pass' once the pairs agree clearly enough, None while undecided."""
    if len(pairs) < MIN_DECIDED:
        return None
    ratios = {m: [_judged(m, p["skin"][m], p["vanilla"][m]) for p in pairs] for m in lim}
    v_slowest = max(p["vanilla"]["anchor_ms"] for p in pairs) + ANCHOR_FLOOR_MS
    s_anchor = [p["skin"]["anchor_ms"] for p in pairs]
    if any(min(r) > lim[m] and statistics.median(r) > lim[m] * MARGIN for m, r in ratios.items()) or min(s_anchor) > v_slowest:
        return "fail"
    if all(max(r) <= lim[m] and statistics.median(r) < lim[m] / MARGIN for m, r in ratios.items()) and max(s_anchor) <= v_slowest:
        return "pass"
    return None


def _speed_failures(where: str, m: dict, v: dict, lim: dict[str, float]) -> list[str]:
    fails = []
    for metric, ratio in lim.items():
        if _judged(metric, m[metric]["median"], v[metric]["median"]) > ratio:
            fails.append(f"{where}: {metric} {m[metric]['median']} > {ratio}x vanilla {v[metric]['median']}")
    if m["anchor_ms"]["median"] > v["anchor_ms"]["max"] + ANCHOR_FLOOR_MS:
        late = f"more than {ANCHOR_FLOOR_MS:g} ms beyond vanilla's slowest {v['anchor_ms']['max']}"
        fails.append(f"{where}: anchor_ms {m['anchor_ms']['median']} {late}")
    return fails


def _aggregate(trials: list[dict]) -> dict:
    return {
        k: {"median": statistics.median(t[k] for t in trials), "min": min(t[k] for t in trials), "max": max(t[k] for t in trials)}
        for k in ("recalc_style_ms", "task_ms", "anchor_ms")
    }


def evaluate_bench(bench: dict) -> list[str]:
    fails: list[str] = []
    for cell, c in bench["cells"].items():
        plugins, prof, route = cell.split("/")
        pairs, lim = c["pairs"], limits(plugins, prof, route)
        verdict = decide(pairs, lim)
        if verdict is None and len(pairs) < MIN_TRIALS:
            fails.append(f"{cell}: {len(pairs)} pairs and no early decision, at least {MIN_TRIALS} needed")
        elif verdict != "pass":
            s, v = _aggregate([p["skin"] for p in pairs]), _aggregate([p["vanilla"] for p in pairs])
            fails += _speed_failures(cell, s, v, lim) or ([f"{cell}: every pair beyond a limit"] if verdict == "fail" else [])
    return fails


def route_failures(skin: dict, scope: set[str]) -> list[str]:
    fails: list[str] = []
    for key, r in skin.get("routes", {}).items():
        prof, route = key.split("/", 1)
        budget = GLASS_BUDGET[prof] + (1 if prof == "desktop" and route in MENU_STATES else 0)
        if r.get("glass", 0) > budget:
            fails.append(f"{key}: {r['glass']} live glass surfaces, budget {budget}: {r.get('glass_elements')}")
        if route in scope:
            if r.get("blue"):
                fails.append(f"{key}: Jellyfin blue still painted: {r['blue']}")
            if r.get("contrast_failures"):
                fails.append(f"{key}: low contrast: {r['contrast_failures']}")
    return fails + [f"skin run failure: {f}" for f in skin.get("failures", [])]


def evaluate(vanilla: dict, skin: dict, scope: set[str]) -> list[str]:
    fails: list[str] = []
    if vanilla.get("css_mode") != "vanilla":
        fails.append("first run is not a vanilla run")
    if skin.get("css_mode") == "vanilla":
        fails.append("second run is vanilla")
    for key in ("plugins", "server_version", "browser_version", "plugin_versions"):
        if vanilla.get(key) != skin.get(key):
            fails.append(f"{key} differs: {vanilla.get(key)} vs {skin.get(key)}")
    v_perf, s_perf = vanilla.get("perf", {}), skin.get("perf", {})
    if v_perf or s_perf:
        vt, st = vanilla.get("trials"), skin.get("trials")
        if vt is None or st is None or vt != st or st < MIN_TRIALS:
            fails.append(f"trials: {vt} vs {st}, both must be at least {MIN_TRIALS} and equal")
    for prof, routes in v_perf.items():
        for route in routes:
            if route not in s_perf.get(prof, {}):
                fails.append(f"{prof}/{route}: no skin performance to compare")
    for prof, routes in s_perf.items():
        for route, m in routes.items():
            v = v_perf.get(prof, {}).get(route)
            where = f"{prof}/{route}"
            if not v:
                fails.append(f"{where}: no vanilla performance to compare")
                continue
            fails += _speed_failures(where, m, v, limits(skin.get("plugins", ""), prof, route))
    return fails + route_failures(skin, scope)


def _summary(run: str) -> dict:
    return json.loads((pathlib.Path(run) / "summary.json").read_text())


def _provenance(what: str, run: dict) -> list[str]:
    if run.get("css_mode") == "live":
        return [f"a {what} of live CSS, not the build"]
    if run.get("skin_dirty") is not False:
        return [f"a {what} of uncommitted CSS"]
    return []


def pool(benches: list[dict]) -> tuple[dict, list[str]]:
    """One bench holding every cell's pairs from all the benches, and a note per pooled cell."""
    cells: dict[str, list[dict]] = {}
    sources: dict[str, int] = {}
    for b in benches:
        for cell, c in b["cells"].items():
            cells.setdefault(cell, []).extend(c["pairs"])
            sources[cell] = sources.get(cell, 0) + 1
    notes = [f"{cell}: {len(cells[cell])} pairs pooled from {n} benches" for cell, n in sources.items() if n > 1]
    return {**benches[0], "cells": {cell: {"pairs": p} for cell, p in cells.items()}}, notes


def evaluate_evidence(benches: list[dict], captures: dict[str, dict], scope: set[str]) -> tuple[list[str], list[str]]:
    """Failures and notes for benches plus skin captures (keyed by run name): one clean build,
    every speed cell benched and every route captured for each plugin state."""
    fails = [f for b in benches for f in _provenance("bench", b)]
    fails += [
        "a bench in which the skin CSS never reached the page"
        for b in benches
        if b.get("css_mode") == "dist" and not b.get("intercept_hits")
    ]
    builds = sorted({b.get("skin_build") for b in benches}, key=str)
    if len(builds) > 1:
        fails.append(f"benches measured different builds: {', '.join(map(str, builds))}")
    for b in benches[1:]:
        for key in ("server_version", "browser_version", "plugin_versions"):
            if b.get(key) != benches[0].get(key):
                fails.append(f"benches differ in {key}: {benches[0].get(key)} vs {b.get(key)}")
    bench, notes = pool(benches)
    fails += evaluate_bench(bench)
    benched = {cell.split("/")[0] for cell in bench["cells"]}
    for state in sorted(benched):
        fails += [f"{state}/{p}/{r}: not benched" for p in PROFILES for r in PERF_ROUTES if f"{state}/{p}/{r}" not in bench["cells"]]
    if not captures:
        return fails + ["no capture runs: glass, blue and contrast unchecked"], notes
    captured = {c.get("plugins") for c in captures.values()}
    fails += [f"{s}: benched but never captured" for s in sorted(benched - captured, key=str)]
    fails += [f"{s}: captured but never benched" for s in sorted((captured & SPEED_STATES) - benched, key=str)]
    for run, capture in captures.items():
        state = capture.get("plugins")
        if capture.get("css_mode") == "vanilla":
            fails.append(f"{run}: a vanilla capture has no skin checks")
            continue
        fails += [f"{run}: {f}" for f in _provenance("capture", capture)]
        notes += [f"{run}: signed in again before {key}" for key in capture.get("relogins", [])]
        if capture.get("skin_build") != builds[0]:
            fails.append(f"{run}: captured build {capture.get('skin_build')}, benched {builds[0]}")
        for key in ("server_version", "browser_version", "plugin_versions"):
            if capture.get(key) != bench.get(key):
                fails.append(f"{run}: {key} differs from the bench: {capture.get(key)} vs {bench.get(key)}")
        try:
            off = plugins.parse_state(str(state))
        except plugins.PluginStateError as e:
            fails.append(f"{run}: {e}")
            continue
        fails += [
            f"{state}: no capture of {p}/{r.name}"
            for p in PROFILES
            for r in ROUTES
            if not r.needs & off and f"{p}/{r.name}" not in capture.get("routes", {})
        ]
        fails += [f"{state}: {f}" for f in route_failures(capture, scope)]
    return fails, notes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*", help="VANILLA SKIN, or with --bench the skin capture runs")
    ap.add_argument(
        "--bench", action="append", help="a harness.bench run, repeatable: speed comes from its paired trials, pooled across benches"
    )
    ap.add_argument("--scope", default="home", help="route names, or all")
    args = ap.parse_args(argv)
    scope = {r.name for r in ROUTES} if args.scope == "all" else set(args.scope.split(","))
    if args.bench:
        benches = [json.loads((pathlib.Path(b) / "bench.json").read_text()) for b in args.bench]
        fails, notes = evaluate_evidence(benches, {pathlib.Path(r).name: _summary(r) for r in args.runs}, scope)
        for n in notes:
            print(n)
    elif len(args.runs) == 2:
        fails = evaluate(_summary(args.runs[0]), _summary(args.runs[1]), scope)
    else:
        ap.error("give VANILLA SKIN, or --bench BENCH_RUN [SKIN_CAPTURE_RUN ...]")
    for f in fails:
        print("FAIL", f)
    print("gates: pass" if not fails else f"gates: {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
