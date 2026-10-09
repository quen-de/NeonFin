import pytest

from harness import perf


def test_percentile_nearest_rank():
    assert perf.percentile([1, 2, 3, 4, 100], 0.5) == 3
    assert perf.percentile([1, 2, 3, 4, 100], 0.95) == 100


def test_frame_stats_counts_dropped_frames():
    s = perf.frame_stats([16.7] * 18 + [40, 60])
    assert s["frames"] == 20 and s["dropped"] == 2
    assert s["frame_p50"] == pytest.approx(16.7)


def test_frame_stats_rejects_empty():
    with pytest.raises(ValueError):
        perf.frame_stats([])


def test_metric_deltas_seconds_to_ms():
    m0 = {"RecalcStyleDuration": 0.1, "LayoutDuration": 0.2, "TaskDuration": 1.0, "ScriptDuration": 0.5}
    m1 = {"RecalcStyleDuration": 0.15, "LayoutDuration": 0.2, "TaskDuration": 1.5, "ScriptDuration": 0.5}
    assert perf.metric_deltas(m0, m1) == {"recalc_style_ms": 50.0, "layout_ms": 0.0, "task_ms": 500.0, "script_ms": 0.0}


def test_aggregate_median_min_max():
    agg = perf.aggregate([{"a": 1.0}, {"a": 3.0}, {"a": 2.0}])
    assert agg == {"a": {"median": 2.0, "min": 1.0, "max": 3.0}}
