import re

import pytest

from harness import checks

pytestmark = pytest.mark.live

NAV = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root"
ACTIONS = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiBox-root:not(:last-child)"
# Media Bar Enhanced builds #slides-container and puts its version class on the body.
HERO = "() => !!document.querySelector('body.jellyfin-v12 #slides-container')"
BLUR_INSIDE_SLIDES = """() => [...document.querySelectorAll('#slides-container *')].filter((e) => {
  const v = getComputedStyle(e).backdropFilter; return v && v !== 'none'; }).length"""


def hero_is(page):
    if not page.evaluate(HERO):
        pytest.skip("this server's home has no Media Bar Enhanced hero")


@pytest.mark.parametrize("profile, budget", [("desktop", 2), ("phone", 0)])
def test_home_with_every_plugin_keeps_the_glass_budget(open_page, profile, budget):
    page = open_page("home", profile, "all")
    assert page.evaluate(BLUR_INSIDE_SLIDES) == 0
    assert len(checks.glass_elements(page)) == budget


def test_hero_play_is_a_neon_tube(open_page, style, color):
    page = open_page("home", "desktop", "all")
    play = style(page, "#slides-container .slide.active .play-button", "box-shadow", "background-color")
    assert play["box-shadow"].count("inset") == 2 and color(play["background-color"])[:3] == (255, 36, 72)


def test_the_active_dot_is_crimson(open_page, style, color):
    dot = style(open_page("home", "desktop", "all"), "#slides-container .dot.active", "background-color")
    if dot is None:
        pytest.skip("this server's hero counts its slides instead of showing dots")
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


# The hero shows the plot from about 1100px wide; 1280 is the narrowest common desktop with it.
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
    # Media Bar Enhanced shows no plot on phones; its details line stands in.
    shown = ".plot" if profile == "desktop" else ":is(.plot, .misc-info)"
    assert page.locator(f"#slides-container .slide.active {shown} >> visible=true").count() >= 1
    assert checks.contrast_failures(page, "home", tmp_path / "hero.png") == []


def test_without_media_bar_home_starts_below_the_capsules(open_page):
    page = open_page("home", "desktop", "without:media-bar-enhanced")
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
    # Only desktop fades down from the top, under its glass capsules: the one gradient with no
    # angle, since Chrome leaves out the default top-to-bottom.
    top_fade = re.compile(r"linear-gradient\((?!\d+deg|to )")
    assert len(top_fade.findall(desktop)) == 1 and top_fade.findall(phone) == [], (desktop, phone)


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


def _hold_the_slide(page):
    """Stop the slideshow and finish what is moving, so two samples see the same slide."""
    pause = page.locator("#slides-container .pause-button >> visible=true")
    if pause.count():
        pause.first.click()
    page.evaluate("() => document.getAnimations().forEach((a) => { try { a.finish(); } catch (e) {} })")
    page.wait_for_timeout(200)


