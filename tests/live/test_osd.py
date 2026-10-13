import re

import pytest

from harness import checks

pytestmark = pytest.mark.live

INK = (5, 6, 10)
COLOURS = r"(?:rgba?|color)\([^()]*\)"
ICONS = """(sel) => [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length)
  .map((e) => [e.tagName.toLowerCase(), getComputedStyle(e).textShadow, getComputedStyle(e).filter])"""
WHITE_FRAME = ".videoPlayerContainer video { visibility: hidden !important; } .videoPlayerContainer { background: #fff !important; }"


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_controls_sit_on_ink_gradients_that_fade_by_opacity(osd, style, color, profile):
    page = osd(profile)
    # Jellyfin 12 keeps a hidden legacy header with the same classes; the MUI one shows.
    for sel in (".skinHeader.osdHeader.MuiBox-root", ".videoOsdBottom"):
        s = style(page, sel, "background-image", "transition-property")
        stops = [color(c) for c in re.findall(COLOURS, s["background-image"])]
        assert stops and stops[0][:3] == INK and stops[0][3] >= 0.75, (sel, s)
        assert s["transition-property"] == "opacity", (sel, s)
    assert checks.glass_elements(page) == []  # no glass over video


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_control_icons_have_a_soft_shadow(osd, profile):
    icons = osd(profile).evaluate(ICONS, ".videoOsdBottom .material-icons, .osdHeader .material-icons, .osdHeader svg")
    assert icons
    for tag, shadow, filt in icons:
        assert ("drop-shadow" in filt) if tag == "svg" else (shadow != "none"), (tag, shadow, filt)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_control_text_reads_over_a_white_frame(osd, tmp_path, profile):
    page = osd(profile, variant="white-frame")
    page.add_style_tag(content=WHITE_FRAME)
    page.wait_for_timeout(300)
    assert checks.contrast_failures(page, "osd", tmp_path / "osd.png") == []


def test_the_time_bubble_is_a_dark_pill(osd, style, color):
    page = osd("desktop", variant="bubble")
    box = page.locator(".osdPositionSlider").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_selector(".sliderBubble:not(.hide)")
    s = style(page, ".sliderBubble", "background-color", "border-top-left-radius")
    r, g, b, a = color(s["background-color"])
    assert a >= 0.95 and max(r, g, b) < 40 and (r, g, b) != (40, 40, 40), s
    assert float(s["border-top-left-radius"].removesuffix("px")) >= 8, s


def test_the_up_next_countdown_is_crimson(osd, color):
    page = osd("desktop")
    # Up Next shows near the end of an episode; its countdown is built the same way.
    c = page.evaluate("""() => { const e = document.createElement('div');
      e.className = 'upNextDialog-countdownText'; e.textContent = '10'; document.body.append(e);
      const c = getComputedStyle(e).color; e.remove(); return c; }""")
    r, g, b, _ = color(c)
    assert r - max(g, b) > 80, c
