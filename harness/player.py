"""Player timing: how long Play takes to show a picture, how fast the controls come back, and
how smoothly frames run while they show, with the skin against vanilla (spec 6.12).

usage: python -m harness.player --label NAME [--profiles desktop,phone]
       [--titles direct,hdr,convert] [--pairs 7] [--plugins all]

The titles come from harness/config.local.json (python -m harness.discover). direct is an H.264
MP4 that every browser plays as is; hdr is an HEVC HDR film as this browser handles it; convert
is the same film with HEVC hidden from the page, so the server has to convert it, as it does for
a browser without HEVC. Vanilla and skin trials alternate as in the speed bench, and the first
pair warms caches and is dropped. Nothing is gated: the numbers say whether the skin costs the
player anything, and whether a delay is the server's. Writes harness/runs/NAME/player.json.
"""

from __future__ import annotations

import argparse
import datetime
import json
import statistics
import sys
import time
import urllib.parse

from playwright.sync_api import sync_playwright

import build
from harness import bench, config, gates, lock, perf, plugins, session
from harness.profiles import PROFILES
from harness.run import RUNS, prepare_outdir, server_version

# Title name: (config item, hide HEVC from the page).
TITLES = {"direct": ("play_direct", False), "hdr": ("play_hdr", False), "convert": ("play_hdr", True)}
PLAY = ".mainDetailButtons button[data-action='resume'], .mainDetailButtons button[data-action='play']"
# The controls hide 3 s after they show; the frame window ends well before.
WINDOW_MS = 2000
METRICS = (
    "first_frame_ms",
    "info_ms",
    "start_ms",
    "metadata_ms",
    "controls_shown_ms",
    "controls_visible_ms",
    "frame_p95",
    "dropped",
    "video_dropped",
    "task_ms",
    "recalc_style_ms",
)
SHOWN = ("first_frame_ms", "start_ms", "metadata_ms", "controls_visible_ms", "frame_p95", "dropped", "video_dropped", "task_ms")

# Marks in the page's own clock (event timeStamps share performance.now()'s origin).
PLAYER_JS = r"""(() => {
  const L = window.__nfp = { click: null, info: null, loadstart: null, metadata: null, frame: null, inputs: [], osd: null };
  document.addEventListener('click', (e) => {
    if (L.click === null && e.target.closest('.mainDetailButtons')) L.click = e.timeStamp;
  }, true);
  for (const [type, key] of [['loadstart', 'loadstart'], ['loadedmetadata', 'metadata']]) {
    document.addEventListener(type, (e) => {
      if (e.target.tagName !== 'VIDEO' || L[key] !== null) return;
      L[key] = e.timeStamp;
      if (type === 'loadstart') e.target.requestVideoFrameCallback((now) => { L.frame = now; });
    }, true);
  }
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) if (L.info === null && e.name.includes('/PlaybackInfo')) L.info = e.responseEnd;
  }).observe({ type: 'resource', buffered: true });
  for (const type of ['pointermove', 'pointerdown']) document.addEventListener(type, (e) => L.inputs.push(e.timeStamp), true);
})()"""

# Armed while the controls are hidden: notes when they show again and when they are fully opaque.
OSD_ARM = r"""() => {
  const L = window.__nfp, bar = document.querySelector('.videoOsdBottom');
  L.inputs = [];
  L.osd = { input: null, shown: null, visible: null };
  const obs = new MutationObserver(() => {
    if (bar.classList.contains('videoOsdBottom-hidden') || bar.classList.contains('hide')) return;
    obs.disconnect();
    L.osd.shown = performance.now();
    L.osd.input = L.inputs.filter((t) => t <= L.osd.shown).pop() ?? null;
    const poll = () => {
      if (parseFloat(getComputedStyle(bar).opacity) >= 0.99) L.osd.visible = performance.now();
      else requestAnimationFrame(poll);
    };
    requestAnimationFrame(poll);
  });
  obs.observe(bar, { attributes: true, attributeFilter: ['class'] });
}"""

# A browser without HEVC (or Dolby Vision) answers no to every question about it.
NO_HEVC_JS = r"""(() => {
  const hevc = (t) => /hvc1|hev1|hevc|dvh1|dvhe/i.test(t || '');
  const isType = MediaSource.isTypeSupported.bind(MediaSource);
  MediaSource.isTypeSupported = (t) => !hevc(t) && isType(t);
  const canPlay = HTMLMediaElement.prototype.canPlayType;
  HTMLMediaElement.prototype.canPlayType = function (t) { return hevc(t) ? '' : canPlay.call(this, t); };
})()"""

