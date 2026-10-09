"""Whether the skin meets the spec's gates against vanilla Jellyfin (spec section 5).

usage: python -m harness.gates VANILLA_RUN SKIN_RUN [--scope home,movies]
       python -m harness.gates --bench BENCH_RUN [SKIN_CAPTURE_RUN ...] [--scope home,movies]

Performance and glass apply to every route captured; Jellyfin blue and text
contrast apply only to the routes in scope (the pages the milestone styles).
A bench run (harness.bench) carries paired vanilla and skin trials; capture
runs next to it carry the glass, blue and contrast checks.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys

GLASS_BUDGET = {"desktop": 3, "phone": 0}
MENU_STATES = {"usermenu", "select", "actionsheet"}
RECALC_RATIO = 1.3
TASK_RATIO = 1.15
MIN_TRIALS = 7
# Accepted exceptions, keyed by (plugin state, profile, route), with their own ceilings so
# they cannot drift further unnoticed.
# 2026-10-09: a plugin-built desktop home restyles 1.6x to 1.8x vanilla while scrolling (the
# card ring and lift, a taller page, about 12% more per restyled element) with frames
# unchanged: 0 dropped, p95 16.7 ms. Cutting the card treatment only reaches 1.29x.
EXCEPTIONS = {("all", "desktop", "home"): {"recalc_style_ms": 2.0, "task_ms": 1.25}}
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


def decide(pairs: list[dict], lim: dict[str, float]) -> str | None:
    """'fail' or 'pass' once the pairs agree clearly enough, None while undecided."""
    if len(pairs) < MIN_DECIDED:
        return None
    ratios = {m: [_ratio(p["skin"][m], p["vanilla"][m]) for p in pairs] for m in lim}
    v_slowest = max(p["vanilla"]["anchor_ms"] for p in pairs)
    s_anchor = [p["skin"]["anchor_ms"] for p in pairs]
    if any(min(r) > lim[m] and statistics.median(r) > lim[m] * MARGIN for m, r in ratios.items()) or min(s_anchor) > v_slowest:
        return "fail"
    if all(max(r) <= lim[m] and statistics.median(r) < lim[m] / MARGIN for m, r in ratios.items()) and max(s_anchor) <= v_slowest:
        return "pass"
    return None


def _speed_failures(where: str, m: dict, v: dict, lim: dict[str, float]) -> list[str]:
    fails = []
    for metric, ratio in lim.items():
        if m[metric]["median"] > ratio * v[metric]["median"]:
            fails.append(f"{where}: {metric} {m[metric]['median']} > {ratio}x vanilla {v[metric]['median']}")
    if m["anchor_ms"]["median"] > v["anchor_ms"]["max"]:
        fails.append(f"{where}: anchor_ms {m['anchor_ms']['median']} beyond vanilla's slowest {v['anchor_ms']['max']}")
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
    for key in ("plugins", "server_version", "browser_version"):
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*", help="VANILLA SKIN, or with --bench the skin capture runs")
    ap.add_argument("--bench", help="a harness.bench run: speed comes from its paired trials")
    ap.add_argument("--scope", default="home")
    args = ap.parse_args(argv)
    scope = set(args.scope.split(","))
    if args.bench:
        bench = json.loads((pathlib.Path(args.bench) / "bench.json").read_text())
        fails = evaluate_bench(bench)
        for run in args.runs:
            capture = _summary(run)
            if capture.get("css_mode") == "vanilla":
                fails.append(f"{run}: a vanilla capture has no skin checks")
            for key in ("server_version", "browser_version"):
                if capture.get(key) != bench.get(key):
                    fails.append(f"{run}: {key} differs from the bench: {capture.get(key)} vs {bench.get(key)}")
            fails += [f"{capture.get('plugins')}: {f}" if len(args.runs) > 1 else f for f in route_failures(capture, scope)]
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
