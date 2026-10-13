"""Settings pages: working pages, close to Jellyfin's, with no blue left (spec 6.14)."""

import pytest

from harness import checks

pytestmark = pytest.mark.live

SETTINGS = ("prefs", "display", "playback", "subtitles", "homeprefs", "profile", "quickconnect", "select")


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", SETTINGS)
def test_settings_pages_carry_no_jellyfin_blue(open_page, route, profile):
    assert checks.blue_hits(open_page(route, profile, "all")) == {}


@pytest.mark.parametrize(("route", "selector"), [("playback", ".sectionTitle"), ("display", ".MuiTypography-h2")])
def test_settings_headings_are_semibold_interface_type(open_page, style, route, selector):
    s = style(open_page(route, "desktop", "all"), f".userPreferencesPage {selector}", "font-weight", "font-family", "text-transform")
    assert s["font-weight"] == "600" and s["font-family"].startswith("-apple-system") and s["text-transform"] == "none", s


def test_a_contained_settings_button_is_a_neon_tube(open_page, style, color):
    b = style(open_page("display", "desktop", "all"), ".userPreferencesPage .MuiButton-root.MuiButton-contained", "box-shadow", "background-color")
    assert b["box-shadow"].count("inset") == 2 and color(b["background-color"])[:3] == (255, 36, 72), b


def test_the_subtitle_slider_takes_the_accent(open_page, color):
    c = open_page("subtitles", "desktop", "all").evaluate("() => getComputedStyle(document.querySelector('input[type=range]')).accentColor")
    assert color(c)[:3] == (255, 36, 72), c


def test_settings_links_are_crimson_for_text(open_page, color):
    c = open_page("display", "desktop", "all").evaluate(
        "() => { const a = document.querySelector('.userPreferencesPage a.MuiLink-root'); return a && getComputedStyle(a).color; }"
    )
    if c is None:
        pytest.skip("no MUI link on the display settings page")
    r, g, b, _ = color(c)
    assert r > 240 and g > 100 and r - max(g, b) > 60, c