QUALITY = """() => {
  const q = document.querySelector('video').getVideoPlaybackQuality();
  return [q.droppedVideoFrames, q.totalVideoFrames];
}"""
OSD_UP = "() => !document.querySelector('.videoOsdBottom').classList.contains('videoOsdBottom-hidden')"
STOP_JS = "(id) => window.ApiClient.stopActiveEncodings(id).then(() => true, () => false)"


def run_pairs(trial, pairs: int) -> list[dict]:
    """Pairs of trial(side) results in the bench's alternating order; pair 0 warms caches and is
    dropped."""
    out = []
    for i in range(pairs + 1):
        pair = {side: trial(side) for side in bench.order(i)}
        if i:
            out.append(pair)
    return out


def play_method(urls: list[str]) -> str:
    """How the picture reached the browser: the file as it is, or converted into HLS by the
    server (repackaged or transcoded), with the server's reasons."""
    for u in urls:
        parts = urllib.parse.urlsplit(u)
        if parts.path.lower().endswith("/master.m3u8"):
            reasons = urllib.parse.parse_qs(parts.query).get("TranscodeReasons", ["no reason given"])[0]
            return f"converted ({reasons})"
    if any("static=true" in urllib.parse.urlsplit(u).query.lower() for u in urls):
        return "direct"
    return "unknown"


def play_session(urls: list[str]) -> str | None:
    for u in urls:
        for key, values in urllib.parse.parse_qs(urllib.parse.urlsplit(u).query).items():
            if key.lower() == "playsessionid":
                return values[0]
    return None


def timings(start: dict, osd: dict) -> dict:
    """Milliseconds from the click on Play, and from the input that woke the controls; None where
    a mark is missing."""

    def gap(a, b):
        return None if a is None or b is None else round(b - a, 1)

    return {
        "info_ms": gap(start["click"], start["info"]),
        "start_ms": gap(start["click"], start["loadstart"]),
        "metadata_ms": gap(start["click"], start["metadata"]),
        "first_frame_ms": gap(start["click"], start["frame"]),
        "controls_shown_ms": gap(osd["input"], osd["shown"]),
        "controls_visible_ms": gap(osd["input"], osd["visible"]),
    }


def medians(pairs: list[dict], side: str) -> dict:
    out = {}
    for m in METRICS:
        values = [p[side][m] for p in pairs if p[side].get(m) is not None]
        out[m] = statistics.median(values) if values else None
    return out


def describe(cell: str, pairs: list[dict]) -> str:
    v, s = medians(pairs, "vanilla"), medians(pairs, "skin")

    def one(m):
        name = m.removesuffix("_ms")
        return f"{name} n/a" if v[m] is None or s[m] is None else f"{name} {v[m]:.0f}->{s[m]:.0f}"

    trials = [p[side] for p in pairs for side in p]
    methods = sorted({t["method"] for t in trials})
    hid = sum(not t["controls_held"] for t in trials)
    line = f"{cell:16} {len(pairs)} pairs  " + "  ".join(one(m) for m in SHOWN) + f"  [{', '.join(methods)}]"
    return line + (f"  controls hid early in {hid} trial{'s' if hid != 1 else ''}" if hid else "")


def wake(page, prof) -> None:
    """What a viewer does to bring the controls back: move the mouse, or tap the picture."""
    vp = prof.context["viewport"]
    if prof.context.get("has_touch"):
        page.touchscreen.tap(vp["width"] / 2, vp["height"] / 3)
    else:
        page.mouse.move(vp["width"] / 3, vp["height"] / 3)
        page.mouse.move(vp["width"] / 2, vp["height"] / 2)


