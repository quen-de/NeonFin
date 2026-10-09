"""Scroll performance: rAF frame intervals plus Chrome's main-thread counters."""

from __future__ import annotations

import math
import statistics

RAF_START = """() => {
  window.__nf = { rec: true, frames: [] };
  let last = performance.now();
  const tick = (t) => { window.__nf.frames.push(t - last); last = t; if (window.__nf.rec) requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}"""
RAF_STOP = "() => { window.__nf.rec = false; return window.__nf.frames.slice(1); }"
CDP = {"RecalcStyleDuration": "recalc_style_ms", "LayoutDuration": "layout_ms", "TaskDuration": "task_ms", "ScriptDuration": "script_ms"}


def percentile(values, q: float) -> float:
    """Nearest-rank percentile."""
    s = sorted(values)
    return s[max(0, math.ceil(q * len(s)) - 1)]


def frame_stats(deltas, budget_ms: float = 1000 / 60) -> dict:
    if not deltas:
        raise ValueError("no frames recorded")
    return {
        "frames": len(deltas),
        "frame_p50": percentile(deltas, 0.5),
        "frame_p95": percentile(deltas, 0.95),
        "dropped": sum(d > budget_ms * 1.5 for d in deltas),
    }


def metric_deltas(m0: dict, m1: dict) -> dict:
    return {name: round((m1[k] - m0[k]) * 1000, 1) for k, name in CDP.items()}


def aggregate(trials: list[dict]) -> dict:
    return {
        k: {"median": statistics.median(t[k] for t in trials), "min": min(t[k] for t in trials), "max": max(t[k] for t in trials)}
        for k in trials[0]
    }


def read_metrics(cdp) -> dict:
    return {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}


def scroll_trial(page, cdp, viewport, steps: int = 30, dy: int = 200, gap_ms: int = 50) -> dict:
    page.mouse.move(viewport["width"] / 2, viewport["height"] / 2)
    m0 = read_metrics(cdp)
    page.evaluate(RAF_START)
    for _ in range(steps):
        page.mouse.wheel(0, dy)
        page.wait_for_timeout(gap_ms)
    page.wait_for_timeout(300)
    frames = page.evaluate(RAF_STOP)
    return frame_stats(frames) | metric_deltas(m0, read_metrics(cdp))
