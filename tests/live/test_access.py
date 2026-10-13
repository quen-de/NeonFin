import pytest

from harness import checks

pytestmark = pytest.mark.live

NAV = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root"
ACTIONS = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiBox-root:not(:last-child)"
MENU = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiIconButton-root:first-child"


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("feature", [("prefers-reduced-transparency", "reduce"), ("prefers-contrast", "more")])
def test_glass_turns_solid_when_asked(open_page, style, color, feature, profile):
    page = open_page("home", profile, "none", media=(feature,))
    # Phones have no navigation capsule; their menu button is a capsule of its own.
    for sel in (NAV, ACTIONS) if profile == "desktop" else (ACTIONS, MENU):
        s = style(page, sel, "backdrop-filter", "background-color")
        assert s["backdrop-filter"] == "none"
        assert color(s["background-color"]) == (9, 11, 18, 1.0)


def test_forced_colors_drop_the_glass(open_page, style):
    page = open_page("home", "desktop", "none", media=(("forced-colors", "active"),))
    for sel in (NAV, ACTIONS):
        assert style(page, sel, "backdrop-filter")["backdrop-filter"] == "none"


# The skin stills motion with 0.01ms, not 0s, so Jellyfin's transitionend handlers still run.
CARD_MOTION = "(c) => { const s = getComputedStyle(c.querySelector('.cardScalable')); return [s.transitionDuration, s.transform]; }"
STILL = """(c) => { const s = getComputedStyle(c.querySelector('.cardScalable'));
  return s.transform === 'none' && s.transitionDuration.split(',').every((d) => parseFloat(d) * (d.trim().endsWith('ms') ? 0.001 : 1) <= 0.001); }"""


def test_reduced_motion_stills_the_cards(open_page):
    page = open_page("home", "desktop", "none", media=(("prefers-reduced-motion", "reduce"),))
    card = page.locator(".homeSectionsContainer .emby-scroller .card >> visible=true").first
    card.hover()
    page.wait_for_timeout(300)
    assert card.evaluate(STILL), card.evaluate(CARD_MOTION)
    page.mouse.move(0, 0)


def test_reduced_motion_stills_keyboard_focus(open_page):
    page = open_page("home", "desktop", "none", media=(("prefers-reduced-motion", "reduce"),), variant="focus")
    card = page.locator(".homeSectionsContainer .emby-scroller .card >> visible=true").first
    card.locator(".cardImageContainer").focus()
    assert card.evaluate(STILL), card.evaluate(CARD_MOTION)


def test_forced_colors_leave_text_and_focus_to_the_system(open_page, style):
    # Box shadows vanish in forced colours, so the card's focus mark is the system outline again.
    page = open_page("home", "desktop", "none", media=(("forced-colors", "active"),), variant="focus")
    assert style(page, f"{NAV} > .MuiButton-root", "forced-color-adjust")["forced-color-adjust"] == "auto"
    target = page.locator(".homeSectionsContainer .emby-scroller .card >> visible=true").first.locator(".cardImageContainer")
    target.focus()
    assert target.evaluate("(a) => getComputedStyle(a).outlineStyle") == "solid"


LIBRARY_BAR = ".MuiAppBar-root > .MuiToolbar-root + .MuiToolbar-root"


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("feature", [("prefers-reduced-transparency", "reduce"), ("prefers-contrast", "more"), ("forced-colors", "active")])
def test_the_library_toolbar_turns_solid_when_asked(open_page, style, color, feature, profile):
    page = open_page("movies", profile, "none", media=(feature,))
    s = style(page, LIBRARY_BAR, "backdrop-filter", "background-color")
    assert s["backdrop-filter"] == "none"
    # Forced colours paint the system's own background.
    if feature[0] != "forced-colors":
        assert color(s["background-color"]) == (9, 11, 18, 1.0)


ASKS = [("prefers-reduced-transparency", "reduce"), ("prefers-contrast", "more")]


@pytest.mark.parametrize("ask", ASKS)
@pytest.mark.parametrize("route", ["home", "movies", "login", "usermenu", "jepanel"])
def test_every_glass_surface_turns_solid_with_every_plugin(open_page, route, ask):
    # Every element with a backdrop, plugin surfaces included, not only the capsules.
    assert checks.glass_elements(open_page(route, "desktop", "all", media=(ask,))) == []