def measure(page, cdp, cfg, prof, item: str, urls: list[str]) -> dict:
    session.navigate(page, f"{cfg.url}/web/#/details?id={item}", PLAY)
    session.settle(page, cfg.volatile)
    page.locator(PLAY).first.click()
    page.wait_for_function("() => window.__nfp.frame !== null", timeout=90_000)
    start = page.evaluate("() => window.__nfp")
    page.wait_for_selector(".videoOsdBottom.hide", state="attached", timeout=20_000)
    page.evaluate(OSD_ARM)
    wake(page, prof)
    page.wait_for_function("() => window.__nfp.osd.visible !== null", timeout=10_000)
    osd = page.evaluate("() => window.__nfp.osd")
    m0, q0 = perf.read_metrics(cdp), page.evaluate(QUALITY)
    page.evaluate(perf.RAF_START)
    page.wait_for_timeout(WINDOW_MS)
    frames = page.evaluate(perf.RAF_STOP)
    q1, m1 = page.evaluate(QUALITY), perf.read_metrics(cdp)
    return (
        timings(start, osd)
        | perf.frame_stats(frames)
        | perf.metric_deltas(m0, m1)
        | {
            "video_dropped": q1[0] - q0[0],
            "video_frames": q1[1] - q0[1],
            "controls_held": page.evaluate(OSD_UP),
            "method": play_method(urls),
        }
    )


def stop_conversion(page, urls: list[str]) -> bool | None:
    """End this trial's conversion on the server now. The harness swallows playback reports, the
    Stopped one included, which is what normally ends it. None when nothing was converted."""
    sid = play_session(urls)
    if sid is None or play_method(urls) == "direct":
        return None
    try:
        return page.evaluate(STOP_JS, sid)
    except Exception:
        return False


def play_trial(browser, cfg, prof, item: str, convert: bool, state, override, plugins_off) -> dict:
    """One trial in a fresh context: open the title, press Play, time the first frame, let the
    controls hide, wake them, record frames while they show, then end any conversion."""
    ctx, page = session.new_page(browser, prof, state, override, plugins_off, freeze_clock=False)
    ctx.add_init_script(PLAYER_JS)
    if convert:
        ctx.add_init_script(NO_HEVC_JS)
    # Kept in memory only: these URLs carry the session's token.
    urls: list[str] = []
    page.on("request", lambda r: urls.append(r.url) if "/videos/" in r.url.lower() else None)
    try:
        cdp = ctx.new_cdp_session(page)
        cdp.send("Performance.enable")
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": prof.cpu_throttle})
        result = measure(page, cdp, cfg, prof, item, urls)
    finally:
        stopped = stop_conversion(page, urls)
        ctx.close()
    return result | {"conversion_stopped": stopped}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--profiles", default="desktop,phone")
    ap.add_argument("--titles", default=",".join(TITLES))
    ap.add_argument("--pairs", type=int, default=gates.MIN_TRIALS)
    ap.add_argument("--plugins", default="all", help="one plugin state, as for the bench")
    args = ap.parse_args(argv)
    titles = args.titles.split(",")
    unknown = set(titles) - set(TITLES)
    if unknown:
        ap.error(f"unknown titles {', '.join(sorted(unknown))}; titles: {', '.join(TITLES)}")
    try:
        off = plugins.parse_state(args.plugins)
    except plugins.PluginStateError as e:
        ap.error(str(e))
    cfg = config.load()
    missing = sorted({TITLES[t][0] for t in titles} - set(cfg.items))
    if missing:
        ap.error(f"config.local.json has no {', '.join(missing)}; run python -m harness.discover")

    outdir = prepare_outdir(RUNS, args.label)
    served = build.build()
    sha, dirty = build.parse_header(served)
    sides = {"vanilla": session.Override(""), "skin": session.Override(served)}
    out = {
        "label": args.label,
        "date": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "skin_sha": sha,
        "skin_dirty": dirty,
        "server_version": server_version(cfg.url),
        "plugins": args.plugins,
        "pairs": args.pairs,
        "cells": {},
    }
    t0 = time.monotonic()

    def save(o):
        o["seconds"] = round(time.monotonic() - t0)
        (outdir / "player.json").write_text(json.dumps(o, indent=1) + "\n")

    with lock.hold(timed=True), sync_playwright() as pw:
        browser = session.launch(pw)
        out["browser_version"] = browser.version
        for prof_name in args.profiles.split(","):
            prof = PROFILES[prof_name]
            state = session.login_state(browser, cfg, prof)
            for title in titles:
                key, convert = TITLES[title]
                cell = f"{prof_name}/{title}"
                pairs = run_pairs(lambda side: play_trial(browser, cfg, prof, cfg.items[key], convert, state, sides[side], off), args.pairs)
                out["cells"][cell] = {"pairs": pairs}
                save(out)
                print(describe(cell, pairs), flush=True)
        browser.close()
    save(out)
    print(f"{outdir}: {len(out['cells'])} cells in {out['seconds']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
