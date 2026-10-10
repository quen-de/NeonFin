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


def test_header_reads_over_a_white_hero(open_page, tmp_path):
    # The worst slide the hero can show: the capsules' text must still pass AA over it.
    page = open_page("home", "desktop", "all", variant="white-hero")
    page.add_style_tag(
        content="#slides-container .backdrop-container { background: #fff !important; }"
        " #slides-container .backdrop-container > * { visibility: hidden !important; }"
    )
    page.wait_for_timeout(200)
    reach = page.evaluate(
        """() => { const b = document.querySelector('#slides-container .slide.active .backdrop-container');
      return [getComputedStyle(b).backgroundColor, Math.round(b.getBoundingClientRect().top)]; }"""
    )
    assert reach == ["rgb(255, 255, 255)", 0]
    assert page.locator(f"{NAV} > .MuiButton-root >> visible=true").count() > 0
    fails = checks.contrast_failures(page, "home", tmp_path / "hero.png")
    assert [f for f in fails if "MuiButton" in f["label"]] == []


# Media Bar shows the plot from about 1100px wide; 1280 is the narrowest common desktop with it.
@pytest.mark.parametrize("profile, viewport", [("desktop", None), ("desktop", (1280, 800)), ("phone", None)])
def test_hero_text_reads_over_a_white_slide(open_page, tmp_path, profile, viewport):
    # The plot and the details line sit on the artwork itself, so they too must pass AA over
    # the brightest slide the hero can show.
    page = open_page("home", profile, "all", viewport=viewport, variant="white-hero")
    page.add_style_tag(
        content="#slides-container .backdrop-container { background: #fff !important; }"
        " #slides-container .backdrop-container > * { visibility: hidden !important; }"
    )
    page.wait_for_timeout(200)
    assert page.locator("#slides-container .slide.active .plot >> visible=true").count() == 1
    assert checks.contrast_failures(page, "home", tmp_path / "hero.png") == []


def test_a_long_details_line_keeps_to_the_dimmed_column(open_page):
    # Only the column the plot keeps to is dimmed for text. Two long genres on a 1280px desktop
    # used to carry the details line past it, over undimmed artwork.
    page = open_page("home", "desktop", "all", viewport=(1280, 800), variant="long-details")
    edges = page.evaluate("""() => {
      const slide = document.querySelector('#slides-container .slide.active');
      const genre = document.createElement('span');
      genre.className = 'spec-item spec-genre';
      genre.textContent = 'Science Fiction · Adventure · Animation';
      slide.querySelector('.spec-line').append(genre);
      const right = (s) => slide.querySelector(s).getBoundingClientRect().right;
      return [right('.spec-line'), right('.plot')]; }""")
    assert edges[0] <= edges[1] + 1, edges


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
    assert open_page("home", "desktop", plugin_state).locator(ACTIONS).count() == 1
    page = open_page("home", "desktop", plugin_state)
    nav, act = style(page, NAV)["rect"], style(page, ACTIONS)["rect"]
    assert nav[2] < 720 and act[0] > nav[0] + nav[2] and act[0] + act[2] > 1440 - 120


def test_language_flags_are_rounded(open_page, style):
    f = style(open_page("home", "desktop", "all"), ".je-tag-host .language-flag", "border-top-left-radius")
    if f is None:
        pytest.skip("no language flags on this server's home")
    assert f["border-top-left-radius"] == "3px"


def test_enhanced_tray_buttons_brighten_on_hover(open_page, color):
    page = open_page("home", "desktop", "all", variant="hover")
    button = page.locator(".je-header-buttons-tray .headerButton >> visible=true").first
    button.hover()
    page.wait_for_timeout(300)
    assert color(button.evaluate("(b) => getComputedStyle(b).color"))[3] > 0.9
    page.mouse.move(0, 0)


def test_phone_hero_keeps_its_top_undimmed(open_page):
    # Phones draw the header solid, so nothing needs dimming under it.
    page = open_page("home", "phone", "all")
    overlay = "getComputedStyle(document.querySelector('#slides-container .slide.active .gradient-overlay')).backgroundImage"
    desktop = open_page("home", "desktop", "all").evaluate(overlay)
    phone = page.evaluate(overlay)
    # The left and bottom fades only; desktop adds the top fade under its glass capsules.
    assert phone.count("linear-gradient(") == 2 and desktop.count("linear-gradient(") == 3


@pytest.mark.parametrize("viewport", [None, (1280, 800)])
def test_the_plot_keeps_to_the_dimmed_column(open_page, viewport):
    # At most three lines, ending before the left fade starts to clear (40% of the width).
    page = open_page("home", "desktop", "all", viewport=viewport)
    right, width, lines = page.evaluate(
        """() => { const p = document.querySelector('#slides-container .slide.active .plot'), r = p.getBoundingClientRect();
      return [r.right, innerWidth, p.clientHeight / parseFloat(getComputedStyle(p).lineHeight)]; }"""
    )
    assert 1.99 <= lines <= 3.01 and right <= 0.4 * width, (right, width, lines)


