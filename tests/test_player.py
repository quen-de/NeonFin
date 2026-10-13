import pytest
from playwright.sync_api import sync_playwright

from harness import player, session
from harness.profiles import PROFILES

DIRECT = "https://srv/Videos/abc/stream.mp4?Static=true&mediaSourceId=abc&PlaySessionId=p1&api_key=secret"
HLS = "https://srv/videos/abc/master.m3u8?VideoCodec=h264&PlaySessionId=p2&TranscodeReasons=VideoCodecNotSupported&api_key=secret"


def test_pairs_alternate_sides_and_the_warm_up_pair_is_dropped():
    calls = []
    pairs = player.run_pairs(lambda side: calls.append(side) or {"side": side}, 2, [])
    assert calls == ["skin", "vanilla", "vanilla", "skin", "skin", "vanilla"]
    assert len(pairs) == 2 and all(set(p) == {"skin", "vanilla"} for p in pairs)


def test_a_failed_trial_keeps_the_pairs_before_it_and_says_where():
    calls, kept = [], []

    def trial(side):
        if len(calls) == 4:
            raise player.TrialError("never played", True)
        calls.append(side)
        return {"side": side}

    with pytest.raises(player.TrialError) as failed:
        player.run_pairs(trial, 3, kept)
    assert len(kept) == 1
    assert (failed.value.pair, failed.value.side, failed.value.conversion_stopped) == (2, "skin", True)


def test_play_method_tells_a_direct_file_from_a_conversion():
    assert player.play_method([DIRECT]) == "direct"
    assert player.play_method([DIRECT, HLS]) == "converted (VideoCodecNotSupported)"
    assert player.play_method([]) == "unknown"


def test_play_session_is_read_from_any_casing():
    assert player.play_session([DIRECT]) == "p1"
    assert player.play_session(["https://srv/videos/x/main.m3u8?playSessionId=p3"]) == "p3"
    assert player.play_session(["https://srv/Items/x/PlaybackInfo"]) is None


def test_after_a_fallback_the_session_stopped_is_the_conversion():
    assert player.play_session([DIRECT, HLS]) == "p2"


class FakePage:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def route(self, match, handler):
        self.calls.append(("route", match("https://srv/videos/x/hls1/main/3.mp4"), match("https://srv/Videos/ActiveEncodings?x=1")))

    def evaluate(self, js, arg=None):
        self.calls.append(("evaluate", arg))
        if self.fail:
            raise RuntimeError("page gone")
        return True


def test_a_direct_trial_has_no_conversion_to_stop():
    page = FakePage()
    assert player.stop_conversion(page, [DIRECT]) is None
    assert player.stop_conversion(page, []) is None
    assert page.calls == []


def test_a_conversion_is_cut_off_from_its_segments_then_stopped_by_its_own_session():
    page = FakePage()
    assert player.stop_conversion(page, [DIRECT, HLS]) is True
    assert page.calls == [("route", True, False), ("evaluate", ["p2", player.STOP_TIMEOUT_MS])]


def test_a_conversion_that_cannot_be_stopped_says_so():
    assert player.stop_conversion(FakePage(fail=True), [HLS]) is False
    assert player.stop_conversion(FakePage(), ["https://srv/videos/x/master.m3u8?VideoCodec=h264"]) is False


def test_timings_count_from_the_click_and_from_the_input_that_woke_the_controls():
    start = {"click": 100.0, "info": 130.0, "loadstart": 400.0, "metadata": 900.0, "frame": 1000.0}
    osd = {"input": 5000.0, "shown": 5004.0, "visible": 5300.0, "frame": 40.0}
    assert player.timings(start, osd) == {
        "info_ms": 30.0,
        "start_ms": 300.0,
        "metadata_ms": 800.0,
        "first_frame_ms": 900.0,
        "controls_shown_ms": 4.0,
        "controls_visible_ms": 300.0,
        "controls_frame_ms": 40.0,
    }


def test_a_missing_mark_is_none_and_medians_skip_it():
    t = player.timings(
        {"click": 0.0, "info": None, "loadstart": 1.0, "metadata": 2.0, "frame": 3.0},
        {"input": None, "shown": 9.0, "visible": 10.0, "frame": None},
    )
    assert t["info_ms"] is None and t["controls_shown_ms"] is None and t["controls_frame_ms"] is None and t["first_frame_ms"] == 3.0
    pairs = [{"vanilla": {"info_ms": None}, "skin": {"info_ms": 5.0}}, {"vanilla": {"info_ms": 7.0}, "skin": {"info_ms": 9.0}}]
    assert player.medians(pairs, "vanilla")["info_ms"] == 7.0
    assert player.medians(pairs, "skin")["first_frame_ms"] is None


def test_describe_names_the_play_method_and_counts_controls_that_hid():
    trial = {m: 10.0 for m in player.METRICS} | {"method": "direct", "controls_held": True, "conversion_stopped": None, "css_hits": 1}
    pairs = [{"vanilla": trial, "skin": trial | {"controls_held": False}}]
    line = player.describe("desktop/direct", pairs)
    assert "first_frame 10->10" in line and "[direct]" in line and "controls hid early in 1 trial" in line
    assert "not stopped" not in line and "no CSS" not in line


