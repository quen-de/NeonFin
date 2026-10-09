from harness import gates


def summary(css_mode="dist", perf=None, routes=None, **extra):
    return {
        "css_mode": css_mode,
        "plugins": "all",
        "server_version": "12.0",
        "browser_version": "1",
        "perf": perf or {},
        "routes": routes or {},
        "failures": [],
        "trials": 7,
        **extra,
    }


def metric(median, lo=None, hi=None):
    return {"median": median, "min": median if lo is None else lo, "max": median if hi is None else hi}


def perf(recalc, task, anchor, anchor_max=None):
    return {
        "desktop": {
            "home": {"recalc_style_ms": metric(recalc), "task_ms": metric(task), "anchor_ms": metric(anchor, anchor, anchor_max or anchor)}
        }
    }


def test_skin_within_every_gate_passes():
    vanilla = summary("vanilla", perf(20, 400, 1000, 1200))
    skin = summary(perf=perf(25, 450, 1150), routes={"desktop/home": {"glass": 2, "blue": {}, "contrast_failures": []}})
    assert gates.evaluate(vanilla, skin, {"home"}) == []


def test_recalc_and_task_time_ratios():
    fails = gates.evaluate(
        summary("vanilla", perf(20, 400, 1000), plugins="none"), summary(perf=perf(27, 470, 1000), plugins="none"), set()
    )
    assert len(fails) == 2
    assert any("recalc_style_ms" in f for f in fails) and any("task_ms" in f for f in fails)


def test_page_ready_must_stay_within_vanilla_spread():
    fails = gates.evaluate(summary("vanilla", perf(20, 400, 1000, 1200)), summary(perf=perf(20, 400, 1300)), set())
    assert len(fails) == 1 and "anchor_ms" in fails[0]


def test_glass_budget_by_profile_with_one_more_while_a_menu_is_open():
    routes = {"desktop/home": {"glass": 4}, "desktop/usermenu": {"glass": 4}, "phone/home": {"glass": 1}}
    fails = gates.evaluate(summary("vanilla"), summary(routes=routes), set())
    assert len(fails) == 2
    assert any(f.startswith("desktop/home") for f in fails) and any(f.startswith("phone/home") for f in fails)


def test_blue_and_contrast_only_count_in_scope():
    routes = {
        "desktop/home": {"glass": 0, "blue": {"div background": 1}, "contrast_failures": [{"ratio": 2}]},
        "desktop/movies": {"glass": 0, "blue": {"div background": 1}},
    }
    fails = gates.evaluate(summary("vanilla"), summary(routes=routes), {"home"})
    assert len(fails) == 2 and all(f.startswith("desktop/home") for f in fails)


def test_runs_must_be_comparable():
    fails = gates.evaluate(summary("vanilla"), summary(plugins="none"), set())
    assert any("plugins differs" in f for f in fails)
    fails = gates.evaluate(summary("dist"), summary("vanilla"), set())
    assert any("not a vanilla run" in f for f in fails) and any("second run is vanilla" in f for f in fails)


def test_a_skin_run_missing_a_measured_route_fails():
    vanilla = summary("vanilla", perf(20, 400, 1000))
    assert gates.evaluate(vanilla, summary(perf={}), set()) == ["desktop/home: no skin performance to compare"]


def test_trials_must_be_recorded_equal_and_at_least_seven():
    v = perf(20, 400, 1000)
    assert gates.evaluate(summary("vanilla", v, trials=7), summary(perf=v, trials=5), set()) == [
        "trials: 7 vs 5, both must be at least 7 and equal"
    ]
    assert gates.evaluate(summary("vanilla", v, trials=5), summary(perf=v, trials=5), set()) == [
        "trials: 5 vs 5, both must be at least 7 and equal"
    ]
    assert gates.evaluate(summary("vanilla", v, trials=None), summary(perf=v), set()) == [
        "trials: None vs 7, both must be at least 7 and equal"
    ]


def test_plugin_built_desktop_home_runs_under_its_accepted_exception():
    vanilla = summary("vanilla", perf(16, 420, 1000))
    assert gates.evaluate(vanilla, summary(perf=perf(28, 500, 1000)), set()) == []
    fails = gates.evaluate(vanilla, summary(perf=perf(33, 530, 1000)), set())
    assert len(fails) == 2 and all("desktop/home" in f for f in fails)


