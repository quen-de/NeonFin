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
@pytest.mark.parametrize("route", ["movies", "series"])
def test_play_all_is_the_neon_tube_and_shuffle_a_round_tinted_button(open_page, color, profile, route):
    buttons = open_page(route, profile, "none").evaluate(GROUP)
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


OUTSIDE = """(bar) => { const b = document.querySelector(bar), r = b.getBoundingClientRect();
  return [...b.querySelectorAll('button, .MuiChip-root')].filter((e) => e.offsetParent)
    .map((e) => [e.innerText.trim(), e.getBoundingClientRect()])
    .filter(([, q]) => q.top < r.top - 0.5 || q.bottom > r.bottom + 0.5 || q.left < r.left - 0.5 || q.right > r.right + 0.5)
    .map(([t, q]) => [t, q.left, q.top, q.right, q.bottom]); }"""


@pytest.mark.parametrize("filtered", [False, True])
def test_on_a_narrow_desktop_the_capsule_holds_its_controls(open_page, filtered):
    # With a filter on, Jellyfin adds a Reset filters button to the row.
    page = open_page("movies", "desktop", "all", viewport=(1024, 768), variant="letter-b" if filtered else "")
    if filtered:
        page.locator(f"{RAIL} .MuiToggleButton-root >> text=B").first.click()
        page.wait_for_selector(f"{BAR2} .MuiButton-textPrimary")
        page.wait_for_timeout(500)
    g = page.evaluate(GEOMETRY, [BAR2, FIRST_HEADER_ITEM])
    assert g["height"] == 42 and g["overflow"] <= 0, g
    assert page.evaluate(OUTSIDE, BAR2) == []


TEXT_GROUP = """(bar) => [...document.querySelectorAll(bar + ' .MuiButtonGroup-text > .MuiButton-root')]
  .filter((b) => b.offsetParent).map((b) => { const cs = getComputedStyle(b), r = b.getBoundingClientRect();
    return { icon: b.querySelector('svg')?.dataset.testid, w: r.width, h: r.height, left: r.left, right: r.right,
             radii: ['TopLeft', 'TopRight', 'BottomRight', 'BottomLeft'].map((c) => parseFloat(cs[`border${c}Radius`])),
             border: cs.borderRightWidth, shadow: cs.boxShadow, bg: cs.backgroundColor }; })"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", ["movies", "series"])
def test_filter_sort_view_and_paging_are_round_tinted_buttons(open_page, color, profile, route):
    # Spec 6.8: everything in the row but Play All is a round tinted button.
    buttons = open_page(route, profile, "none").evaluate(TEXT_GROUP, BAR2)
    assert {"FilterAltIcon", "SortByAlphaIcon"} <= {b["icon"] for b in buttons}, buttons
    for b in buttons:
        r, g, bl, a = color(b["bg"])
        assert b["w"] == pytest.approx(b["h"], abs=0.5) and min(b["radii"]) >= b["h"] / 2 and b["border"] == "0px", b
        assert min(r, g, bl) == 255 and 0.04 <= a <= 0.12 and "inset" in b["shadow"], b
    gaps = [nxt["left"] - cur["right"] for cur, nxt in zip(buttons, buttons[1:])]
    assert all(gap >= 4 for gap in gaps), gaps


def test_a_round_button_brightens_on_hover(open_page, color):
    page = open_page("movies", "desktop", "none", variant="text-hover")
    button = page.locator(f"{BAR2} .MuiButtonGroup-text > .MuiButton-root >> visible=true").first
    rest = color(button.evaluate("(e) => getComputedStyle(e).backgroundColor"))[3]
    button.hover()
    page.wait_for_timeout(300)
    assert color(button.evaluate("(e) => getComputedStyle(e).backgroundColor"))[3] > rest
    page.mouse.move(0, 0)


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


@pytest.mark.parametrize("route", ["movies", "series"])
def test_shuffle_stays_round_when_the_library_hides_play_all(open_page, color, route):
    page = open_page(route, "desktop", "none", variant="no-play-all")
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


# MUI squares off grouped buttons from emotion styles it may inject after the skin at any time.
MUI_CORNERS_AFTER_THE_SKIN = """(rail) => {
  const group = document.querySelector(rail + ' .MuiToggleButtonGroup-root');
  const css = [...group.classList].find((c) => c.startsWith('css-'));
  const tag = document.createElement('style');
  tag.textContent = ['firstButton', 'middleButton', 'lastButton']
    .map((p) => '.' + css + ' .MuiToggleButtonGroup-' + p + ' { border-radius: 0; }').join('');
  document.head.append(tag);
}"""


@pytest.mark.parametrize("route", ["movies", "series"])
def test_a_to_z_letters_stay_round_whatever_order_mui_styles_load_in(open_page, route):
    page = open_page(route, "phone", "none", variant="mui-corners-last")
    page.evaluate(MUI_CORNERS_AFTER_THE_SKIN, RAIL)
    radii = page.evaluate(f"""() => [...document.querySelectorAll('{RAIL} .MuiToggleButton-root')].flatMap((b) => {{
      const cs = getComputedStyle(b);
      return [cs.borderTopLeftRadius, cs.borderTopRightRadius, cs.borderBottomRightRadius, cs.borderBottomLeftRadius]; }})""")
    assert radii and set(radii) == {"999px"}, sorted(set(radii))


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_picking_a_letter_lights_it_crimson_and_leaves_no_blue(open_page, color, profile):
    page = open_page("movies", profile, "none", variant="letter-b")
    page.locator(f"{RAIL} .MuiToggleButton-root >> text=B").first.click()
    page.wait_for_selector(f"{RAIL} .Mui-selected")
    page.wait_for_timeout(800)
    picked = page.evaluate(f"() => getComputedStyle(document.querySelector('{RAIL} .Mui-selected')).color")
    assert color(picked)[:3] == (255, 124, 145), picked
    assert checks.blue_hits(page) == {}


def test_reset_filters_answers_hover_without_blue(open_page):
    page = open_page("movies", "desktop", "none", variant="reset-hover")
    page.locator(f"{RAIL} .MuiToggleButton-root >> text=B").first.click()
    reset = page.locator(f"{BAR2} .MuiButton-textPrimary")
    reset.wait_for()
    reset.hover()
    page.wait_for_timeout(400)
    assert checks.blue_hits(page) == {}
    page.mouse.move(0, 0)