def test_describe_flags_a_conversion_left_running_and_a_page_that_never_loaded_the_css():
    trial = {m: 10.0 for m in player.METRICS} | {
        "method": "converted (x)",
        "controls_held": True,
        "conversion_stopped": True,
        "css_hits": 1,
    }
    pairs = [{"vanilla": trial | {"css_hits": 0}, "skin": trial | {"conversion_stopped": False}}]
    line = player.describe("phone/convert", pairs)
    assert "conversion not stopped in 1 trial" in line and "no CSS request in 1 trial" in line


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        b = session.launch(pw)
        yield b
        b.close()


def test_hidden_hevc_is_refused_and_h264_still_offered(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None, freeze_clock=False)
    page.goto("about:blank")
    page.evaluate(player.NO_HEVC_JS)
    got = page.evaluate("""() => [MediaSource.isTypeSupported('video/mp4; codecs="hvc1.2.4.L153.B0"'),
        MediaSource.isTypeSupported('video/mp4; codecs="avc1.640028"'),
        document.createElement('video').canPlayType('video/mp4; codecs="hev1.1.6.L93.B0"')]""")
    assert got == [False, True, ""]
    ctx.close()


def test_only_a_video_started_by_play_counts(browser):
    # A theme video or trailer on the title page may load before Play.
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None, freeze_clock=False)
    page.set_content("<video id=theme></video><div class=mainDetailButtons><button>Play</button></div><video id=player></video>")
    page.evaluate(player.PLAYER_JS)
    page.evaluate("() => document.getElementById('theme').dispatchEvent(new Event('loadstart'))")
    assert page.evaluate("() => window.__nfp.loadstart") is None
    page.click("button")
    page.evaluate("() => document.getElementById('player').dispatchEvent(new Event('loadstart'))")
    assert page.evaluate("() => [window.__nfp.loadstart >= window.__nfp.click, window.__nfp.video.id]") == [True, "player"]
    ctx.close()


def test_controls_are_visible_once_the_frame_that_shows_them_is_done(browser):
    # As in the player, the bar leaves display:none and shows at full opacity at once; what CSS
    # can cost is the style, layout and paint of the frame that shows it.
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None, freeze_clock=False)
    page.set_content("""<style>.hide { display: none; } .videoOsdBottom-hidden { opacity: 0; }
      .videoOsdBottom i { display: inline-block; width: 3px; height: 3px; border-radius: 50%; box-shadow: 0 0 6px red; }</style>
      <div class="videoOsdBottom videoOsdBottom-hidden hide"></div>
      <script>document.querySelector('.videoOsdBottom').innerHTML = '<i></i>'.repeat(40000);
      document.addEventListener('pointermove', () => {
        document.querySelector('.videoOsdBottom').classList.remove('videoOsdBottom-hidden', 'hide');
      });</script>""")
    page.evaluate(player.PLAYER_JS)
    page.evaluate(player.OSD_ARM)
    page.mouse.move(10, 10)
    page.wait_for_function("() => window.__nfp.osd.visible !== null", timeout=10_000)
    osd = page.evaluate("() => window.__nfp.osd")
    assert osd["frame"] >= 20
    assert osd["visible"] - osd["shown"] >= 20
    ctx.close()


def test_a_stop_the_server_never_answers_gives_up(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None, freeze_clock=False)
    page.goto("about:blank")
    page.evaluate("() => { window.ApiClient = { stopActiveEncodings: () => new Promise(() => {}) }; }")
    assert page.evaluate(player.STOP_JS, ["p", 100]) is False
    ctx.close()


def test_controls_time_runs_from_the_waking_input_to_full_opacity(browser):
    ctx, page = session.new_page(browser, PROFILES["desktop"], None, None, freeze_clock=False)
    page.set_content("""<style>.videoOsdBottom { transition: opacity 0.2s; height: 50px; }
      .videoOsdBottom-hidden { opacity: 0; }</style>
      <div class="videoOsdBottom videoOsdBottom-hidden hide"></div>
      <script>document.addEventListener('pointermove', () => {
        const t = performance.now(); while (performance.now() - t < 30) {}
        document.querySelector('.videoOsdBottom').classList.remove('videoOsdBottom-hidden', 'hide');
      });</script>""")
    page.evaluate(player.PLAYER_JS)
    page.evaluate(player.OSD_ARM)
    page.mouse.move(10, 10)
    page.wait_for_function("() => window.__nfp.osd.visible !== null", timeout=5_000)
    osd = page.evaluate("() => window.__nfp.osd")
    assert osd["shown"] - osd["input"] >= 30
    assert osd["visible"] - osd["shown"] >= 150
    ctx.close()


def test_taps_register_on_a_page_whose_clock_is_frozen(browser):
    # Jellyfin ignores a touch less than 300 ms after the last one by Date; on a frozen clock
    # every tap after the first would look like the same instant.
    ctx, page = session.new_page(browser, PROFILES["phone"], None, None)
    page.goto("about:blank")
    page.set_content("<div style='width:100vw;height:100vh'></div>")
    page.evaluate("""() => { window.taps = 0; let last = 0;
      document.addEventListener('pointerdown', () => { const now = new Date().getTime();
        if (now - last > 300) { last = now; window.taps += 1; } }); }""")
    player.wake(page, PROFILES["phone"])
    player.wake(page, PROFILES["phone"])
    assert page.evaluate("taps") == 2
    ctx.close()
