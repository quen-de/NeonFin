import pytest

from harness import checks

pytestmark = pytest.mark.live

FIELD = "#searchPage .searchfields-txtSearch"
GEOM = """() => { const i = document.querySelector('#searchPage .searchfields-txtSearch'), r = i.getBoundingClientRect();
  const c = document.querySelector('.searchfields-icon').getBoundingClientRect();
  const s = document.querySelector('#jellyseerr-search-icon');
  return { input: [r.left, r.top, r.right, r.bottom], icon: [c.left, c.top, c.right, c.bottom], vw: innerWidth,
           text_end: r.right - parseFloat(getComputedStyle(i).paddingRight), seerr: s && s.getBoundingClientRect().left }; }"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_the_field_is_a_large_tinted_pill_with_the_magnifier_inside(open_page, style, color, profile):
    page = open_page("search", profile, "none")
    s = style(page, FIELD, "height", "border-top-left-radius", "background-color", "border-top-width")
    r, g, b, a = color(s["background-color"])
    assert s["height"] == "48px" and float(s["border-top-left-radius"].removesuffix("px")) >= 24, s
    assert min(r, g, b) == 255 and 0.04 <= a <= 0.1 and s["border-top-width"] == "1px", s
    geo = page.evaluate(GEOM)
    (il, it, ir, ib), (cl, ct, cr, cb) = geo["input"], geo["icon"]
    assert il <= cl and cr <= ir and abs((ct + cb) / 2 - (it + ib) / 2) <= 2, geo


def test_on_a_phone_the_field_runs_edge_to_edge_inside_the_gutter(open_page):
    geo = open_page("search", "phone", "none").evaluate(GEOM)
    assert geo["input"][0] == pytest.approx(16, abs=1) and geo["input"][2] == pytest.approx(geo["vw"] - 16, abs=1), geo


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_typed_text_stops_before_the_seerr_icon(open_page, profile):
    geo = open_page("search", profile, "all").evaluate(GEOM)
    if geo["seerr"] is None:
        pytest.skip("Jellyfin Enhanced's Seerr search is not active on this server")
    assert geo["text_end"] <= geo["seerr"], geo


def test_the_focused_field_wears_a_crimson_ring(open_page, style, color):
    page = open_page("search", "desktop", "none", variant="focus")
    page.focus(FIELD)
    page.wait_for_timeout(300)
    s = style(page, FIELD, "border-top-color", "box-shadow")
    r, g, b, _ = color(s["border-top-color"])
    assert r > 2 * max(g, b) and "3px" in s["box-shadow"], s
    assert checks.blue_hits(page) == {}


def test_no_results_is_one_quiet_centred_line(open_page, style, color):
    s = style(open_page("noresults", "desktop", "none"), "#searchPage .noItemsMessage", "color", "text-align")
    assert color(s["color"]) == pytest.approx((246, 243, 240, 0.62), abs=0.01) and s["text-align"] == "center", s


def test_results_are_rows_under_lit_signs(open_page, style):
    # Guard: milestone 1's row titles already apply here.
    s = style(open_page("search", "desktop", "none"), "#searchPage .sectionTitle", "font-family")
    assert s["font-family"].startswith('"NeonFin Sign"')
