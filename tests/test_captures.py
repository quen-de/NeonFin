import sys
import time

from harness import captures


def test_one_capture_only_run_per_css_mode_and_plugin_state():
    cmds = captures.commands("m2", ["dist", "vanilla"], ["all", "without:media-bar,custom-tabs"], ["--show-volatile"])
    assert [label for label, _ in cmds] == [
        "m2-dist-all",
        "m2-dist-no-media-bar-custom-tabs",
        "m2-vanilla-all",
        "m2-vanilla-no-media-bar-custom-tabs",
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
        "without:media-bar,custom-tabs",
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