def test_the_desktop_hero_shows_more_of_the_artwork(open_page, tmp_path):
    page = open_page("home", "desktop", "all", variant="white-hero")
    page.add_style_tag(
        content="#slides-container .backdrop-container { background: #fff !important; }"
        " #slides-container .backdrop-container > * { visibility: hidden !important; }"
    )
    page.wait_for_timeout(200)
    _hold_the_slide(page)
    assert _hero_light(page, tmp_path, 0.85) >= 85  # under the end of the plot
    assert _hero_light(page, tmp_path, 720) >= 170  # mid-screen, beside the text column


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_hero_text_is_primary_white(open_page, style, color, profile):
    page = open_page("home", profile, "all")
    details = (".misc-info", ".genre")
    for sel in (".plot", *details):
        assert color(style(page, f"#slides-container .slide.active {sel}", "color")["color"])[3] >= 0.9, sel


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
    # A hero that re-measures the page on every resize (a phone's address bar folding away mid
    # scroll fires one) can take the scroll for the page's offset and lift the rows over it.
    page = open_page("home", profile, "all", variant="resized-while-scrolled")
    page.evaluate("() => document.scrollingElement.scrollTo(0, 0)")
    before = page.evaluate(ROWS_TOP)
    page.evaluate("() => document.scrollingElement.scrollTo(0, 1500)")
    page.evaluate("() => window.dispatchEvent(new Event('resize'))")
    page.wait_for_timeout(300)
    page.evaluate("() => document.scrollingElement.scrollTo(0, 0)")
    page.wait_for_timeout(100)
    assert page.evaluate(ROWS_TOP) == before


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_enhanced_details_are_set_in_the_interface_face(open_page, style, profile):
    # The plugin brings a narrow web font; the skin keeps its own and loads nothing more.
    page = open_page("home", profile, "all")
    hero_is(page)
    for sel in (".misc-info", ".genre", ".play-button"):
        face = style(page, f"#slides-container .slide.active {sel}", "font-family")["font-family"]
        assert face.startswith("-apple-system") and "Archivo" not in face, (sel, face)


def test_enhanced_counter_is_tinted_and_its_progress_crimson(open_page, style, color):
    page = open_page("home", "desktop", "all")
    hero_is(page)
    counter = style(page, "#slides-container .slide-counter", "backdrop-filter", "background-color")
    if counter is None:
        pytest.skip("this server's Media Bar Enhanced shows dots, not a counter")
    assert counter["backdrop-filter"] == "none" and color(counter["background-color"])[:3] == (9, 11, 18)
    fill = style(page, "#slides-container .media-bar-progress-fill", "background-color")
    assert color(fill["background-color"])[:3] == (255, 36, 72)


def test_enhanced_trailer_is_a_tinted_pill_beside_play(open_page, style, color):
    page = open_page("home", "desktop", "all", variant="trailer")
    hero_is(page)
    # Only a slide with a trailer has the button: give the current one a button like the plugin's.
    page.evaluate("""() => { const b = document.createElement('button');
      b.className = 'detailButton trailer-button'; b.textContent = 'Trailer';
      document.querySelector('#slides-container .slide.active .button-container').append(b); }""")
    trailer = style(page, "#slides-container .slide.active .trailer-button", "background-color", "border-top-left-radius")
    play = style(page, "#slides-container .slide.active .play-button", "border-top-left-radius")
    assert color(trailer["background-color"])[3] <= 0.15, trailer
    assert trailer["border-top-left-radius"] == play["border-top-left-radius"] == "999px"


LONG_DETAILS = """() => {
  const slide = document.querySelector('#slides-container .slide.active'), line = slide.querySelector('.misc-info');
  for (const text of ['Ends at 11:59 PM', '2h 38m', 'Dolby Vision']) {
    const item = document.createElement('div'); item.className = 'runTime'; item.textContent = text; line.append(item); }
  const lines = (e) => new Set([...(() => { const r = document.createRange(); r.selectNodeContents(e); return r.getClientRects(); })()]
    .map((r) => Math.round(r.top))).size;
  return { right: line.getBoundingClientRect().right, plot: slide.querySelector('.plot').getBoundingClientRect().right,
    width: innerWidth, broken: [...line.querySelectorAll('.runTime, .date')].filter((e) => lines(e) > 1).map((e) => e.textContent) }; }"""


@pytest.mark.parametrize("profile, viewport", [("desktop", (1280, 800)), ("phone", None)])
def test_a_long_enhanced_details_line_wraps_between_items(open_page, profile, viewport):
    # The interface face is wider than the plugin's: a long line wraps between its items, never
    # inside one, and on desktop keeps to the dimmed column the plot keeps to.
    page = open_page("home", profile, "all", viewport=viewport, variant="long-details")
    hero_is(page)
    r = page.evaluate(LONG_DETAILS)
    assert r["broken"] == [], r
    assert r["right"] <= (r["plot"] + 1 if profile == "desktop" else r["width"]), r
