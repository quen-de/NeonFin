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
    fails = gates.evaluate(summary("vanilla", perf(20, 400, 1000)), summary(perf=perf(27, 470, 1000)), set())
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
