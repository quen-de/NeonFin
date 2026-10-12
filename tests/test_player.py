import pytest
from playwright.sync_api import sync_playwright

from harness import player, session
from harness.profiles import PROFILES

DIRECT = "https://srv/Videos/abc/stream.mp4?Static=true&mediaSourceId=abc&PlaySessionId=p1&api_key=secret"
HLS = "https://srv/videos/abc/master.m3u8?VideoCodec=h264&PlaySessionId=p2&TranscodeReasons=VideoCodecNotSupported&api_key=secret"


def test_pairs_alternate_sides_and_the_warm_up_pair_is_dropped():
    calls = []
    pairs = player.run_pairs(lambda side: calls.append(side) or {"side": side}, 2)
    assert calls == ["skin", "vanilla", "vanilla", "skin", "skin", "vanilla"]
    assert len(pairs) == 2 and all(set(p) == {"skin", "vanilla"} for p in pairs)


def test_play_method_tells_a_direct_file_from_a_conversion():
    assert player.play_method([DIRECT]) == "direct"
    assert player.play_method([DIRECT, HLS]) == "converted (VideoCodecNotSupported)"
    assert player.play_method([]) == "unknown"


def test_play_session_is_read_from_any_casing():
    assert player.play_session([DIRECT]) == "p1"
    assert player.play_session(["https://srv/videos/x/main.m3u8?playSessionId=p3"]) == "p3"
    assert player.play_session(["https://srv/Items/x/PlaybackInfo"]) is None


def test_timings_count_from_the_click_and_from_the_input_that_woke_the_controls():
    start = {"click": 100.0, "info": 130.0, "loadstart": 400.0, "metadata": 900.0, "frame": 1000.0}
    osd = {"input": 5000.0, "shown": 5004.0, "visible": 5300.0}
    assert player.timings(start, osd) == {
        "info_ms": 30.0,
        "start_ms": 300.0,
        "metadata_ms": 800.0,
        "first_frame_ms": 900.0,
        "controls_shown_ms": 4.0,
        "controls_visible_ms": 300.0,
    }


def test_a_missing_mark_is_none_and_medians_skip_it():
    t = player.timings(
        {"click": 0.0, "info": None, "loadstart": 1.0, "metadata": 2.0, "frame": 3.0}, {"input": None, "shown": 9.0, "visible": 10.0}
    )
    assert t["info_ms"] is None and t["controls_shown_ms"] is None and t["first_frame_ms"] == 3.0
    pairs = [{"vanilla": {"info_ms": None}, "skin": {"info_ms": 5.0}}, {"vanilla": {"info_ms": 7.0}, "skin": {"info_ms": 9.0}}]
    assert player.medians(pairs, "vanilla")["info_ms"] == 7.0
    assert player.medians(pairs, "skin")["first_frame_ms"] is None


def test_describe_names_the_play_method_and_counts_controls_that_hid():
    trial = {m: 10.0 for m in player.METRICS} | {"method": "direct", "controls_held": True}
    pairs = [{"vanilla": trial, "skin": trial | {"controls_held": False}}]
    line = player.describe("desktop/direct", pairs)
    assert "first_frame 10->10" in line and "[direct]" in line and "controls hid early in 1 trial" in line


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
