import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright.sync_api import sync_playwright

from harness import session
from harness.profiles import PROFILES


def test_patch_branding_replaces_only_custom_css():
    body = json.dumps({"LoginDisclaimer": "hi", "CustomCss": "old", "SplashscreenEnabled": False}).encode()
    out = json.loads(session.patch_branding(body, ".new{}"))
    assert out == {"LoginDisclaimer": "hi", "CustomCss": ".new{}", "SplashscreenEnabled": False}


class _Handler(BaseHTTPRequestHandler):
    posts: list[str] = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        _Handler.posts.append(self.path)
        self.send_response(204)
        self.end_headers()

    do_DELETE = do_POST

    def do_GET(self):
        if self.path.startswith("/pixel.svg"):
            body, ctype = b"<svg xmlns='http://www.w3.org/2000/svg' width='4' height='3'/>", "image/svg+xml"
        elif self.path == "/lazyimg":
            # Far off-screen inside a horizontal scroller: native lazy loading
            # decides by a network-dependent distance, so it varies per run.
            body, ctype = (
                (
                    b"<html><body><div style='width:400px;overflow:hidden;white-space:nowrap'>"
                    b"<div style='display:inline-block;width:30000px'></div>"
                    b"<img id=flag loading=lazy src='/pixel.svg'></div></body></html>"
                ),
                "text/html",
            )
        elif self.path == "/hang":
            time.sleep(30)
            body, ctype = b"late", "text/plain"
        elif self.path == "/hangpage":
            body, ctype = b"<html><body><script>fetch('/hang')</script></body></html>", "text/html"
        elif self.path == "/slow":
            time.sleep(1.5)
            body, ctype = b"ok", "text/plain"
        elif self.path == "/slowpage":
            # Like a lazy image row: DOM busy past networkidle, then a slow fetch
            # with no DOM change until it lands. Only network tracking sees it.
            body, ctype = (
                (
                    b"<html><body><div id=b></div><script>let n = 0; const tick = setInterval(() => {"
                    b"document.getElementById('b').textContent = ++n; if (n === 9) { clearInterval(tick);"
                    b"fetch('/slow').then(r => r.text()).then(t => { window.done = t; }); } }, 100)"
                    b"</script></body></html>"
                ),
                "text/html",
            )
        elif self.path.startswith("/Branding/Configuration"):
            body, ctype = json.dumps({"CustomCss": "live", "LoginDisclaimer": ""}).encode(), "application/json"
        elif self.path == "/plugpage":
            body, ctype = b"<html><body><script src='/MediaBarEnhanced/x.js'></script></body></html>", "text/html"
        elif self.path == "/MediaBarEnhanced/x.js":
            body, ctype = b"window.mb = 1;", "application/javascript"
        else:
            body = (
                b"<html><body><div id=out></div><script>"
                b"fetch('/Branding/Configuration').then(r=>r.json())"
                b".then(j=>{document.getElementById('out').textContent=j.CustomCss})"
                b"</script></body></html>"
            )
            ctype = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = session.launch(pw)
        yield b
        b.close()


def test_override_patches_branding_and_counts_hits(browser, server):
    override = session.Override(".dist{}")
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, override)
    page.goto(server + "/")
    page.wait_for_function("document.getElementById('out').textContent.length > 0")
    assert page.text_content("#out") == ".dist{}"
    assert override.hits == 1
    ctx.close()


def test_navigate_raises_when_anchor_missing(browser, server):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    with pytest.raises(session.RouteError):
        session.navigate(page, server + "/", ".homeSectionsContainer", timeout_ms=1_500)
    ctx.close()


