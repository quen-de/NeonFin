import pytest

pytestmark = pytest.mark.live

NAV = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root"
ACTIONS = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiBox-root:not(:last-child)"


@pytest.mark.parametrize("feature", [("prefers-reduced-transparency", "reduce"), ("prefers-contrast", "more")])
def test_glass_turns_solid_when_asked(open_page, style, color, feature):
    page = open_page("home", "desktop", "none", media=(feature,))
    for sel in (NAV, ACTIONS):
        s = style(page, sel, "backdrop-filter", "background-color")
        assert s["backdrop-filter"] == "none"
        assert color(s["background-color"]) == (9, 11, 18, 1.0)


def test_forced_colors_drop_the_glass(open_page, style):
    page = open_page("home", "desktop", "none", media=(("forced-colors", "active"),))
    for sel in (NAV, ACTIONS):
        assert style(page, sel, "backdrop-filter")["backdrop-filter"] == "none"


def test_reduced_motion_stills_the_cards(open_page):
    page = open_page("home", "desktop", "none", media=(("prefers-reduced-motion", "reduce"),))
    card = page.locator(".homeSectionsContainer .emby-scroller .card >> visible=true").first
    card.hover()
    page.wait_for_timeout(300)
    got = card.evaluate(
        "(c) => { const s = getComputedStyle(c.querySelector('.cardScalable')); return [s.transitionDuration, s.transform]; }"
    )
    assert got == ["0s", "none"]
    page.mouse.move(0, 0)
