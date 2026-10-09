from harness import run


def test_screenshots_hide_volatile_parts_unless_asked_to_show_them():
    volatile = ["#slides-container", ".clock"]
    assert run.shot_hidden(volatile, show_volatile=False) == ("#slides-container", ".clock")
    assert run.shot_hidden(volatile, show_volatile=True) == ()
