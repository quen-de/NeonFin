import pytest

from harness import checks

pytestmark = pytest.mark.live

NAV = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root"
ACTIONS = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiBox-root:not(:last-child)"


def test_desktop_header_is_two_glass_capsules(open_page, style, color):
    page = open_page("home", "desktop", "none")
    bar = style(page, ".MuiAppBar-root", "background-color", "box-shadow")
    assert color(bar["background-color"])[3] == 0 and bar["box-shadow"] == "none"
    for sel in (NAV, ACTIONS):
        s = style(page, sel, "backdrop-filter", "border-top-left-radius", "height")
        assert "blur(20px)" in s["backdrop-filter"] and "saturate" in s["backdrop-filter"]
        assert s["height"] == "42px" and s["border-top-left-radius"] == "999px"
    nav, act = style(page, NAV)["rect"], style(page, ACTIONS)["rect"]
    assert nav[2] < 720  # content width, not stretched across the bar
    assert act[0] > nav[0] + nav[2]  # two capsules side by side
    assert act[0] + act[2] > 1440 - 120  # actions on the right; only the avatar sits further right


def test_selected_section_is_a_crimson_pill_without_glow(open_page, style, color):
    page = open_page("movies", "desktop", "none")
    s = style(page, f"{NAV} > .MuiButton-textPrimary", "background-color", "box-shadow", "color")
    assert s is not None, "no selected section on the library page"
    r, g, b, a = color(s["background-color"])
    assert (r, g, b) == (255, 36, 72) and a == pytest.approx(0.2, abs=0.01)
    assert s["box-shadow"].count("inset") == 1 and "0px 0px 0px 1px" in s["box-shadow"]
    assert color(s["color"])[:3] == (255, 255, 255)


def test_avatar_is_oxblood(open_page, style, color):
    page = open_page("home", "desktop", "none")
    s = style(page, ".MuiAppBar-root .MuiAvatar-root", "background-color")
    assert color(s["background-color"]) == (74, 10, 21, 1.0)  # oxblood, derived from the accent


@pytest.mark.parametrize("plugin_state", ["all", "none"])
def test_capsules_never_overlap_on_a_narrow_desktop(open_page, style, plugin_state):
    # Many sections, with and without the plugins' buttons: the navigation must shrink and
    # scroll, never push.
    page = open_page("home", "desktop", plugin_state, viewport=(1024, 768), variant="many-sections")
    page.evaluate(
        """(sel) => { const nav = document.querySelector(sel), pill = nav.querySelector('.MuiButton-root');
      for (let i = 0; i < 12; i++) nav.append(pill.cloneNode(true)); }""",
        NAV,
    )
    page.wait_for_timeout(100)
    nav, act = style(page, NAV)["rect"], style(page, ACTIONS)["rect"]
    assert abs(nav[1] - act[1]) < 4, (nav, act)  # one row: the actions never wrap below
    assert nav[0] + nav[2] <= act[0]
    assert page.evaluate("(sel) => { const n = document.querySelector(sel); return n.scrollWidth > n.clientWidth; }", NAV)


def test_phone_header_is_solid(open_page, style, color):
    page = open_page("home", "phone", "none")
    s = style(page, ACTIONS, "backdrop-filter", "background-color")
    assert s["backdrop-filter"] == "none" and color(s["background-color"])[3] >= 0.9


def test_phone_drawer_is_solid_with_a_crimson_current_section(open_page, style, color):
    # Jellyfin marks the drawer item only where its link matches the location, as on home.
    page = open_page("home", "phone", "none", variant="drawer")
    page.locator(".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiIconButton-root").first.click()
    page.wait_for_selector(".MuiDrawer-paper", state="visible")
    assert color(style(page, ".MuiDrawer-paper", "background-color")["background-color"]) == (9, 11, 18, 1.0)
    sel = style(page, ".MuiDrawer-paper .Mui-selected", "background-color")
    assert sel is not None and color(sel["background-color"])[:3] == (255, 36, 72)
    page.keyboard.press("Escape")


def test_phone_header_stays_solid_at_tablet_width(open_page, style):
    page = open_page("home", "phone", "none", viewport=(1024, 768))
    assert style(page, NAV, "backdrop-filter")["backdrop-filter"] == "none"
    assert checks.glass_elements(page) == []
