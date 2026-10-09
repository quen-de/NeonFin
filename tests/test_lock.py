import threading
import time

from harness import lock


def test_untimed_work_waits_for_a_timed_run(tmp_path):
    path = tmp_path / "timing.lock"
    said, entered = [], []

    def capture():
        with lock.hold(timed=False, path=path, notify=said.append):
            entered.append(time.monotonic())

    with lock.hold(timed=True, path=path):
        t = threading.Thread(target=capture)
        t.start()
        time.sleep(0.3)
        assert entered == []
        released = time.monotonic()
    t.join(5)
    assert entered and entered[0] >= released
    assert said == ["waiting for a timed run to finish"]


def test_untimed_work_runs_side_by_side(tmp_path):
    path = tmp_path / "timing.lock"
    said = []
    with lock.hold(timed=False, path=path), lock.hold(timed=False, path=path, notify=said.append):
        pass
    assert said == []


def test_a_timed_run_waits_for_untimed_work(tmp_path):
    path = tmp_path / "timing.lock"
    said = []
    with lock.hold(timed=False, path=path):
        t = threading.Thread(target=lambda: lock.hold(timed=True, path=path, notify=said.append).__enter__())
        t.daemon = True
        t.start()
        time.sleep(0.3)
        assert said == ["waiting for other harness runs to finish"]
