from harness import run


def test_screenshots_hide_volatile_parts_unless_asked_to_show_them():
    volatile = ["#slides-container", ".clock"]
    assert run.shot_hidden(volatile, show_volatile=False) == ("#slides-container", ".clock")
    assert run.shot_hidden(volatile, show_volatile=True) == ()


def test_a_route_whose_plugin_is_off_is_skipped_not_failed():
    from harness.profiles import Route

    plain, calendar = Route("home", "", "a"), Route("calendar", "", "b", needs=frozenset({"jellyfin-enhanced", "plugin-pages"}))
    assert run.split_routes([plain, calendar], frozenset()) == ([plain, calendar], [])
    assert run.split_routes([plain, calendar], frozenset({"plugin-pages"})) == ([plain], [calendar])
