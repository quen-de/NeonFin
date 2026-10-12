import pytest

from harness import checks

pytestmark = pytest.mark.live

PAPERS = {"actionsheet": ".actionSheet", "usermenu": "#app-user-menu .MuiMenu-paper", "select": "#menu-language .MuiPaper-root"}


@pytest.mark.parametrize("route", list(PAPERS))
def test_desktop_menus_are_glass(open_page, style, color, route):
    page = open_page(route, "desktop", "none")
    s = style(page, PAPERS[route], "backdrop-filter", "background-color", "border-top-left-radius", "box-shadow")
    # Dense enough for AA over a white page, thin enough to stay glass.
    assert "blur" in s["backdrop-filter"] and 0.4 <= color(s["background-color"])[3] <= 0.75, s
    assert s["border-top-left-radius"] == "14px" and "inset" in s["box-shadow"], s
    assert len(checks.glass_elements(page)) <= 3


@pytest.mark.parametrize("route", list(PAPERS))
def test_phone_menus_are_solid(open_page, style, color, route):
    page = open_page(route, "phone", "none")
    s = style(page, PAPERS[route], "backdrop-filter", "background-color", "border-top-left-radius")
    assert s["backdrop-filter"] == "none" and color(s["background-color"])[3] >= 0.95, s
    assert s["border-top-left-radius"] == "14px", s
    assert checks.glass_elements(page) == []


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("feature", [("prefers-reduced-transparency", "reduce"), ("prefers-contrast", "more")])
def test_menus_turn_solid_when_asked(open_page, style, color, feature, profile):
    page = open_page("actionsheet", profile, "none", media=(feature,))
    s = style(page, ".actionSheet", "backdrop-filter", "background-color")
    assert s["backdrop-filter"] == "none" and color(s["background-color"])[3] == 1, s


def test_menus_over_video_turn_solid_when_asked(open_page, style, color):
    page = _osd_menu(open_page, "desktop", ".btnVideoOsdSettings", "settings", media=(("prefers-contrast", "more"),))
    assert color(style(page, ".actionSheet", "background-color")["background-color"])[3] == 1


def test_the_user_menu_reads_over_a_white_hero(open_page, tmp_path):
    # MUI menus open with nothing dimming the page behind them.
    page = open_page("usermenu", "desktop", "all", variant="white-hero")
    page.add_style_tag(
        content="#slides-container .backdrop-container { background: #fff !important; }"
        " #slides-container .backdrop-container > * { visibility: hidden !important; }"
    )
    page.wait_for_timeout(300)
    labels = page.evaluate(
        "(s) => [...document.querySelectorAll(s)].filter((e) => e.offsetParent).length", checks.TEXT_TARGETS["usermenu"][0]
    )
    assert labels >= 3
    assert checks.contrast_failures(page, "usermenu", tmp_path / "menu.png") == []


def test_a_focused_settings_field_keeps_its_label_off_blue(open_page, color):
    page = open_page("select", "desktop", "none")
    label = page.evaluate("() => getComputedStyle(document.querySelector('#display-settings-language-label')).color")
    r, g, b, _ = color(label)
    assert not (b > r + 60), label


def test_the_selected_choice_in_a_select_menu_is_crimson(open_page, color):
    page = open_page("select", "desktop", "none")
    bg = page.evaluate("() => getComputedStyle(document.querySelector('#menu-language .MuiMenuItem-root.Mui-selected')).backgroundColor")
    r, g, b, a = color(bg)
    assert r > 2 * max(g, b) and a > 0, bg


def _osd_menu(open_page, profile, button, variant, media=()):
    page = open_page("osd", profile, "none", variant=variant, media=media)
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
    # Jellyfin draws a check on every choice and hides all but the current one.
    icons = page.evaluate(
        """() => [...document.querySelectorAll('.actionSheet .actionsheetMenuItemIcon')]
      .filter((i) => i.offsetParent && getComputedStyle(i).visibility !== 'hidden')
      .map((i) => [i.classList.contains('check'), getComputedStyle(i).color])"""
    )
    crimson = [is_check for is_check, c in icons if (lambda r, g, b, a: r > 2 * max(g, b))(*color(c))]
    assert crimson and all(crimson), icons


THUMB = """() => { const s = document.querySelector('.osdPositionSlider');
  const lower = s.parentElement.querySelector('.mdl-slider-background-lower');
  const r = s.getBoundingClientRect(), l = lower.getBoundingClientRect();
  return [l.right, r.top + r.height / 2]; }"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_player_bars_are_crimson_with_a_white_handle(osd, style, color, tmp_path, profile):
    from PIL import Image

    page = osd(profile)
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


ITEMS = {
    "actionsheet": ".actionSheet .actionSheetMenuItem",
    "usermenu": "#app-user-menu .MuiMenuItem-root",
    "select": "#menu-language .MuiMenuItem-root",
}
HEIGHTS = "(s) => [...document.querySelectorAll(s)].filter((e) => e.offsetParent).map((e) => e.getBoundingClientRect().height)"


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", list(ITEMS))
def test_menu_items_are_40px_on_desktop_and_finger_sized_on_phones(open_page, route, profile):
    heights = open_page(route, profile, "none").evaluate(HEIGHTS, ITEMS[route])
    fits = (lambda h: abs(h - 40) < 0.5) if profile == "desktop" else (lambda h: h >= 44)
    assert heights and all(map(fits, heights)), heights


SHEET = """() => { const s = document.querySelector('.actionSheet'); const r = s.getBoundingClientRect();
  const cs = getComputedStyle(s);
  return {rect: [r.left, r.top, r.right, r.bottom], vw: innerWidth, vh: innerHeight, origin: cs.transformOrigin,
    radii: [cs.borderTopLeftRadius, cs.borderTopRightRadius, cs.borderBottomRightRadius, cs.borderBottomLeftRadius]}; }"""


@pytest.mark.parametrize("over", ["page", "video"])
def test_phone_action_sheets_rise_from_the_bottom_edge(open_page, over):
    if over == "page":
        page = open_page("actionsheet", "phone", "none")
    else:
        # Its own page: a sheet along the bottom covers the button that opens it.
        page = _osd_menu(open_page, "phone", ".btnVideoOsdSettings", "rise")
    page.wait_for_timeout(300)  # the 140 ms scale-in
    s = page.evaluate(SHEET)
    left, top, right, bottom = s["rect"]
    assert left == 0 and right == s["vw"] and abs(bottom - s["vh"]) < 1, s
    assert top >= 0.16 * s["vh"] - 1, s  # never taller than 84% of the screen
    assert s["radii"] == ["14px", "14px", "0px", "0px"], s
    origin_y = float(s["origin"].split()[1].removesuffix("px"))
    assert abs(origin_y - (bottom - top)) < 1, s  # it grows up from the edge
