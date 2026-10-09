"""Capture one harness run into harness/runs/<label>/."""

from __future__ import annotations

import argparse
import datetime
import gzip
import json
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

import build
from harness import collect, config, cssbundle, perf, plugins, session
from harness.profiles import PERF_ROUTES, PROFILES, ROUTES

RUNS = pathlib.Path(__file__).resolve().parent / "runs"


def prepare_outdir(root: pathlib.Path, label: str) -> pathlib.Path:
    out = root / label
    out.mkdir(parents=True, exist_ok=False)  # never overwrite a run
    return out


def server_version(base: str) -> str:
    with urllib.request.urlopen(f"{base}/System/Info/Public", timeout=30) as r:
        return json.loads(r.read()).get("Version", "unknown")


def write_gz(path: pathlib.Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, sort_keys=True)


def capture_profile(browser, cfg, prof, routes, override, effective, outdir, summary, plugins_off):
    volatile = cfg.volatile
    state = session.login_state(browser, cfg, prof)
    ctx, page = session.new_page(browser, prof, state, override, plugins_off)
    anon_ctx, anon_page = session.new_page(browser, prof, None, override, plugins_off)
    n_rules, selectors = collect.css_selectors(page, effective)
    unique = sorted(set(selectors))
    hit: set[int] = set()
    (outdir / prof.name).mkdir(parents=True, exist_ok=True)
    for route in routes:
        p = page if route.logged_in else anon_page
        key = f"{prof.name}/{route.name}"
        try:
            settled = session.open_route(p, cfg, route, volatile)
        except session.RouteError as e:
            summary["failures"].append(f"{key}: {e}")
            continue
        session.screenshot(p, route, volatile, outdir / prof.name / f"{route.name}.png")
        snap = collect.styles(p, volatile)
        write_gz(outdir / prof.name / f"{route.name}.styles.json.gz", snap)
        hit |= set(collect.matched(p, unique))
        summary["routes"][key] = {"settled": settled, "elements": len(snap), "backdrop_elements": collect.backdrop_count(snap)}
    summary["css"]["rules"] = n_rules
    summary["css"]["selectors"] = len(unique)
    summary["css"]["matched_share"][prof.name] = round(len(hit) / len(unique), 4) if unique else 0
    anon_ctx.close()
    ctx.close()
    return state


def perf_profile(browser, cfg, prof, state, override, trials, plugins_off):
    by_name = {r.name: r for r in ROUTES}
    out = {}
    for name in PERF_ROUTES:
        route = by_name[name]
        results = []
        for i in range(trials + 1):  # trial 0 warms caches and is discarded
            ctx, page = session.new_page(browser, prof, state, override, plugins_off)
            cdp = ctx.new_cdp_session(page)
            cdp.send("Performance.enable")
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": prof.cpu_throttle})
            anchor_ms = session.navigate(page, session.route_url(cfg, route), route.anchor)
            session.settle(page, cfg.volatile)
            r = perf.scroll_trial(page, cdp, prof.context["viewport"]) | {"anchor_ms": round(anchor_ms, 1)}
            ctx.close()
            if i:
                results.append(r)
        out[name] = perf.aggregate(results)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--label", required=True)
    ap.add_argument("--css", choices=("live", "dist"), required=True)
    ap.add_argument("--profiles", default="desktop,phone")
    ap.add_argument("--routes", default=",".join(r.name for r in ROUTES))
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--no-perf", action="store_true")
    ap.add_argument("--plugins", default="all", help="all, none, or without:<name>[,<name>]")
    args = ap.parse_args(argv)
    try:
        plugins_off = plugins.parse_state(args.plugins)
    except plugins.PluginStateError as e:
        ap.error(str(e))

    cfg = config.load()
    wanted = args.routes.split(",")
    routes = [r for r in ROUTES if r.name in wanted]
    outdir = prepare_outdir(RUNS, args.label)
    branding = cssbundle.probe_branding(cfg.url)
    if args.css == "dist":
        served = build.build()
        sha, dirty = build.parse_header(served)
        override = session.Override(served)
    else:
        served, sha, dirty, override = branding["custom_css"], None, None, None
    effective = cssbundle.strip_imports(served)
    summary = {
        "label": args.label,
        "plugins": args.plugins,
        "css_mode": args.css,
        "date": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "fork_sha": sha,
        "fork_dirty": dirty,
        "server_version": server_version(cfg.url),
        "branding_response": {k: branding[k] for k in ("wire_bytes", "encoding")},
        "css": {
            "custom_css_bytes": len(served.encode()),
            "effective_bytes": len(effective.encode()),
            "effective_gzip": len(gzip.compress(effective.encode())),
            "matched_share": {},
        },
        "routes": {},
        "perf": {},
        "failures": [],
    }
    with sync_playwright() as pw:
        browser = session.launch(pw)
        summary["browser_version"] = browser.version
        for name in args.profiles.split(","):
            prof = PROFILES[name]
            state = capture_profile(browser, cfg, prof, routes, override, effective, outdir, summary, plugins_off)
            if not args.no_perf:
                summary["perf"][name] = perf_profile(browser, cfg, prof, state, override, args.trials, plugins_off)
        browser.close()
    if override is not None:
        summary["intercept_hits"] = override.hits
        if override.hits == 0:
            summary["failures"].append("dist mode: the CSS intercept was never hit")
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{outdir}: {len(summary['routes'])} captures, {len(summary['failures'])} failures")
    for f in summary["failures"]:
        print("  FAIL", f)
    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
