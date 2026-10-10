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


def perf(recalc, task, anchor, anchor_max=None, route="home"):
    return {
        "desktop": {
            route: {"recalc_style_ms": metric(recalc), "task_ms": metric(task), "anchor_ms": metric(anchor, anchor, anchor_max or anchor)}
        }
    }


def test_skin_within_every_gate_passes():
    vanilla = summary("vanilla", perf(20, 400, 1000, 1200))
    skin = summary(perf=perf(25, 450, 1150), routes={"desktop/home": {"glass": 2, "blue": {}, "contrast_failures": []}})
    assert gates.evaluate(vanilla, skin, {"home"}) == []


def test_recalc_and_task_time_ratios():
    fails = gates.evaluate(
        summary("vanilla", perf(20, 400, 1000, route="movies"), plugins="none"),
        summary(perf=perf(27, 470, 1000, route="movies"), plugins="none"),
        set(),
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


def test_exceptions_cover_only_their_own_cells():
    plain = gates.evaluate(
        summary("vanilla", perf(16, 420, 1000), plugins="none"), summary(perf=perf(28, 500, 1000), plugins="none"), set()
    )
    assert plain == ["desktop/home: recalc_style_ms 28 > 1.62x vanilla 16"]
    assert gates.limits("none", "desktop", "home") == {"recalc_style_ms": 1.62, "task_ms": 1.37}
    assert gates.limits("none", "phone", "home") == {"recalc_style_ms": 1.3, "task_ms": 1.15}
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
    return {
        "css_mode": "dist",
        "skin_sha": "abc",
        "skin_dirty": False,
        "intercept_hits": 9,
        "server_version": "12.0",
        "browser_version": "1",
        "cells": cells,
        **extra,
    }


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
    assert len(gates.evaluate_bench(bench({"none/desktop/home": {"pairs": pairs}}))) == 1  # its own, lower ceiling
    assert len(gates.evaluate_bench(bench({"none/phone/home": {"pairs": pairs}}))) == 2


def full_cells(state, pairs):
    from harness.profiles import PERF_ROUTES

    return {f"{state}/{p}/{r}": {"pairs": pairs} for p in ("desktop", "phone") for r in PERF_ROUTES}


def capture(state, **extra):
    from harness.profiles import ROUTES

    routes = {f"{p}/{r.name}": {"glass": 0, "blue": {}, "contrast_failures": []} for p in ("desktop", "phone") for r in ROUTES}
    return summary(**{"plugins": state, "routes": routes, "perf": {}, "trials": None, "skin_sha": "abc", "skin_dirty": False, **extra})


def judge(tmp_path, benches, captures, capsys):
    import json

    args = []
    for i, b in enumerate(benches):
        (tmp_path / f"b{i}").mkdir()
        (tmp_path / f"b{i}" / "bench.json").write_text(json.dumps(b))
        args += ["--bench", str(tmp_path / f"b{i}")]
    for i, c in enumerate(captures):
        (tmp_path / f"c{i}").mkdir()
        (tmp_path / f"c{i}" / "summary.json").write_text(json.dumps(c))
        args.append(str(tmp_path / f"c{i}"))
    code = gates.main(args)
    return code, capsys.readouterr().out


CLEAR = [pair(10, 10.5)] * 4


def test_a_bench_with_captures_for_every_state_passes(tmp_path, capsys):
    code, out = judge(tmp_path, [bench(full_cells("all", CLEAR) | full_cells("none", CLEAR))], [capture("all"), capture("none")], capsys)
    assert code == 0 and "gates: pass" in out


def test_a_bench_alone_never_passes(tmp_path, capsys):
    code, out = judge(tmp_path, [bench(full_cells("all", CLEAR))], [], capsys)
    assert code == 1 and "no capture runs: glass, blue and contrast unchecked" in out


def test_every_cell_of_a_benched_state_is_needed(tmp_path, capsys):
    cells = full_cells("all", CLEAR)
    del cells["all/phone/series"]
    code, out = judge(tmp_path, [bench(cells)], [capture("all")], capsys)
    assert code == 1 and "all/phone/series: not benched" in out


def test_title_pages_are_benched_too(tmp_path, capsys):
    # Title pages carry a blurred copy of the backdrop, so a bench of home and the libraries
    # alone is incomplete.
    cells = {f"all/{p}/{r}": {"pairs": CLEAR} for p in ("desktop", "phone") for r in ("home", "movies", "series")}
    code, out = judge(tmp_path, [bench(cells)], [capture("all")], capsys)
    assert code == 1 and "all/desktop/movie: not benched" in out


def test_benched_states_are_captured_and_all_on_and_off_are_benched(tmp_path, capsys):
    # Speed is gated with every plugin on and every plugin off (spec 7.2); a state with one
    # plugin removed needs captures only.
    both = bench(full_cells("all", CLEAR) | full_cells("none", CLEAR))
    code, out = judge(tmp_path, [both], [capture("all"), capture("without:media-bar")], capsys)
    assert code == 1 and "none: benched but never captured" in out and "without:media-bar" not in out
    (tmp_path / "2").mkdir()
    code, out = judge(tmp_path / "2", [bench(full_cells("all", CLEAR))], [capture("all"), capture("none")], capsys)
    assert code == 1 and "none: captured but never benched" in out
    (tmp_path / "3").mkdir()
    code, out = judge(tmp_path / "3", [bench(full_cells("all", CLEAR))], [capture("all"), capture("without:media-bar")], capsys)
    assert code == 0, out


def test_a_capture_must_cover_every_route(tmp_path, capsys):
    c = capture("all")
    del c["routes"]["phone/osd"]
    code, out = judge(tmp_path, [bench(full_cells("all", CLEAR))], [c], capsys)
    assert code == 1 and "all: no capture of phone/osd" in out


def test_benches_of_one_build_pool_their_pairs(tmp_path, capsys):
    first = full_cells("all", CLEAR)
    first["all/desktop/movies"] = {"pairs": [pair(10, 13.5), pair(10, 12.5)] * 2}
    second = {"all/desktop/movies": {"pairs": [pair(10, 12.4), pair(10, 12.6), pair(10, 12.5)]}}
    code, out = judge(tmp_path, [bench(first), bench(second)], [capture("all")], capsys)
    assert code == 0
    assert "all/desktop/movies: 7 pairs pooled from 2 benches" in out


def test_benches_and_captures_come_from_one_clean_build(tmp_path, capsys):
    cells = full_cells("all", CLEAR)
    cases = [
        ([bench(cells), bench({}, skin_sha="def")], [capture("all")], "benches measured different builds: abc, def"),
        ([bench(cells, skin_dirty=True)], [capture("all")], "a bench of uncommitted CSS"),
        ([bench(cells, css_mode="live")], [capture("all")], "a bench of live CSS, not the build"),
        ([bench(cells)], [capture("all", skin_sha="def")], "captured build def, benched abc"),
        ([bench(cells)], [capture("all", skin_dirty=True)], "a capture of uncommitted CSS"),
    ]
    for i, (benches, captures, message) in enumerate(cases):
        (tmp_path / str(i)).mkdir()
        code, out = judge(tmp_path / str(i), benches, captures, capsys)
        assert code == 1 and message in out, (message, out)


def test_the_exception_ceilings_sit_just_above_what_was_measured():
    assert gates.limits("all", "desktop", "home") == {"recalc_style_ms": 1.9, "task_ms": 1.24}


def test_a_bench_whose_skin_never_reached_the_page_fails(tmp_path, capsys):
    code, out = judge(tmp_path, [bench(full_cells("all", CLEAR), intercept_hits=0)], [capture("all")], capsys)
    assert code == 1 and "the skin CSS never reached the page" in out
