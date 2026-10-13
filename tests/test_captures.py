import sys
import time

from harness import captures


def test_one_capture_only_run_per_css_mode_and_plugin_state():
    cmds = captures.commands("m2", ["dist", "vanilla"], ["all", "without:media-bar-enhanced,custom-tabs"], ["--show-volatile"])
    assert [label for label, _ in cmds] == [
        "m2-dist-all",
        "m2-dist-no-media-bar-enhanced-custom-tabs",
        "m2-vanilla-all",
        "m2-vanilla-no-media-bar-enhanced-custom-tabs",
    ]
    label, argv = cmds[1]
    assert argv[1:] == [
        "-m",
        "harness.run",
        "--label",
        label,
        "--css",
        "dist",
        "--plugins",
        "without:media-bar-enhanced,custom-tabs",
        "--no-perf",
        "--show-volatile",
    ]


def test_runs_go_side_by_side_and_report_each_exit_code():
    sleep = [sys.executable, "-c", "import time, sys; time.sleep(0.6); sys.exit(int(sys.argv[1]))"]
    cmds = [(f"r{i}", [*sleep, str(i % 2)]) for i in range(4)]
    t0 = time.monotonic()
    codes = captures.run_all(cmds, jobs=4)
    assert time.monotonic() - t0 < 2.0
    assert {label: code for label, (code, _) in codes.items()} == {"r0": 0, "r1": 1, "r2": 0, "r3": 1}


def test_a_repeated_plugin_state_runs_once():
    assert [label for label, _ in captures.commands("m2", ["dist"], ["all", "all"], [])] == ["m2-dist-all"]


def test_a_failed_run_reports_its_count_and_first_failures():
    out = "\n".join(["runs/x: 20 captures, 9 failures", *[f"  FAIL desktop/r{i}: never became visible" for i in range(9)]])
    report = captures.report(out)
    assert report.splitlines()[0] == "runs/x: 20 captures, 9 failures"
    assert "FAIL desktop/r0" in report and "FAIL desktop/r8" not in report and "5 more" in report


def test_a_crashed_run_reports_its_last_lines():
    out = "\n".join(["Traceback (most recent call last):", *[f"  line {i}" for i in range(8)], "RuntimeError: boom"])
    assert captures.report(out).splitlines()[-1] == "RuntimeError: boom"
