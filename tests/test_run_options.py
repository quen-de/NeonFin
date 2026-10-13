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


class FakePage:
    def __init__(self, url):
        self.url = url


def _opener(monkeypatch, fail_times):
    from harness import session

    calls = []

    def open_route(page, cfg, route, volatile):
        calls.append(page.url)
        if len(calls) <= fail_times:
            raise session.RouteError("anchor never visible")
        return True

    monkeypatch.setattr(session, "open_route", open_route)
    return calls


def test_a_lost_session_signs_in_again_once(monkeypatch):
    from harness.profiles import Route

    calls = _opener(monkeypatch, 1)
    pages = [FakePage("https://jf.example/web/#/login")]
    got = run.open_signed_in(lambda: pages[-1], lambda: pages.append(FakePage("https://jf.example/web/#/home")), None, Route("home", "", "a"), [])
    assert got == (True, True) and calls == ["https://jf.example/web/#/login", "https://jf.example/web/#/home"]


def test_a_failure_while_still_signed_in_is_not_retried(monkeypatch):
    import pytest

    from harness import session
    from harness.profiles import Route

    _opener(monkeypatch, 9)
    relogins = []
    with pytest.raises(session.RouteError):
        run.open_signed_in(lambda: FakePage("https://jf.example/web/#/home"), lambda: relogins.append(1), None, Route("home", "", "a"), [])
    assert relogins == []


def test_a_second_sign_out_is_a_failure(monkeypatch):
    import pytest

    from harness import session
    from harness.profiles import Route

    _opener(monkeypatch, 9)
    relogins = []
    with pytest.raises(session.RouteError):
        run.open_signed_in(lambda: FakePage("https://jf.example/web/#/login"), lambda: relogins.append(1), None, Route("home", "", "a"), [])
    assert relogins == [1]
