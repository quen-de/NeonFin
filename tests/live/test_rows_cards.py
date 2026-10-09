import pytest

from harness import checks

pytestmark = pytest.mark.live

SIGN = ".homeSectionsContainer .sectionTitleContainer .sectionTitle"
CARD = ".homeSectionsContainer .emby-scroller .card"
CARD_STATE = """(card) => {
  const s = card.querySelector('.cardScalable'), cs = getComputedStyle(s);
  return { transform: cs.transform, radius: cs.borderTopLeftRadius, opacity: cs.opacity,
           ring: getComputedStyle(s, '::before').opacity, edge: getComputedStyle(s, '::after').boxShadow };
}"""


def first_card(page):
    return page.locator(f"{CARD} >> visible=true").first


@pytest.mark.parametrize("profile, rem, plugin_state", [("desktop", 2.1, "none"), ("desktop", 2.1, "all"), ("phone", 1.5, "none")])
def test_row_titles_are_lit_signs(open_page, style, profile, rem, plugin_state):
    page = open_page("home", profile, plugin_state)
    s = style(page, SIGN, "font-family", "font-weight", "text-transform", "text-shadow", "font-size")
    root = float(style(page, "html", "font-size")["font-size"].removesuffix("px"))
    assert s["font-family"].startswith('"NeonFin Sign"')
    assert s["font-weight"] == "800" and s["text-transform"] == "uppercase"
    assert s["text-shadow"].count("px") >= 9  # three glow layers
    assert float(s["font-size"].removesuffix("px")) == pytest.approx(rem * root, abs=0.2)
    assert page.evaluate("[...document.fonts].some((f) => f.family.replace(/\"/g, '') === 'NeonFin Sign' && f.status === 'loaded')")


def test_long_row_titles_wrap_on_phones(open_page):
    page = open_page("home", "phone", "none", variant="long-title")
    right = page.evaluate(
        """(sel) => { const t = document.querySelector(sel);
      t.textContent = 'Récemment ajoutés dans Documentaires et séries';
      return t.getBoundingClientRect().right; }""",
        SIGN,
    )
    assert right <= 412


def test_cards_have_rounded_artwork_a_hairline_and_a_hidden_ring(open_page):
    s = first_card(open_page("home", "desktop", "none")).evaluate(CARD_STATE)
    assert s["radius"] == "12px" and s["ring"] == "0" and "inset" in s["edge"]


def test_hover_lifts_the_card_and_lights_the_ring_without_dimming_others(open_page):
    page = open_page("home", "desktop", "none", variant="hover")
    cards = page.locator(f"{CARD} >> visible=true")
    cards.first.hover()
    page.wait_for_timeout(400)
    s = cards.first.evaluate(CARD_STATE)
    assert s["transform"] == "matrix(1, 0, 0, 1, 0, -4)" and s["ring"] == "1"
    assert cards.nth(1).evaluate(CARD_STATE)["opacity"] == "1"
    page.mouse.move(0, 0)


def test_pointer_hover_lifts_at_once(open_page):
    # A gliding lift restyles the card on every frame while rows scroll under a still pointer.
    page = open_page("home", "desktop", "none", variant="hover")
    card = first_card(page)
    card.hover()
    got = card.evaluate(
        "(c) => { const s = getComputedStyle(c.querySelector('.cardScalable')); return [s.transform, s.transitionDuration]; }"
    )
    assert got == ["matrix(1, 0, 0, 1, 0, -4)", "0s"]
    page.mouse.move(0, 0)


def test_touch_screens_keep_no_hover_lift(open_page):
    page = open_page("home", "phone", "none", variant="hover")
    card = first_card(page)
    card.hover()
    page.wait_for_timeout(400)
    s = card.evaluate(CARD_STATE)
    assert s["transform"] == "none" and s["ring"] == "0"
    page.mouse.move(0, 0)


def test_keyboard_focus_matches_hover(open_page):
    page = open_page("home", "desktop", "none", variant="focus")
    card = first_card(page)
    card.locator(".cardImageContainer").focus()
    page.wait_for_timeout(400)
    s = card.evaluate(CARD_STATE)
    assert s["transform"] == "matrix(1, 0, 0, 1, 0, -4)" and s["ring"] == "1"
    assert card.evaluate("(c) => getComputedStyle(c.querySelector('.cardScalable')).transitionDuration") == "0.18s"


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("plugin_state", ["all", "none"])
def test_no_jellyfin_blue_on_home(open_page, profile, plugin_state):
    assert checks.blue_hits(open_page("home", profile, plugin_state)) == {}
