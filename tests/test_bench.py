from harness import bench

LIMITS = {"recalc_style_ms": 1.3, "task_ms": 1.15}


def fake(ratio, calls, task_ratio=None):
    def trial(side, i):
        calls.append((i, side))
        if side == "vanilla":
            return {"recalc_style_ms": 10.0, "task_ms": 400.0, "anchor_ms": 1000.0}
        return {"recalc_style_ms": 10.0 * ratio, "task_ms": 400.0 * (task_ratio or ratio), "anchor_ms": 1000.0}

    return trial


def test_sides_alternate_order_and_the_warm_up_pair_is_dropped():
    calls = []
    pairs = bench.run_cell(fake(1.0, calls), LIMITS, max_pairs=7)
    assert calls[:6] == [(0, "skin"), (0, "vanilla"), (1, "vanilla"), (1, "skin"), (2, "skin"), (2, "vanilla")]
    assert len(pairs) == len(calls) // 2 - 1


def test_a_clear_cell_stops_after_four_pairs():
    assert len(bench.run_cell(fake(1.0, []), LIMITS, max_pairs=7)) == 4
    assert len(bench.run_cell(fake(2.0, []), LIMITS, max_pairs=7)) == 4


def test_a_borderline_cell_runs_every_pair():
    assert len(bench.run_cell(fake(1.28, [], task_ratio=1.1), LIMITS, max_pairs=7)) == 7


def test_cells_cover_every_plugin_state_profile_and_route():
    assert bench.cells(["all", "without:media-bar"], ["desktop"], ["home", "movies"]) == [
        ("all", "desktop", "home"),
        ("all", "desktop", "movies"),
        ("without:media-bar", "desktop", "home"),
        ("without:media-bar", "desktop", "movies"),
    ]


def test_each_cell_is_saved_as_soon_as_it_is_measured():
    saved = []

    def trial_for(state, profile, route):
        if route == "movies":
            raise RuntimeError("route never loaded")
        return fake(1.0, [])

    out = {"max_pairs": 7, "cells": {}}
    try:
        bench.run_cells(
            [("all", "desktop", "home"), ("all", "desktop", "movies")], trial_for, out, lambda o: saved.append(list(o["cells"]))
        )
    except RuntimeError:
        pass
    assert saved == [["all/desktop/home"]]


def test_describe_survives_a_zero_vanilla_metric():
    pair = {
        "vanilla": {"recalc_style_ms": 0.0, "task_ms": 400.0, "anchor_ms": 1000.0},
        "skin": {"recalc_style_ms": 1.0, "task_ms": 400.0, "anchor_ms": 1000.0},
    }
    assert "recalc_style 0.0->1.0 (infx)" in bench.describe("all/desktop/home", [pair] * 4, LIMITS)
