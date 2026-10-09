import pytest

from harness import checks

pytestmark = pytest.mark.live

NAV = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root"
ACTIONS = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiBox-root:not(:last-child)"
BLUR_INSIDE_SLIDES = """() => [...document.querySelectorAll('#slides-container *')].filter((e) => {
  const v = getComputedStyle(e).backdropFilter; return v && v !== 'none'; }).length"""


@pytest.mark.parametrize("profile, budget", [("desktop", 2), ("phone", 0)])
def test_home_with_every_plugin_keeps_the_glass_budget(open_page, profile, budget):
    page = open_page("home", profile, "all")
    assert page.evaluate(BLUR_INSIDE_SLIDES) == 0
    assert len(checks.glass_elements(page)) == budget


def test_media_bar_play_is_a_neon_tube_and_the_active_dot_is_crimson(open_page, style, color):
    page = open_page("home", "desktop", "all")
    play = style(page, "#slides-container .slide.active .play-button", "box-shadow", "background-color")
    assert play["box-shadow"].count("inset") == 2 and color(play["background-color"])[:3] == (255, 36, 72)
    dot = style(page, "#slides-container .dot.active", "background-color")
    assert color(dot["background-color"]) == (255, 36, 72, 1.0)


def test_without_media_bar_home_starts_below_the_capsules(open_page):
    page = open_page("home", "desktop", "without:media-bar")
    top = page.evaluate("""() => document.querySelector(
      '.homeSectionsContainer > .verticalSection:not(.hide):not(#hssLoadingIndicator)').getBoundingClientRect().top""")
    assert top >= 48


def test_enhanced_buttons_sit_inside_the_actions_capsule(open_page, style):
    page = open_page("home", "desktop", "all")
    cap = style(page, ACTIONS)["rect"]
    btn = style(page, ".je-header-buttons-tray .headerButton", "width", "border-top-left-radius")
    assert btn["width"] == "34px" and btn["border-top-left-radius"] == "999px"
    x, y, w, h = btn["rect"]
    assert cap[0] <= x and x + w <= cap[0] + cap[2] and cap[1] <= y and y + h <= cap[1] + cap[3]


@pytest.mark.parametrize("plugin_state", ["all", "without:jellyfin-enhanced"])
def test_actions_stay_one_right_aligned_capsule(open_page, style, plugin_state):
    page = open_page("home", "desktop", plugin_state)
    nav, act = style(page, NAV)["rect"], style(page, ACTIONS)["rect"]
    assert nav[2] < 720 and act[0] > nav[0] + nav[2] and act[0] + act[2] > 1440 - 120


def test_language_flags_are_rounded(open_page, style):
    f = style(open_page("home", "desktop", "all"), ".je-tag-host .language-flag", "border-top-left-radius")
    if f is None:
        pytest.skip("no language flags on this server's home")
    assert f["border-top-left-radius"] == "3px"