def _hero_light(page, tmp_path, x_frac):
    """Mean brightness of the white slide beside the plot, text hidden: how much artwork shows."""
    from PIL import Image

    box = page.evaluate(
        "() => { const b = document.querySelector('#slides-container .slide.active .plot').getBoundingClientRect();"
        " return [b.left, b.top, b.width, b.height]; }"
    )
    x, y = (box[0] + box[2] * x_frac) if x_frac <= 1 else x_frac, box[1] + box[3] / 2
    page.screenshot(
        path=str(tmp_path / "light.png"), style="#slides-container .slide.active .plot-container { visibility: hidden !important; }"
    )
    dpr = page.evaluate("devicePixelRatio")
    im = (
        Image.open(tmp_path / "light.png")
        .convert("L")
        .crop((round((x - 3) * dpr), round((y - 3) * dpr), round((x + 3) * dpr), round((y + 3) * dpr)))
    )
    px = list(getattr(im, "get_flattened_data", im.getdata)())
    return sum(px) / len(px)


def test_the_desktop_hero_shows_more_of_the_artwork(open_page, tmp_path):
    page = open_page("home", "desktop", "all", variant="white-hero")
    page.add_style_tag(
        content="#slides-container .backdrop-container { background: #fff !important; }"
        " #slides-container .backdrop-container > * { visibility: hidden !important; }"
    )
    page.wait_for_timeout(200)
    assert _hero_light(page, tmp_path, 0.85) >= 85  # under the end of the plot
    assert _hero_light(page, tmp_path, 720) >= 170  # mid-screen, beside the text column


def test_the_phone_hero_panel_lets_the_artwork_through(open_page, style, color):
    page = open_page("home", "phone", "all")
    panel = style(page, "#slides-container .slide.active .slide-content", "background-color")
    assert color(panel["background-color"])[3] <= 0.66


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_hero_text_is_primary_white(open_page, style, color, profile):
    page = open_page("home", profile, "all")
    for sel in ("#slides-container .slide.active .plot", "#slides-container .slide.active .spec-line"):
        assert color(style(page, sel, "color")["color"])[3] >= 0.9, sel


def seerr_card(page):
    cards = page.locator(".jellyseerr-card >> visible=true")
    if not cards.count():
        pytest.skip("no Seerr results on this server for the search term")
    return cards.first


def test_seerr_request_is_a_neon_tube(open_page, color):
    page = open_page("search", "desktop", "all", variant="seerr-hover")
    card = seerr_card(page)
    card.scroll_into_view_if_needed()
    card.hover()
    page.wait_for_timeout(500)
    button = card.locator(".jellyseerr-request-button.jellyseerr-button-request")
    if not button.count():
        pytest.skip("the first Seerr result offers no request")
    bg, shadow, radius = button.first.evaluate(
        "(e) => { const cs = getComputedStyle(e); return [cs.backgroundColor, cs.boxShadow, cs.borderTopLeftRadius]; }"
    )
    assert color(bg)[:3] == (255, 36, 72) and shadow.count("inset") == 2 and float(radius.removesuffix("px")) >= 15, (bg, shadow, radius)
    page.mouse.move(0, 0)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_seerr_media_badges_are_quiet_dark_chips(open_page, color, profile):
    page = open_page("search", profile, "all")
    seerr_card(page)
    for bg in page.evaluate(
        "() => [...document.querySelectorAll('.jellyseerr-card .jellyseerr-media-badge')].slice(0, 8)"
        ".map((b) => getComputedStyle(b).backgroundColor)"
    ):
        r, g, b, a = color(bg)
        assert max(r, g, b) <= 20 and a >= 0.7, bg


ROWS_TOP = """() => Math.round(document.querySelector('.homeSectionsContainer').getBoundingClientRect().top
  + document.scrollingElement.scrollTop)"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_rows_stay_under_the_hero_after_a_resize_while_scrolled(open_page, profile):
    # Media Bar re-measures the page on every resize (a phone's address bar folding away mid
    # scroll fires one) and used to take the scroll for the page's offset, lifting the rows
    # over the hero until a reload.
    page = open_page("home", profile, "all", variant="resized-while-scrolled")
    page.evaluate("() => document.scrollingElement.scrollTo(0, 0)")
    before = page.evaluate(ROWS_TOP)
    page.evaluate("() => document.scrollingElement.scrollTo(0, 1500)")
    page.evaluate("() => window.dispatchEvent(new Event('resize'))")
    page.wait_for_timeout(300)
    page.evaluate("() => document.scrollingElement.scrollTo(0, 0)")
    page.wait_for_timeout(100)
    assert page.evaluate(ROWS_TOP) == before