SLOW = """() => {
  const secs = (v) => Math.max(...v.split(',').map((d) => parseFloat(d) * (d.trim().endsWith('ms') ? 0.001 : 1)));
  const out = new Set();
  for (const e of document.querySelectorAll('*')) for (const p of [null, '::before', '::after']) {
    const cs = getComputedStyle(e, p);
    if (secs(cs.transitionDuration) > 0.001 || (cs.animationName !== 'none' && secs(cs.animationDuration) > 0.001))
      out.add(e.tagName.toLowerCase() + [...e.classList].slice(0, 2).map((c) => '.' + c).join('') + (p || ''));
  }
  return [...out].slice(0, 20);
}"""


@pytest.mark.parametrize("route", ["home", "movie", "usermenu"])
def test_reduced_motion_stops_every_transition_and_animation(open_page, route):
    page = open_page(route, "desktop", "all", media=(("prefers-reduced-motion", "reduce"),))
    assert page.evaluate(SLOW) == []


def tab_to(page, selector, limit=80):
    """Press Tab until focus lands on selector, as a keyboard user would; False if it never does."""
    for _ in range(limit):
        page.keyboard.press("Tab")
        if page.evaluate("(s) => !!document.activeElement && !!document.activeElement.closest(s)", selector):
            return True
    return False


FOCUSED = "() => { const cs = getComputedStyle(document.activeElement); return [cs.outlineStyle, cs.outlineColor]; }"


@pytest.mark.parametrize(
    ("route", "plugin_state", "target"),
    [
        ("login", "none", ".raised.button-submit"),
        ("movie", "all", ".mainDetailButtons > .detailButton.btnPlay"),
        ("display", "all", ".MuiButton-root.MuiButton-contained"),
        ("home", "all", "#slides-container .slide.active .play-button"),
    ],
)
def test_neon_tubes_take_a_light_focus_ring(open_page, color, route, plugin_state, target):
    # A crimson ring vanishes into a tube's own crimson glow.
    page = open_page(route, "desktop", plugin_state, variant="tab")
    if not tab_to(page, target):
        if route == "home":
            pytest.skip("Tab never reaches the hero's Play on this server")
        pytest.fail(f"Tab never reached {target}")
    style, colour = page.evaluate(FOCUSED)
    assert style == "solid" and color(colour)[:3] == (255, 255, 255), (style, colour)


def test_a_user_reached_with_tab_is_ringed(open_page):
    page = open_page("picker", "desktop", "none", variant="tab")
    assert tab_to(page, "#divUsers .card", 20)
    page.wait_for_timeout(400)
    opacity, shadow = page.evaluate("""() => { const s = document.activeElement.closest('.card').querySelector('.cardScalable');
      const cs = getComputedStyle(s, '::after'); return [cs.opacity, cs.boxShadow]; }""")
    assert opacity == "1" and "255, 36, 72" in shadow, (opacity, shadow)


def test_a_user_keeps_an_outline_in_forced_colours(open_page):
    # Forced colours drop box shadows, so the ring is gone there; the outline must stay.
    page = open_page("picker", "desktop", "none", media=(("forced-colors", "active"),), variant="tab")
    assert tab_to(page, "#divUsers .card", 20)
    assert page.evaluate("() => getComputedStyle(document.activeElement).outlineStyle") != "none"


def test_disclaimer_links_are_underlined(open_page):
    # Crimson alone does not tell a link from the grey text around it.
    page = open_page("login", "desktop", "none", variant="disclaimer-link")
    line = page.evaluate("""() => { const a = document.createElement('a'); a.className = 'button-link'; a.href = '#';
      a.textContent = 'terms'; document.querySelector('#loginPage .loginDisclaimer').append(a);
      const v = getComputedStyle(a).textDecorationLine; a.remove(); return v; }""")
    assert line == "underline"


def test_the_phone_panel_leaves_room_for_the_home_bar(open_page):
    # Headless Chrome has no home bar, so read the rule itself.
    pad = open_page("login", "phone", "none").evaluate("""() => {
      for (const sheet of document.styleSheets) { let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
        for (const r of rules) if (r.selectorText === '.layout-mobile #loginPage > .margin-auto-y')
          return r.style.getPropertyValue('padding-bottom'); }
      return null; }""")
    assert pad and "safe-area-inset-bottom" in pad, pad
