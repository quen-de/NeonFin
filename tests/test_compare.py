import gzip
import json

from PIL import Image

from harness import compare


def el(label, **s):
    return {"label": label, "s": s}


def test_diff_styles_reports_added_removed_changed():
    a = {"k1": el("div.a", color="red"), "k2": el("div.b", color="red")}
    b = {"k1": el("div.a", color="blue"), "k3": el("div.c", color="red")}
    d = compare.diff_styles(a, b)
    assert d["only_a"] == ["k2"] and d["only_b"] == ["k3"]
    assert d["changed"] == {"k1": {"color": ("red", "blue")}}


def test_group_changes_counts_identical_changes():
    changed = {"k1": {"color": ("red", "blue")}, "k2": {"color": ("red", "blue")}}
    assert compare.group_changes(changed, {"k1": "div.a", "k2": "div.a"}) == [(2, "div.a", "color", "red", "blue")]


def test_perf_deltas_flag_only_beyond_spread():
    pa = {"phone": {"home": {"frame_p95": {"median": 20, "min": 18, "max": 24}}}}
    pb_small = {"phone": {"home": {"frame_p95": {"median": 22, "min": 20, "max": 25}}}}
    pb_big = {"phone": {"home": {"frame_p95": {"median": 40, "min": 38, "max": 42}}}}
    assert compare.perf_deltas(pa, pb_small)[0]["significant"] is False
    assert compare.perf_deltas(pa, pb_big)[0]["significant"] is True


def test_environment_warnings():
    sa = {"browser_version": "154.0", "server_version": "12.2.0"}
    assert compare.environment_warnings(sa, dict(sa)) == []
    w = compare.environment_warnings(sa, {"browser_version": "155.0", "server_version": "12.2.0"})
    assert len(w) == 1 and "browser_version" in w[0]


def write_run(d, snap, color):
    (d / "desktop").mkdir(parents=True)
    with gzip.open(d / "desktop" / "home.styles.json.gz", "wt") as f:
        json.dump(snap, f)
    Image.new("RGB", (4, 4), color).save(d / "desktop" / "home.png")
    (d / "summary.json").write_text(json.dumps({"browser_version": "1", "server_version": "1", "perf": {}}))


def test_compare_end_to_end(tmp_path):
    write_run(tmp_path / "A", {"k": el("div.a", color="red")}, "white")
    write_run(tmp_path / "B", {"k": el("div.a", color="red")}, "white")
    report, n = compare.compare(tmp_path / "A", tmp_path / "B")
    assert n == 0 and "desktop/home: 0 style diffs" in report

    write_run(tmp_path / "C", {"k": el("div.a", color="blue")}, "black")
    report, n = compare.compare(tmp_path / "A", tmp_path / "C")
    assert n == 1 and "`div.a` color" in report
    assert (tmp_path / "C" / "desktop" / "home.diff.png").exists()


def test_diff_styles_ignores_transforms_of_elements_hidden_in_both_runs():
    # A closed MUI drawer is visibility:hidden and parked off-screen by an
    # offset measured at mount, racing the custom CSS. It paints nothing.
    a = {
        "drawer": el("div.paper", visibility="hidden", transform="matrix(1, 0, 0, 1, -169.219, 0)"),
        "shown": el("div.card", visibility="visible", transform="none"),
    }
    b = {
        "drawer": el("div.paper", visibility="hidden", transform="matrix(1, 0, 0, 1, -172.844, 0)"),
        "shown": el("div.card", visibility="visible", transform="scale(1.1)"),
    }
    assert compare.diff_styles(a, b)["changed"] == {"shown": {"transform": ("none", "scale(1.1)")}}
