"""Whether a skin run meets the spec's gates against a vanilla run (spec section 5).

usage: python -m harness.gates VANILLA_RUN SKIN_RUN [--scope home,movies]

Performance and glass apply to every route captured; Jellyfin blue and text
contrast apply only to the routes in scope (the pages the milestone styles).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

GLASS_BUDGET = {"desktop": 3, "phone": 0}
MENU_STATES = {"usermenu", "select", "actionsheet"}
RECALC_RATIO = 1.3
TASK_RATIO = 1.15


def evaluate(vanilla: dict, skin: dict, scope: set[str]) -> list[str]:
    fails: list[str] = []
    if vanilla.get("css_mode") != "vanilla":
        fails.append("first run is not a vanilla run")
    if skin.get("css_mode") == "vanilla":
        fails.append("second run is vanilla")
    for key in ("plugins", "server_version", "browser_version"):
        if vanilla.get(key) != skin.get(key):
            fails.append(f"{key} differs: {vanilla.get(key)} vs {skin.get(key)}")
    for prof, routes in skin.get("perf", {}).items():
        for route, m in routes.items():
            v = vanilla.get("perf", {}).get(prof, {}).get(route)
            where = f"{prof}/{route}"
            if not v:
                fails.append(f"{where}: no vanilla performance to compare")
                continue
            for metric, ratio in (("recalc_style_ms", RECALC_RATIO), ("task_ms", TASK_RATIO)):
                if m[metric]["median"] > ratio * v[metric]["median"]:
                    fails.append(f"{where}: {metric} {m[metric]['median']} > {ratio}x vanilla {v[metric]['median']}")
            if m["anchor_ms"]["median"] > v["anchor_ms"]["max"]:
                fails.append(f"{where}: anchor_ms {m['anchor_ms']['median']} beyond vanilla's slowest {v['anchor_ms']['max']}")
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
    fails += [f"skin run failure: {f}" for f in skin.get("failures", [])]
    return fails


def _summary(run: str) -> dict:
    return json.loads((pathlib.Path(run) / "summary.json").read_text())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("vanilla")
    ap.add_argument("skin")
    ap.add_argument("--scope", default="home")
    args = ap.parse_args(argv)
    fails = evaluate(_summary(args.vanilla), _summary(args.skin), set(args.scope.split(",")))
    for f in fails:
        print("FAIL", f)
    print("gates: pass" if not fails else f"gates: {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
