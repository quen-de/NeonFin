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


def test_focus_left_by_a_mouse_click_leaves_the_card_dark(open_page):
    # On Windows a click leaves focus on the card's button; once the pointer leaves, the card
    # goes dark. Chromium on macOS focuses no button on click, so the test sets that state up:
    # a click focuses a spot in the margin, and focus moved on from there is not keyboard focus.
    page = open_page("home", "desktop", "none", variant="click")
    card = page.locator(f"{CARD} >> visible=true").nth(1)
    page.evaluate(
        """() => { const d = document.createElement('div'); d.tabIndex = -1; d.id = 'nf-test-spot';
      d.style.cssText = 'position:fixed;left:0;bottom:0;width:8px;height:8px'; document.body.append(d); }"""
    )
    page.mouse.click(4, page.viewport_size["height"] - 4)
    button = card.locator("button.cardOverlayButton").first
    button.evaluate("(b) => b.focus()")
    page.wait_for_timeout(400)
    assert button.evaluate("(b) => b === document.activeElement && !b.matches(':focus-visible')")
    s = card.evaluate(CARD_STATE)
    assert s["transform"] == "none" and s["ring"] == "0", s


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
    box = card.locator(".cardScalable").bounding_box()
    clip = {"x": box["x"] + box["width"] * 0.3, "y": box["y"] - 34, "width": box["width"] * 0.4, "height": 28}
    page.screenshot(path=str(tmp_path / "unlit.png"), clip=clip)
    card.hover()
    page.wait_for_timeout(300)
    page.screenshot(path=str(tmp_path / "glow.png"), clip=clip)
    page.mouse.move(0, 0)
    unlit = [round(r) for r, _, _ in rows(tmp_path / "unlit.png")]
    reds = [round(r) for r, _, _ in rows(tmp_path / "glow.png")]
    assert max(r - u for r, u in zip(reds, unlit)) >= 15, (unlit, reds)  # the glow is there
    assert max(b - a for a, b in zip(reds, reds[1:])) < 25, reds  # and fades, no step


def test_the_ring_goes_out_at_once_with_the_glow(open_page):
    # Leaving a card brings Jellyfin's paint containment straight back, which would cut a
    # fading glow at the card's edge, so the ring goes out at once.
    page = open_page("home", "desktop", "none", variant="unhover")
    card = page.locator(f"{CARD} >> visible=true").nth(1)
    card.hover()
    page.wait_for_timeout(300)
    page.mouse.move(0, 0)
    assert card.locator(".cardScalable").evaluate("(s) => getComputedStyle(s, '::after').opacity") == "0"


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


