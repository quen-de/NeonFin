import pytest

from harness import checks

pytestmark = pytest.mark.live

NEON = (255, 36, 72)


def crimson(c):
    r, g, b, a = c
    return a > 0 and r > 2 * max(g, b)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", ["login", "dialog"])
def test_no_blue_on_sign_in_or_dialogs(open_page, route, profile):
    assert checks.blue_hits(open_page(route, profile, "none")) == {}


@pytest.mark.parametrize("route", ["login", "dialog"])
def test_the_primary_button_is_a_neon_tube(open_page, style, color, route):
    page = open_page(route, "desktop", "none")
    s = style(page, ".raised.button-submit", "background-color", "box-shadow", "border-top-left-radius", "color")
    bg = color(s["background-color"])
    assert crimson(bg) and bg[3] < 0.3, s
    assert "inset" in s["box-shadow"] and "255, 36, 72" in s["box-shadow"], s
    assert s["border-top-left-radius"] == "999px" and color(s["color"])[:3] == (255, 255, 255), s


def test_other_raised_buttons_are_tinted_pills(open_page, style, color):
    s = style(open_page("picker", "desktop", "none"), ".btnManual", "background-color", "box-shadow", "border-top-left-radius")
    r, g, b, a = color(s["background-color"])
    assert (r, g, b) == (255, 255, 255) and 0.05 <= a <= 0.1, s
    assert "inset" in s["box-shadow"] and s["border-top-left-radius"] == "999px", s


@pytest.mark.parametrize("how", ["focus", "hover"])
@pytest.mark.parametrize("target", [".raised.button-submit", ".btnForgotPassword"])
def test_buttons_stay_off_blue_when_focused_or_hovered(open_page, target, how):
    page = open_page("login", "desktop", "none", variant=f"{how} {target}")
    button = page.locator(target).first
    button.focus() if how == "focus" else button.hover()
    page.wait_for_timeout(300)
    assert checks.blue_hits(page) == {}


def test_a_checked_box_is_crimson_with_a_white_tick(open_page, style, color):
    page = open_page("login", "desktop", "none")
    box = style(page, ".chkRememberLogin + span + .checkboxOutline", "background-color", "border-top-color")
    tick = style(page, ".chkRememberLogin + span + .checkboxOutline > .checkboxIcon-checked", "color")
    assert color(box["background-color"])[:3] == NEON and color(box["border-top-color"])[:3] == NEON, box
    assert color(tick["color"])[:3] == (255, 255, 255), tick


def test_a_focused_empty_box_is_edged_in_crimson(open_page, style, color):
    page = open_page("login", "desktop", "none", variant="unchecked")
    page.focus(".chkRememberLogin")
    page.keyboard.press("Space")
    assert page.eval_on_selector(".chkRememberLogin", "(e) => !e.checked")
    s = style(page, ".chkRememberLogin + span + .checkboxOutline", "border-top-color")
    assert crimson(color(s["border-top-color"])), s


def test_a_ticked_box_shows_keyboard_focus(open_page, style):
    # "Remember me" starts ticked; the input itself is invisible, so its box carries the ring.
    page = open_page("login", "desktop", "none", variant="tab-to-box")
    page.focus("#txtManualPassword")
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.matches('.chkRememberLogin:checked:focus-visible')")
    ring = style(page, ".chkRememberLogin + span + .checkboxOutline", "box-shadow")["box-shadow"]
    assert "255, 36, 72" in ring, ring