def test_settle_ignores_volatile_churn(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.set_content(
        "<div id=slides><span>0</span></div><div id=still></div>"
        "<script>let n=0;setInterval(()=>{document.querySelector('#slides span').textContent=++n},50)</script>"
    )
    t0 = time.monotonic()
    assert session.settle(page, ["#slides"], quiet_ms=300, cap_ms=5_000) is True
    assert time.monotonic() - t0 < 3
    ctx.close()


def test_settle_gives_up_at_cap(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.set_content("<div id=busy>0</div><script>let n=0;setInterval(()=>{document.getElementById('busy').textContent=++n},50)</script>")
    assert session.settle(page, [], quiet_ms=300, cap_ms=1_500) is False
    ctx.close()


def test_settle_gives_up_at_cap_on_a_request_that_never_ends(browser, server):
    # A server slow to answer one request (a recommendation row built on demand) must not
    # stop a run: the page is unsettled, not an error.
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/hangpage")
    t0 = time.monotonic()
    assert session.settle(page, [], quiet_ms=300, cap_ms=1_500) is False
    assert time.monotonic() - t0 < 5
    ctx.close()


def test_settle_gives_up_at_cap_on_fonts_that_never_load(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.set_content("<script>Object.defineProperty(document.fonts, 'ready', { get: () => new Promise(() => {}) })</script>")
    t0 = time.monotonic()
    assert session.settle(page, [], quiet_ms=300, cap_ms=1_500) is False
    assert time.monotonic() - t0 < 5
    ctx.close()


def test_open_route_turns_failed_state_action_into_route_error(browser, server, monkeypatch):
    from harness.config import Config
    from harness.profiles import Route

    def broken(page):
        page.locator("#does-not-exist").click(timeout=500)

    monkeypatch.setitem(session.STATES, "broken", broken)
    cfg = Config(url=server, user="u", password="p", items={})
    route = Route("x", "", "#out", ready="#out", state="broken")
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    monkeypatch.setattr(session, "route_url", lambda cfg, route: cfg.url + "/")
    page.set_default_timeout(2_000)
    with pytest.raises(session.RouteError, match="state broken failed"):
        session.open_route(page, cfg, route, [])
    ctx.close()


SHOT_PAGE = """<html><body style="margin:0;overflow-x:hidden;background:#000">
<div id=slides style="height:400px;background:#f00"></div>
<div style="display:flex;width:5000px;height:1600px;background:#000"></div>
<div id=menu style="position:fixed;bottom:0;right:0;width:100px;height:100px;background:#0f0"></div>
<div id=pop style="position:fixed;top:10px;left:10px;width:50px;height:50px;background:#00f"></div>
</body></html>"""


def _shoot(browser, tmp_path, route):
    from PIL import Image

    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.set_content(SHOT_PAGE)
    path = tmp_path / f"{route.name}.png"
    session.screenshot(page, route, ["#slides"], path)
    ctx.close()
    return Image.open(path).convert("RGB")


def test_screenshot_content_route_is_full_height_but_viewport_wide(browser, tmp_path):
    from harness.profiles import Route

    im = _shoot(browser, tmp_path, Route("x", "", "#menu"))
    # body overflow-x:hidden means no user ever sees past 1440 px.
    assert im.size == (1440, 2000)


def test_screenshot_state_route_is_viewport_only(browser, tmp_path):
    from harness.profiles import Route

    im = _shoot(browser, tmp_path, Route("x", "", "#menu", state="usermenu"))
    assert im.size == (1440, 900)
    assert im.getpixel((1390, 850)) == (0, 255, 0)  # fixed overlay at the viewport bottom


def test_screenshot_hides_volatile_without_covering_overlays(browser, tmp_path):
    from harness.profiles import Route

    im = _shoot(browser, tmp_path, Route("x", "", "#menu", state="usermenu"))
    assert im.getpixel((35, 35)) == (0, 0, 255)  # overlay above the volatile area stays visible
    assert im.getpixel((700, 200)) == (0, 0, 0)  # volatile area itself is blank, not painted over


def test_settle_waits_for_requests_in_flight(browser, server):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/slowpage")
    session.settle(page, [], quiet_ms=300, cap_ms=5_000)
    assert page.evaluate("window.done") == "ok"
    ctx.close()


def test_new_page_freezes_date_and_pins_timezone(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto("about:blank")
    page.wait_for_timeout(50)
    got = page.evaluate("""() => [Date.now(), new Date().getTime(), new Date(0).getTime(),
        typeof Date(), new Date() instanceof Date, Intl.DateTimeFormat().resolvedOptions().timeZone]""")
    assert got == [session.FIXED_NOW_MS, session.FIXED_NOW_MS, 0, "string", True, "UTC"]
    ctx.close()


def test_new_page_never_reports_playback_to_the_server(browser, server):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/")
    _Handler.posts.clear()
    status = page.evaluate("""() => Promise.all(['/Sessions/Playing', '/Sessions/Playing/Progress',
        '/Sessions/Playing/Stopped'].map(u => fetch(u, {method: 'POST'}).then(r => r.status)))""")
    assert status == [204, 204, 204]
    assert _Handler.posts == []
    ctx.close()


def test_prime_loads_every_lazy_element_and_returns_to_top(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.set_content("""<body style="margin:0"><div style="height:6000px"></div><div id=lazy>x</div>
<script>new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && (e.target.dataset.loaded = 1)))
.observe(document.getElementById('lazy'))</script></body>""")
    session.prime(page)
    assert page.evaluate("[document.getElementById('lazy').dataset.loaded, scrollY]") == ["1", 0]
    ctx.close()


def test_navigate_forgets_requests_of_the_previous_document(browser, server):
    # A request cut off by navigation may never report failure; it must not
    # keep the next page unsettled until the cap.
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/hangpage")
    page.wait_for_timeout(200)
    session.navigate(page, server + "/", "#out")
    t0 = time.monotonic()
    assert session.settle(page, [], quiet_ms=300, cap_ms=3_000) is True
    assert time.monotonic() - t0 < 2.5
    ctx.close()


def test_prime_loads_native_lazy_images_however_far_off_screen(browser, server):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/lazyimg")
    session.prime(page)
    session.settle(page, [], quiet_ms=300, cap_ms=3_000)
    assert page.evaluate("document.getElementById('flag').naturalWidth") == 4
    ctx.close()


def test_screenshot_leaves_out_blurhash_placeholders(browser, tmp_path):
    # Their pixels are decoded off-thread and drawn with no DOM change, so
    # whether one is drawn at capture time is timing, not theme.
    from PIL import Image

    from harness.profiles import Route

    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.set_content("""<body style="margin:0;background:#000"><canvas class=blurhash-canvas width=50 height=50></canvas>
<script>const c = document.querySelector('canvas').getContext('2d'); c.fillStyle = '#f00'; c.fillRect(0, 0, 50, 50);</script></body>""")
    session.screenshot(page, Route("x", "", "body", state="s"), [], tmp_path / "b.png")
    assert Image.open(tmp_path / "b.png").convert("RGB").getpixel((25, 25)) == (0, 0, 0)
    ctx.close()


def test_frozen_clock_moves_only_when_the_harness_advances_it(browser):
    # Apps throttle on Date deltas (the OSD slider ignores updates < 700 ms
    # apart), so a capture step must be able to let time pass on purpose.
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto("about:blank")
    page.evaluate("window.__harnessAdvanceClock(1000)")
    assert page.evaluate("[Date.now(), new Date().getTime()]") == [session.FIXED_NOW_MS + 1000] * 2
    ctx.close()


def test_decode_images_waits_for_background_and_img_sources(browser, server):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/")
    page.set_content(f"""<div style="width:40px;height:30px;background-image:url('{server}/pixel.svg')"></div>
<img src="{server}/pixel.svg?b">""")
    assert session.decode_images(page) == 2
    ctx.close()


@pytest.mark.parametrize("off, loaded", [(frozenset(), 1), (frozenset({"media-bar-enhanced"}), None)])
def test_new_page_can_switch_a_plugin_off(browser, server, off, loaded):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None, off)
    page.goto(server + "/plugpage")
    page.wait_for_load_state("load")
    assert page.evaluate("window.mb ?? null") == loaded
    ctx.close()


LAZY_PAGE = """<html><body style="margin:0;background:#000">
<style>#late { width: 100px; height: 100px; } #late.loaded { background: rgb(255, 0, 0); }</style>
<div style="height:3000px"></div><div id=late></div>
<script>
new IntersectionObserver((es, o) => es.forEach((e) => {
  if (e.isIntersecting) { e.target.classList.add('loaded'); o.unobserve(e.target); } }))
  .observe(document.getElementById('late'));
</script></body></html>"""


def test_full_page_screenshots_load_lazy_content_first(browser, tmp_path):
    from PIL import Image

    from harness.profiles import Route

    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.set_content(LAZY_PAGE)
    path = tmp_path / "lazy.png"
    session.screenshot(page, Route("x", "", "body"), [], path)
    top = page.evaluate("scrollY")
    ctx.close()
    assert Image.open(path).convert("RGB").getpixel((50, 3050)) == (255, 0, 0)
    assert top == 0


GROWING_PAGE = """<body style="margin:0"><div id=feed style="height:3000px"></div><script>
addEventListener('scroll', () => { const f = document.getElementById('feed');
  if (f.offsetHeight < 400000) f.style.height = (f.offsetHeight + 2000) + 'px'; });
</script></body>"""


def test_the_lazy_reveal_stops_on_a_page_that_grows_as_it_scrolls(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.set_content(GROWING_PAGE)
    t0 = time.monotonic()
    session.reveal_lazy(page)
    took, top = time.monotonic() - t0, page.evaluate("scrollY")
    ctx.close()
    assert took < 5 and top == 0


def test_new_page_can_leave_the_clock_running(browser):
    # Player trials time real playback: buffering and the controls read Date.
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None, freeze_clock=False)
    page.goto("about:blank")
    assert abs(page.evaluate("Date.now()") - time.time() * 1000) < 60_000
    ctx.close()


def test_new_page_refuses_plugin_writes_and_sign_in_but_lets_reads_through(browser, server):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/")
    _Handler.posts.clear()
    got = page.evaluate("""() => Promise.all([
        ['/JellyfinEnhanced/jellyseerr/request', 'POST'], ['/HomeScreen/Sections', 'POST'], ['/MediaBarEnhanced/x', 'DELETE'],
        ['/Users/AuthenticateByName', 'POST'], ['/users/authenticatebyname', 'POST'],
        ['/JellyfinEnhanced/x.js', 'GET'], ['/other', 'POST'],
      ].map(([u, m]) => fetch(u, { method: m }).then((r) => r.status, () => 'refused')))""")
    assert got == ["refused"] * 5 + [200, 204]
    assert _Handler.posts == ["/other"]
    ctx.close()


def test_new_page_refuses_the_servers_own_writes_but_lets_playback_through(browser, server):
    # A stray click must not favourite, mark played, rate, rearrange, delete or sign out on the
    # real server. The player still asks for its stream, which is a POST.
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/")
    _Handler.posts.clear()
    writes = [
        ["/UserFavoriteItems/abc", "POST"], ["/Users/u1/FavoriteItems/abc", "DELETE"], ["/UserPlayedItems/abc", "POST"],
        ["/Users/u1/PlayedItems/abc", "POST"], ["/UserItems/abc/Rating?likes=true", "POST"],
        ["/DisplayPreferences/usersettings?client=emby", "POST"], ["/Users/Configuration?userId=u1", "POST"],
        ["/Users/Password", "POST"], ["/QuickConnect/Authorize?code=1", "POST"], ["/Playlists", "POST"],
        ["/Playlists/p1/Items?ids=abc", "POST"], ["/Collections/c1/Items", "DELETE"], ["/Items/abc", "DELETE"],
        ["/Items/abc", "POST"], ["/Items/abc/Refresh", "POST"], ["/Items/abc/Images/Primary", "DELETE"],
        ["/UserImage?userId=u1", "POST"], ["/Sessions/Logout", "POST"], ["/Library/Refresh", "POST"],
        ["/UserItems/abc/UserData", "POST"], ["/Users/u1/Items/abc/UserData", "POST"], ["/Items?ids=abc", "DELETE"],
    ]
    allowed = [["/Items/abc/PlaybackInfo?userId=u1", "POST"], ["/Sessions/Capabilities/Full", "POST"],
               ["/Videos/ActiveEncodings?deviceId=d1", "DELETE"], ["/other?then=/Library/Refresh", "POST"],
               ["/Items/abc", "GET"], ["/DisplayPreferences/usersettings", "GET"]]
    got = page.evaluate("""(calls) => Promise.all(calls.map(([u, m]) =>
      fetch(u, { method: m }).then((r) => r.status, () => 'refused')))""", writes + allowed)
    assert got == ["refused"] * len(writes) + [204, 204, 204, 204, 200, 200], list(zip([w[0] for w in writes + allowed], got))
    ctx.close()


def test_new_page_refuses_every_way_in_and_the_servers_admin_writes(browser, server):
    # Signing in by any route, and anything a page that strays into the dashboard, live TV or
    # another session's remote control could change.
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    page.goto(server + "/")
    writes = [
        ["/Users/u1/Authenticate?pw=x", "POST"], ["/Users/AuthenticateWithQuickConnect", "POST"],
        ["/Users/ForgotPassword", "POST"], ["/Users/ForgotPassword/Pin", "POST"], ["/QuickConnect/Initiate", "POST"],
        ["/Users/New", "POST"], ["/Users/u1", "POST"], ["/Users/u1", "DELETE"], ["/Users/u1/Policy", "POST"],
        ["/Sessions/s1/Playing/Pause", "POST"], ["/Sessions/s1/Message", "POST"], ["/Sessions/s1/User/u2", "DELETE"],
        ["/System/Restart", "POST"], ["/Plugins/p1/Configuration", "POST"], ["/ScheduledTasks/Running/t1", "POST"],
        ["/Packages/Installed/x", "POST"], ["/Auth/Keys?app=x", "POST"], ["/Startup/Complete", "POST"],
        ["/Devices?id=d1", "DELETE"], ["/LiveTv/Timers", "POST"], ["/SyncPlay/New", "POST"],
        ["/Videos/v1/Subtitles/0", "DELETE"], ["/Videos/MergeVersions?ids=a,b", "POST"],
        ["/Items/RemoteSearch/Apply/abc", "POST"], ["/Items/abc/Lyrics", "DELETE"],
    ]
    allowed = [["/Sessions/Viewing?itemId=abc", "POST"], ["/System/Ping", "POST"], ["/Users/u1", "GET"]]
    got = page.evaluate("""(calls) => Promise.all(calls.map(([u, m]) =>
      fetch(u, { method: m }).then((r) => r.status, () => 'refused')))""", writes + allowed)
    assert got == ["refused"] * len(writes) + [204, 204, 200], list(zip([w[0] for w in writes + allowed], got))
    ctx.close()


def test_open_route_prepares_a_state_before_the_page_loads(browser, server, monkeypatch):
    from harness.config import Config
    from harness.profiles import Route

    seen = []
    monkeypatch.setitem(session.PREPARE, "s", lambda page: seen.append(("prepare", page.url)))
    monkeypatch.setitem(session.STATES, "s", lambda page: seen.append(("state", page.url)))
    monkeypatch.setattr(session, "route_url", lambda cfg, route: cfg.url + "/")
    cfg = Config(url=server, user="u", password="p", items={})
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None)
    session.open_route(page, cfg, Route("x", "", "#out", ready="#out", state="s"), [])
    assert [s for s, _ in seen] == ["prepare", "state"]
    assert not seen[0][1].startswith(server) and seen[1][1].startswith(server)
    ctx.close()


class FakeContext:
    def __init__(self, closed, name):
        self.closed, self.name = closed, name

    def close(self):
        self.closed.append(self.name)


def test_shared_pages_close_the_least_recently_used_past_the_limit():
    # Each shared page is a context with the page's timers still running: a long run that kept
    # them all filled the machine and timed tests out.
    closed = []
    pages = session.Pages(2)

    def opener(name):
        return lambda: (FakeContext(closed, name), name)

    assert pages.get("a", opener("a")) == "a"
    pages.get("b", opener("b"))
    assert pages.get("a", opener("a again")) == "a"
    pages.get("c", opener("c"))
    assert closed == ["b"]
    pages.close()
    assert sorted(closed) == ["a", "b", "c"]