BADGE = """(sel) => { const b = document.querySelector(sel); if (!b) return null;
  const box = b.closest('.cardIndicators'), s = b.closest('.cardScalable');
  const r = b.getBoundingClientRect(), c = s.getBoundingClientRect(), bc = getComputedStyle(box), cs = getComputedStyle(b);
  return { top: r.top - c.top, right: c.right - r.right, corner: bc.borderTopRightRadius, clip: bc.overflow,
           round: cs.borderTopLeftRadius, bg: cs.backgroundColor, blur: cs.backdropFilter, w: r.width, h: r.height }; }"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_unplayed_counts_are_crimson_glass_tabs_in_the_corner(open_page, color, profile):
    got = open_page("series", profile, "none").evaluate(BADGE, ".itemsContainer .card .cardIndicators .countIndicator")
    if got is None:
        pytest.skip("no unplayed counts on this server's shows")
    assert got["top"] == pytest.approx(0, abs=0.5) and got["right"] == pytest.approx(0, abs=0.5)
    assert got["corner"] == "12px" and got["clip"] == "hidden"  # the tab follows the card's corner
    assert got["round"] == "0px" and got["w"] >= got["h"]  # a tab, not a disc
    r, g, b, a = color(got["bg"])
    assert r > 2 * max(g, b) and 0.5 < a < 1  # crimson, see-through
    assert got["blur"] == "none"  # no live glass on hundreds of cards


GAPS = """() => {
  const secs = [...document.querySelectorAll('.homeSectionsContainer > .verticalSection')]
    .filter((s) => s.querySelector('.card') && s.getBoundingClientRect().height > 0);
  const out = [];
  for (let i = 0; i + 1 < secs.length; i++) {
    const last = [...secs[i].querySelectorAll('.cardBox')].pop(), t = secs[i + 1].querySelector('.sectionTitle');
    const box = t && (t.closest('.sectionTitleContainer') || t);
    if (!box || box.getBoundingClientRect().width <= 1) continue;
    // From the title's text, not its box: a title outside a container carries its own padding.
    const top = t.getBoundingClientRect().top + parseFloat(getComputedStyle(t).paddingTop);
    out.push(Math.round(top - last.getBoundingClientRect().bottom));
  }
  return out;
}"""


@pytest.mark.parametrize("plugin_state", ["all", "none"])
def test_rows_sit_closer_on_phones(open_page, plugin_state):
    gaps = open_page("home", "phone", plugin_state).evaluate(GAPS)
    assert gaps and all(36 <= g <= 62 for g in gaps), gaps
    # Evenly: a title in a container (a link) sits no lower than a bare one.
    assert max(gaps) - min(gaps) <= 4, gaps


def test_rows_keep_their_generous_separation_on_desktop(open_page):
    gaps = open_page("home", "desktop", "all").evaluate(GAPS)
    assert gaps and all(g >= 80 for g in gaps), gaps


@pytest.mark.parametrize("route, profile", [("home", "desktop"), ("home", "phone"), ("movies", "desktop")])
def test_the_placeholder_under_the_artwork_takes_its_corners(open_page, route, profile):
    # Jellyfin paints a gray placeholder under each poster; with a smaller radius its corners
    # poke out past the artwork's.
    radii = open_page(route, profile, "none").evaluate(
        """() => [...document.querySelectorAll('.card .cardBox:not(.visualCardBox) .cardPadder')].slice(0, 8)
      .map((p) => [p, p.parentElement.querySelector('.cardImageContainer')].map((e) => getComputedStyle(e).borderTopLeftRadius))"""
    )
    assert radii and all(a == b == "12px" for a, b in radii), radii


MY_MEDIA = """() => {
  const s = [...document.querySelectorAll('.homeSectionsContainer > .verticalSection')]
    .find((x) => x.querySelector('.card[data-type="CollectionFolder"]'));
  if (!s) return null;
  const t = s.querySelector('.sectionTitle'), cs = getComputedStyle(t);
  const box = (t.closest('.sectionTitleContainer') || t).getBoundingClientRect();
  return { text: t.textContent.trim(), w: box.width, h: box.height, display: cs.display, visibility: cs.visibility,
           cards: [...s.querySelectorAll('.card')].filter((c) => c.getBoundingClientRect().width > 0).length };
}"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("plugin_state", ["all", "none"])
def test_my_media_keeps_its_row_but_not_its_title(open_page, profile, plugin_state):
    got = open_page("home", profile, plugin_state).evaluate(MY_MEDIA)
    if got is None:
        pytest.skip("no My Media row on this user's home")
    assert got["cards"] > 0
    assert got["w"] <= 1 and got["h"] <= 1  # nothing on screen
    assert got["text"] and got["display"] != "none" and got["visibility"] == "visible"  # still read out


def hovered_card(page, kind="Movie"):
    card = page.locator(f".card[data-type='{kind}'] >> visible=true").first
    card.scroll_into_view_if_needed()
    card.hover()
    page.wait_for_timeout(400)
    return card


@pytest.mark.parametrize("route", ["home", "movies"])
def test_card_actions_answer_hover_without_blue(open_page, route):
    # Play, Mark played, Add to favorites, More: home renders them as legacy buttons, libraries
    # as MUI ones.
    page = open_page(route, "desktop", "none", variant="card-actions")
    buttons = hovered_card(page).locator(".cardOverlayContainer button")
    assert buttons.count() >= 4
    for i in range(buttons.count()):
        buttons.nth(i).hover()
        page.wait_for_timeout(300)
        assert checks.blue_hits(page) == {}, buttons.nth(i).get_attribute("class")
    page.mouse.move(0, 0)


