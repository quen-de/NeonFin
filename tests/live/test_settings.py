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
    b = style(
        open_page("display", "desktop", "all"), ".userPreferencesPage .MuiButton-root.MuiButton-contained", "box-shadow", "background-color"
    )
    assert b["box-shadow"].count("inset") == 2 and color(b["background-color"])[:3] == (255, 36, 72), b


# MUI marks a disabled button with a class and the attribute, an error one with its variant
# class; the clones keep the rest of the real button's classes.
CLONE = """(extra) => { const b = document.querySelector('.userPreferencesPage .MuiButton-root.MuiButton-contained');
  const c = b.cloneNode(true); c.classList.add(...extra); if (extra.includes('Mui-disabled')) c.disabled = true;
  b.after(c); const cs = getComputedStyle(c);
  return { shadow: cs.boxShadow, glow: cs.textShadow, color: cs.color, bg: cs.backgroundColor }; }"""


def test_a_disabled_settings_button_is_a_dim_pill_not_a_tube(open_page, color):
    got = open_page("display", "desktop", "all", variant="disabled").evaluate(CLONE, ["Mui-disabled"])
    assert got["glow"] == "none" and got["shadow"].count("inset") == 1 and "18px" not in got["shadow"], got
    assert color(got["color"]) == pytest.approx((246, 243, 240, 0.62), abs=0.01), got


def test_an_error_settings_button_takes_the_error_colour_not_the_tube(open_page, color):
    page = open_page("display", "desktop", "all", variant="error")
    got = page.evaluate(CLONE, ["MuiButton-containedError"])
    error = page.evaluate("""() => { const e = document.createElement('i'); e.style.color = 'var(--nf-error)';
      document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; }""")
    assert got["glow"] == "none" and "18px" not in got["shadow"], got
    # The error hue, deepened until its label passes AA.
    bg, err = color(got["bg"]), color(error)
    assert bg[3] == 1 and max(range(3), key=lambda i: bg[i]) == max(range(3), key=lambda i: err[i]), (got, error)
    assert checks.contrast_ratio(color(got["color"]), bg) >= 4.5, got


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
