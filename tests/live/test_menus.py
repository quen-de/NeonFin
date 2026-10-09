import pytest

from harness import checks

pytestmark = pytest.mark.live

PAPERS = {"actionsheet": ".actionSheet", "usermenu": "#app-user-menu .MuiMenu-paper", "select": "#menu-language .MuiPaper-root"}


@pytest.mark.parametrize("route", list(PAPERS))
def test_desktop_menus_are_glass(open_page, style, color, route):
    page = open_page(route, "desktop", "none")
    s = style(page, PAPERS[route], "backdrop-filter", "background-color", "border-top-left-radius", "box-shadow")
    assert "blur" in s["backdrop-filter"] and color(s["background-color"])[3] <= 0.6, s
    assert s["border-top-left-radius"] == "14px" and "inset" in s["box-shadow"], s
    assert len(checks.glass_elements(page)) <= 3


@pytest.mark.parametrize("route", list(PAPERS))
def test_phone_menus_are_solid(open_page, style, color, route):
    page = open_page(route, "phone", "none")
    s = style(page, PAPERS[route], "backdrop-filter", "background-color", "border-top-left-radius")
    assert s["backdrop-filter"] == "none" and color(s["background-color"])[3] >= 0.95, s
    assert s["border-top-left-radius"] == "14px", s
    assert checks.glass_elements(page) == []


@pytest.mark.parametrize("feature", [("prefers-reduced-transparency", "reduce"), ("prefers-contrast", "more")])
def test_menus_turn_solid_when_asked(open_page, style, color, feature):
    page = open_page("actionsheet", "desktop", "none", media=(feature,))
    s = style(page, ".actionSheet", "backdrop-filter", "background-color")
    assert s["backdrop-filter"] == "none" and color(s["background-color"])[3] == 1, s


def test_the_selected_choice_in_a_select_menu_is_crimson(open_page, color):
    page = open_page("select", "desktop", "none")
    bg = page.evaluate("() => getComputedStyle(document.querySelector('#menu-language .MuiMenuItem-root.Mui-selected')).backgroundColor")
    r, g, b, a = color(bg)
    assert r > 2 * max(g, b) and a > 0, bg


def _osd_menu(open_page, profile, button, variant):
    page = open_page("osd", profile, "none", variant=variant)
    page.locator(button).first.click()
    page.wait_for_selector(".actionSheet", state="visible")
    page.wait_for_timeout(400)
    return page


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_menus_over_video_are_solid_smoke(open_page, style, color, profile):
    page = _osd_menu(open_page, profile, ".btnVideoOsdSettings", "settings")
    s = style(page, ".actionSheet", "backdrop-filter", "background-color", "border-top-left-radius")
    r, g, b, a = color(s["background-color"])
    assert s["backdrop-filter"] == "none" and a >= 0.95 and b > r, s  # a cool smoke, not Jellyfin's gray
    assert s["border-top-left-radius"] == "14px", s


def test_only_the_current_choice_is_marked_crimson(open_page, color):
    page = _osd_menu(open_page, "desktop", ".btnSubtitles", "subtitles")
    icons = page.evaluate(
        """() => [...document.querySelectorAll('.actionSheet .actionsheetMenuItemIcon')].filter((i) => i.offsetParent)
      .map((i) => [i.classList.contains('check') && getComputedStyle(i).visibility !== 'hidden', getComputedStyle(i).color])"""
    )
    checks_ = [c for on, c in icons if on]
    assert checks_, icons
    for c in checks_:
        r, g, b, _ = color(c)
        assert r > 2 * max(g, b), icons


THUMB = """() => { const s = document.querySelector('.osdPositionSlider');
  const lower = s.parentElement.querySelector('.mdl-slider-background-lower');
  const r = s.getBoundingClientRect(), l = lower.getBoundingClientRect();
  return [l.right, r.top + r.height / 2]; }"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_player_bars_are_crimson_with_a_white_handle(open_page, style, color, tmp_path, profile):
    from PIL import Image

    page = open_page("osd", profile, "none")
    assert checks.blue_hits(page) == {}
    lower = style(page, ".videoOsdBottom .mdl-slider-background-lower", "background-color")
    assert color(lower["background-color"])[:3] == (255, 36, 72)
    x, y = page.evaluate(THUMB)
    page.mouse.move(x, y)
    page.wait_for_timeout(400)
    page.screenshot(path=str(tmp_path / "thumb.png"), clip={"x": x - 3, "y": y - 3, "width": 6, "height": 6}, animations="disabled")
    im = Image.open(tmp_path / "thumb.png").convert("RGB")
    px = list(getattr(im, "get_flattened_data", im.getdata)())  # getdata is deprecated from Pillow 12
    assert max(min(p) for p in px) >= 235, px  # the handle's middle is white
    assert not any(b > r + 60 and b > 150 for r, _, b in px), px  # and nothing there is Jellyfin blue