def test_episode_list_actions_answer_hover_without_blue(open_page):
    page = open_page("season", "desktop", "none", variant="list-actions")
    buttons = page.locator(".listItem button.paper-icon-button-light >> visible=true")
    assert buttons.count() >= 3
    for i in range(3):
        buttons.nth(i).hover()
        page.wait_for_timeout(300)
        assert checks.blue_hits(page) == {}, buttons.nth(i).get_attribute("class")
    page.mouse.move(0, 0)


@pytest.mark.parametrize(("route", "kind"), [("home", "Movie"), ("movies", "Movie"), ("series", "Series"), ("search", "Movie")])
def test_card_play_is_a_neon_tube_on_a_dark_disc(open_page, color, route, kind):
    page = open_page(route, "desktop", "none", variant="card-play")
    play = hovered_card(page, kind).locator(".cardOverlayFab-primary")
    fg, bg, shadow = play.evaluate("(e) => { const cs = getComputedStyle(e); return [cs.color, cs.backgroundColor, cs.boxShadow]; }")
    r, g, b, a = color(bg)
    assert color(fg) == (255, 255, 255, 1.0) and shadow.count("inset") == 2, (fg, shadow)
    assert r > 2 * max(g, b) and a >= 0.7, bg
    play.hover()
    page.wait_for_timeout(300)
    assert color(play.evaluate("(e) => getComputedStyle(e).backgroundColor"))[0] > r
    page.mouse.move(0, 0)


def test_played_and_favourite_marks_are_crimson(open_page, color):
    page = open_page("movie", "desktop", "none", variant="marks")
    got = page.evaluate("""() => ['playstatebutton-icon-played', 'ratingbutton-icon-withrating'].map((c) => {
      const i = document.createElement('span'); i.className = 'material-icons ' + c; document.body.append(i);
      const v = getComputedStyle(i).color; i.remove(); return v; })""")
    for v in got:
        assert color(v)[:3] == (255, 36, 72), v


@pytest.mark.parametrize("route", ["movies", "series"])
def test_played_and_favourite_marks_on_library_cards_are_crimson(open_page, color, route):
    # Library cards draw their marks as SVG icons, not the icon font home uses.
    page = open_page(route, "desktop", "none", variant="marks")
    page.locator(".itemsContainer .card").first.hover()
    page.wait_for_timeout(300)
    got = page.evaluate("""() => { const c = document.querySelector('.itemsContainer .card');
      return [['CheckIcon', 'playstatebutton-icon-played'], ['FavoriteIcon', 'ratingbutton-icon-withrating']].map(([icon, cls]) => {
        const s = c.querySelector(`.cardOverlayContainer svg[data-testid="${icon}"]`);
        s.classList.add(cls); return getComputedStyle(s).color; }); }""")
    page.mouse.move(0, 0)
    for v in got:
        assert color(v)[:3] == (255, 36, 72), v


MY_MEDIA_NAMES = """(bare) => {
  const s = [...document.querySelectorAll('.homeSectionsContainer > .verticalSection')]
    .find((x) => x.querySelector('.card[data-type="CollectionFolder"]'));
  if (!s) return null;
  const cards = [...s.querySelectorAll('.card')].filter((c) => c.getBoundingClientRect().width > 0);
  if (bare) cards[0].querySelector('.cardImageContainer').classList.add('defaultCardBackground');
  return cards.map((c) => { const t = c.querySelector('.cardText'), r = t.getBoundingClientRect();
    return { text: t.textContent.trim(), w: r.width, h: r.height, art: !c.querySelector('.defaultCardBackground') }; });
}"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("plugin_state", ["all", "none"])
def test_my_media_tiles_with_artwork_drop_their_names(open_page, profile, plugin_state):
    # Library artwork carries its own lettering; the name under it doubled it.
    got = open_page("home", profile, plugin_state).evaluate(MY_MEDIA_NAMES, False)
    if got is None:
        pytest.skip("no My Media row on this user's home")
    tiles = [t for t in got if t["art"]]
    assert tiles and all(t["w"] <= 1 and t["h"] <= 1 and t["text"] for t in tiles), got  # still read out


def test_a_my_media_tile_without_artwork_keeps_its_name(open_page):
    got = open_page("home", "desktop", "none", variant="bare-tile").evaluate(MY_MEDIA_NAMES, True)
    if got is None:
        pytest.skip("no My Media row on this user's home")
    assert not got[0]["art"] and got[0]["h"] > 10, got[0]
