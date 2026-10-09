import pytest

from harness import checks

pytestmark = pytest.mark.live

SIGN = ".homeSectionsContainer .sectionTitleContainer .sectionTitle"
CARD = ".homeSectionsContainer .emby-scroller .card"
CARD_STATE = """(card) => {
  const s = card.querySelector('.cardScalable'), cs = getComputedStyle(s);
  return { transform: cs.transform, radius: cs.borderTopLeftRadius, opacity: cs.opacity,
           ring: getComputedStyle(s, '::after').opacity, edge: getComputedStyle(s.querySelector('.cardImageContainer')).boxShadow };
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


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("plugin_state", ["all", "none"])
def test_every_visible_home_row_title_is_a_sign(open_page, profile, plugin_state):
    # Jellyfin renders some row titles bare inside the section, others inside a title container.
    page = open_page("home", profile, plugin_state)
    fonts = page.evaluate(
        """() => [...document.querySelectorAll('.verticalSection .sectionTitle')]
      .filter((e) => e.getBoundingClientRect().width > 0)
      .map((e) => getComputedStyle(e).fontFamily)"""
    )
    assert fonts and all(f.startswith('"NeonFin Sign"') for f in fonts), fonts


def test_long_row_titles_wrap_on_phones(open_page):
    page = open_page("home", "phone", "none", variant="long-title")
    got = page.evaluate(
        """(sel) => { const t = [...document.querySelectorAll(sel)].find((e) => e.getBoundingClientRect().width > 0);
      t.textContent = 'Récemment ajoutés dans Documentaires et séries';
      const row = t.closest('.sectionTitleContainer') || t.parentElement;
      return { width: t.getBoundingClientRect().width, right: Math.max(t.getBoundingClientRect().right, row.getBoundingClientRect().right),
               overflow: document.documentElement.scrollWidth - innerWidth }; }""",
        SIGN,
    )
    assert got["width"] > 0 and got["right"] <= 412 and got["overflow"] <= 0


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


def test_keyboard_focus_draws_one_ring(open_page):
    page = open_page("home", "desktop", "none", variant="focus")
    target = first_card(page).locator(".cardImageContainer")
    target.focus()
    assert target.evaluate("(a) => [a.matches(':focus-visible'), getComputedStyle(a).outlineStyle]") == [True, "none"]


def test_the_ring_glow_fades_out_instead_of_being_cut(open_page, rows, tmp_path):
    page = open_page("home", "desktop", "none", variant="hover")
    card = page.locator(f"{CARD} >> visible=true").nth(1)
    card.hover()
    page.wait_for_timeout(300)
    box = card.locator(".cardScalable").bounding_box()
    shot = tmp_path / "glow.png"
    page.screenshot(
        path=str(shot), clip={"x": box["x"] + box["width"] * 0.3, "y": box["y"] - 30, "width": box["width"] * 0.4, "height": 28}
    )
    page.mouse.move(0, 0)
    reds = [round(r) for r, _, _ in rows(shot)]
    assert max(b - a for a, b in zip(reds, reds[1:])) < 25, reds


def test_plugin_badges_on_cards_survive_the_ring(open_page):
    # Plugins draw badges on .cardScalable::before (Home Screen Sections' Discover row does),
    # so the skin leaves that pseudo-element alone.
    page = open_page("home", "desktop", "none", variant="badge")
    page.add_style_tag(content=".nf-test-badge::before { content: 'Badge'; position: absolute; background-color: rgb(0, 0, 255); }")
    card = first_card(page)
    card.locator(".cardScalable").evaluate("(s) => s.classList.add('nf-test-badge')")
    card.hover()
    page.wait_for_timeout(300)
    got = card.locator(".cardScalable").evaluate(
        "(s) => { const b = getComputedStyle(s, '::before'); return [b.content, b.width === getComputedStyle(s).width]; }"
    )
    page.mouse.move(0, 0)
    assert got == ['"Badge"', False]


def test_discover_cards_keep_their_type_badges(open_page):
    page = open_page("home", "desktop", "all")
    badges = page.evaluate(
        """() => [...document.querySelectorAll('.cardScalable[class*="discoverCard-"]')].slice(0, 6)
      .map((s) => getComputedStyle(s, '::before').content)"""
    )
    if not badges:
        pytest.skip("no Home Screen Sections Discover row on this server")
    assert all(b not in ("none", '""') for b in badges), badges