def test_the_exception_covers_only_plugin_built_home():
    plain = gates.evaluate(
        summary("vanilla", perf(16, 420, 1000), plugins="none"), summary(perf=perf(28, 500, 1000), plugins="none"), set()
    )
    assert len(plain) == 2
    assert gates.limits("all", "desktop", "movies") == {"recalc_style_ms": 1.3, "task_ms": 1.15}


def pair(v_recalc, s_recalc, v_task=400, s_task=400, v_anchor=1000, s_anchor=1000):
    return {
        "vanilla": {"recalc_style_ms": v_recalc, "task_ms": v_task, "anchor_ms": v_anchor},
        "skin": {"recalc_style_ms": s_recalc, "task_ms": s_task, "anchor_ms": s_anchor},
    }


LIMITS = {"recalc_style_ms": 1.3, "task_ms": 1.15}


def test_no_early_decision_before_four_pairs():
    assert gates.decide([pair(10, 30)] * 3, LIMITS) is None


def test_every_pair_far_over_a_ratio_decides_a_fail():
    assert gates.decide([pair(10, 20), pair(10, 18), pair(11, 19), pair(10, 21)], LIMITS) == "fail"


def test_every_pair_well_inside_every_ratio_decides_a_pass():
    assert gates.decide([pair(10, 10.5), pair(10, 11), pair(11, 10), pair(10, 9)], LIMITS) == "pass"


def test_one_noisy_pair_inside_the_limit_does_not_block_a_pass():
    assert gates.decide([pair(10, 10.5), pair(10, 12.5), pair(11, 10), pair(10, 9)], LIMITS) == "pass"


def test_a_pair_across_the_line_leaves_the_cell_undecided():
    assert gates.decide([pair(10, 10.5), pair(10, 13.5), pair(11, 10), pair(10, 9)], LIMITS) is None
    assert gates.decide([pair(10, 20), pair(10, 18), pair(11, 14), pair(10, 21)], LIMITS) is None


def test_page_ready_slower_than_every_vanilla_load_decides_a_fail():
    pairs = [pair(10, 10, v_anchor=1000 + i, s_anchor=1500) for i in range(4)]
    assert gates.decide(pairs, LIMITS) == "fail"


def bench(cells, **extra):
    return {"css_mode": "dist", "server_version": "12.0", "browser_version": "1", "cells": cells, **extra}


def test_bench_cells_decided_early_need_no_more_pairs():
    b = bench({"all/desktop/movies": {"pairs": [pair(10, 10.5)] * 4}, "none/phone/home": {"pairs": [pair(10, 20)] * 4}})
    fails = gates.evaluate_bench(b)
    assert len(fails) == 1 and fails[0].startswith("none/phone/home: recalc_style_ms")


def test_undecided_bench_cells_need_seven_pairs_then_judge_medians():
    near = [pair(10, 12.5), pair(10, 13.5)] * 2
    assert gates.evaluate_bench(bench({"all/desktop/movies": {"pairs": near}})) == [
        "all/desktop/movies: 4 pairs and no early decision, at least 7 needed"
    ]
    seven = [pair(10, 12.5), pair(10, 13.5)] * 3 + [pair(10, 12.9)]
    assert gates.evaluate_bench(bench({"all/desktop/movies": {"pairs": seven}})) == []
    over = [pair(10, 13.5), pair(10, 12.5)] * 3 + [pair(10, 13.4)]
    fails = gates.evaluate_bench(bench({"all/desktop/movies": {"pairs": over}}))
    assert len(fails) == 1 and "recalc_style_ms 13.4 > 1.3x vanilla 10" in fails[0]


def test_bench_cells_use_the_accepted_exception():
    pairs = [pair(16, 28, 420, 500)] * 7
    assert gates.evaluate_bench(bench({"all/desktop/home": {"pairs": pairs}})) == []
    assert len(gates.evaluate_bench(bench({"none/desktop/home": {"pairs": pairs}}))) == 2


def test_gates_cli_judges_a_bench_and_skin_captures(tmp_path, capsys):
    import json

    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "bench.json").write_text(json.dumps(bench({"all/desktop/home": {"pairs": [pair(10, 10.5)] * 4}})))
    (tmp_path / "c").mkdir()
    routes = {"desktop/home": {"glass": 5, "blue": {}, "contrast_failures": []}}
    (tmp_path / "c" / "summary.json").write_text(json.dumps(summary(routes=routes, perf={})))
    assert gates.main(["--bench", str(tmp_path / "b"), str(tmp_path / "c")]) == 1
    out = capsys.readouterr().out
    assert "desktop/home: 5 live glass surfaces" in out and "gates: 1 failure(s)" in out
