import pytest

from harness import checks

pytestmark = pytest.mark.live

GROUP = """() => [...document.querySelectorAll('.MuiToolbar-root .MuiButtonGroup-contained > .MuiButton-contained')]
  .filter((b) => b.offsetParent).map((b) => { const cs = getComputedStyle(b), r = b.getBoundingClientRect();
    return { text: b.innerText.trim(), w: r.width, h: r.height, left: r.left, right: r.right,
             radius: parseFloat(cs.borderTopLeftRadius), shadow: cs.boxShadow, bg: cs.backgroundColor }; })"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", ["movies", "series"])
def test_no_jellyfin_blue_on_libraries(open_page, profile, route):
    assert checks.blue_hits(open_page(route, profile, "none")) == {}


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_no_jellyfin_blue_on_search(open_page, profile):
    # The search field opens focused.
    assert checks.blue_hits(open_page("search", profile, "none")) == {}


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_play_all_is_the_neon_tube_and_shuffle_a_round_tinted_button(open_page, color, profile):
    buttons = open_page("movies", profile, "none").evaluate(GROUP)
    assert len(buttons) >= 2, buttons
    play, rest = buttons[0], buttons[1:]
    assert play["shadow"].count("inset") == 2 and color(play["bg"])[:3] == (255, 36, 72), play
    assert play["radius"] >= play["h"] / 2, play
    for b in rest:
        r, g, bl, a = color(b["bg"])
        assert b["w"] == pytest.approx(b["h"], abs=0.5) and b["radius"] >= b["h"] / 2, b
        assert min(r, g, bl) == 255 and 0.04 <= a <= 0.12 and "inset" in b["shadow"], b
    assert all(nxt["left"] - cur["right"] >= 6 for cur, nxt in zip(buttons, buttons[1:])), buttons


def test_the_filter_dot_is_crimson(open_page, style, color):
    dot = style(open_page("movies", "desktop", "none"), ".MuiToolbar-root .MuiBadge-dot", "background-color")
    assert color(dot["background-color"])[:3] == (255, 36, 72)


def test_the_item_count_is_a_quiet_rimmed_label(open_page, style, color):
    # It sits on the toolbar capsule's glass: a rim, no fill of its own, grey text.
    chip = style(open_page("movies", "desktop", "none"), ".MuiToolbar-root .MuiChip-filled", "background-color", "color", "box-shadow")
    assert color(chip["background-color"])[3] == 0 and "inset" in chip["box-shadow"], chip
    assert color(chip["color"]) == pytest.approx((246, 243, 240, 0.62), abs=0.01), chip


BAR2 = checks.LIBRARY_BAR
FIRST_HEADER_ITEM = ".MuiAppBar-root > .MuiToolbar-root:first-child > *"
GEOMETRY = """([bar, first]) => { const b = document.querySelector(bar), r = b.getBoundingClientRect();
  return { left: r.left, height: r.height, bottom: r.bottom, first: document.querySelector(first).getBoundingClientRect().left,
           appbar: document.querySelector('.MuiAppBar-root').getBoundingClientRect().height,
           grid: document.querySelector('.itemsContainer').getBoundingClientRect().top,
           overflow: b.scrollWidth - b.clientWidth }; }"""
WHITE_POSTERS = (
    ".itemsContainer .cardScalable, .itemsContainer .cardImageContainer { background: #fff !important; }"
    " .itemsContainer .cardImageContainer > *, .itemsContainer .cardIndicators { visibility: hidden !important; }"
)


@pytest.mark.parametrize("route", ["movies", "series"])
def test_the_library_toolbar_is_one_glass_capsule_under_the_header(open_page, style, route):
    page = open_page(route, "desktop", "all")
    s = style(page, BAR2, "backdrop-filter", "border-top-left-radius")
    g = page.evaluate(GEOMETRY, [BAR2, FIRST_HEADER_ITEM])
    assert "blur(20px)" in s["backdrop-filter"] and float(s["border-top-left-radius"].removesuffix("px")) >= 21
    assert g["height"] == 42 and g["left"] == pytest.approx(g["first"], abs=1) and g["appbar"] == 96, g
    assert len(checks.glass_elements(page)) == 3


def test_on_a_narrow_desktop_the_capsule_holds_its_controls(open_page):
    g = open_page("movies", "desktop", "all", viewport=(1024, 768)).evaluate(GEOMETRY, [BAR2, FIRST_HEADER_ITEM])
    assert g["height"] == 42 and g["overflow"] <= 0, g


@pytest.mark.parametrize("route", ["movies", "series"])
def test_the_phone_library_toolbar_is_solid_and_leaves_the_grid_in_place(open_page, style, color, route):
    page = open_page(route, "phone", "all")
    s = style(page, BAR2, "background-color", "backdrop-filter")
    g = page.evaluate(GEOMETRY, [BAR2, FIRST_HEADER_ITEM])
    assert color(s["background-color"])[3] >= 0.9 and s["backdrop-filter"] == "none", s
    assert g["left"] == pytest.approx(g["first"], abs=1) and g["bottom"] <= g["grid"] + 0.5, g
    assert checks.glass_elements(page) == []


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_header_and_toolbar_read_over_white_posters(open_page, tmp_path, profile):
    page = open_page("movies", profile, "none", variant="white-posters")
    page.add_style_tag(content=WHITE_POSTERS)
    page.evaluate("scrollTo(0, 1600)")
    page.wait_for_timeout(500)
    assert checks.contrast_failures(page, "movies", tmp_path / "white.png") == []


RAIL = ".alphaPicker-fixed-right"


def test_shuffle_stays_round_when_the_library_hides_play_all(open_page, color):
    page = open_page("movies", "desktop", "none", variant="no-play-all")
    page.evaluate("() => document.querySelector('.MuiToolbar-root .MuiButtonGroup-contained > .MuiButton-contained:first-child').remove()")
    page.wait_for_timeout(200)
    buttons = page.evaluate(GROUP)
    assert len(buttons) == 1, buttons
    b = buttons[0]
    r, g, bl, a = color(b["bg"])
    assert b["w"] == pytest.approx(b["h"], abs=0.5) and min(r, g, bl) == 255 and b["shadow"].count("inset") == 1, b


@pytest.mark.parametrize("route", ["movies", "series"])
def test_the_a_to_z_rail_is_grey_on_a_solid_strip(open_page, style, color, route):
    page = open_page(route, "phone", "none")
    strip = style(page, f"{RAIL} .MuiPaper-root", "background-color", "border-top-left-radius")
    letter = style(page, f"{RAIL} .MuiToggleButton-root", "color")
    assert color(strip["background-color"])[3] >= 0.9 and float(strip["border-top-left-radius"].removesuffix("px")) >= 10, strip
    assert color(letter["color"]) == pytest.approx((246, 243, 240, 0.62), abs=0.01)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_picking_a_letter_lights_it_crimson_and_leaves_no_blue(open_page, color, profile):
    page = open_page("movies", profile, "none", variant="letter-b")
    page.locator(f"{RAIL} .MuiToggleButton-root >> text=B").first.click()
    page.wait_for_selector(f"{RAIL} .Mui-selected")
    page.wait_for_timeout(800)
    picked = page.evaluate(f"() => getComputedStyle(document.querySelector('{RAIL} .Mui-selected')).color")
    assert color(picked)[:3] == (255, 124, 145), picked
    assert checks.blue_hits(page) == {}
