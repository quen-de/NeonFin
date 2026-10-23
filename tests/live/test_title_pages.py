import re

import pytest

from harness import checks

pytestmark = pytest.mark.live

# Desktop shows the backdrop behind the page and leaves the in-page one empty; phones fill it.
WHITE_BACKDROP = ".backdropImage, .itemBackdrop[style*='url('] { background: #fff !important; filter: none !important; }"
PAINTED = """() => [...document.querySelectorAll('.backdropImage.displayingBackdropImage, .itemBackdrop[style*="url("]')]
  .filter((e) => e.getBoundingClientRect().height > 0).map((e) => getComputedStyle(e).backgroundColor)"""
PANEL_PAINT = """(sel) => { const e = document.querySelector(sel); const cs = getComputedStyle(e);
  return [cs.backgroundColor, cs.backgroundImage, getComputedStyle(e, '::before').backgroundImage]; }"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", ["movie", "show"])
def test_title_pages_have_no_gray_panels(open_page, color, profile, route):
    # Jellyfin's gray ribbon and page panel give way to the skin's ink, so the backdrop's own
    # colour comes through.
    page = open_page(route, profile, "none")
    for sel in (".detailRibbon", ".detailPageWrapperContainer"):
        bg, image, before = page.evaluate(PANEL_PAINT, sel)
        assert color(bg)[3] == 0, (sel, bg)
        stops = [color(c) for c in re.findall(r"rgba?\([^)]*\)", image + before)]
        assert all(max(c[:3]) <= 12 for c in stops), (sel, image, before)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_title_page_text_reads_over_a_white_backdrop(open_page, tmp_path, profile):
    page = open_page("movie", profile, "none", variant="white-backdrop")
    page.add_style_tag(content=WHITE_BACKDROP)
    page.wait_for_timeout(300)
    assert "rgb(255, 255, 255)" in page.evaluate(PAINTED)
    labels = page.evaluate("(sels) => sels.filter((s) => document.querySelector(s))", list(checks.TEXT_TARGETS["movie"]))
    assert len(labels) >= 4, labels
    assert checks.contrast_failures(page, "movie", tmp_path / "white.png") == []


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", ["movie", "season"])
def test_the_title_is_a_lit_sign(open_page, style, profile, route):
    s = style(open_page(route, profile, "none"), ".detailRibbon .nameContainer > h1", "font-family", "text-transform", "text-shadow")
    assert s["font-family"].startswith('"NeonFin Sign"') and s["text-transform"] == "uppercase"
    assert s["text-shadow"].count("px") >= 9


GLOW = """() => { const h = document.querySelector('.detailRibbon .nameContainer > h1');
  const range = document.createRange(); range.selectNodeContents(h); const t = range.getBoundingClientRect();
  return { above: { x: t.left, y: t.top - 6, width: Math.min(t.width, 300), height: 5 },
           before: { x: t.left - 6, y: t.top + t.height / 4, width: 5, height: t.height / 2 } }; }"""


@pytest.mark.parametrize("route", ["movie", "show"])
def test_the_sign_glow_is_not_cut_off(open_page, tmp_path, route):
    # Jellyfin clips the desktop title to its box for the ellipsis; the glow must still spill
    # past the box, not end in a hard edge.
    from PIL import Image

    page = open_page(route, "desktop", "none", variant="black-backdrop")
    page.add_style_tag(content=".backdropImage { background: #000 !important; }")
    page.wait_for_timeout(300)
    for side, clip in page.evaluate(GLOW).items():
        page.screenshot(path=str(tmp_path / f"{side}.png"), clip=clip, animations="disabled")
        im = Image.open(tmp_path / f"{side}.png").convert("RGB")
        px = list(getattr(im, "get_flattened_data", im.getdata)())
        # An unclipped title (a season's) measures 14 here; a clipped one nothing at all.
        assert max(r - max(g, b) for r, g, b in px) >= 8, side


def test_watched_checks_outside_cards_stay_crimson(open_page, color):
    # Lists (episodes, playlists) show the watched check outside the card tab. The test
    # library may have nothing watched, so add one in Jellyfin's list markup.
    page = open_page("season", "desktop", "none", variant="list-check")
    bg = page.evaluate("""() => { const box = document.createElement('div'); box.className = 'listItemIndicators';
      box.innerHTML = '<div class="playedIndicator indicator"><span class="material-icons indicatorIcon check"></span></div>';
      document.querySelector('.detailPageWrapperContainer').prepend(box);
      return getComputedStyle(box.firstChild).backgroundColor; }""")
    r, g, b, a = color(bg)
    assert r > 2 * max(g, b) and a > 0.5, bg


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_a_focused_track_select_is_crimson_not_blue(open_page, color, profile):
    page = open_page("movie", profile, "none", variant="focused-select")
    page.locator(".trackSelections select:not([disabled]) >> visible=true").first.focus()
    # Read the edge once its transition ends: mid-way, Chrome reports an oklab() blend.
    page.evaluate("() => Promise.all(document.activeElement.getAnimations().map((a) => a.finished))")
    assert checks.blue_hits(page) == {}
    edge = page.evaluate("() => getComputedStyle(document.activeElement).borderTopColor")
    r, g, b, _ = color(edge)
    assert r > 2 * max(g, b), edge


BUTTONS = """() => [...document.querySelectorAll('.mainDetailButtons > .detailButton')].filter((b) => b.offsetParent).map((b) => {
  const cs = getComputedStyle(b), r = b.getBoundingClientRect();
  return { play: b.classList.contains('btnPlay'), w: r.width, h: r.height, left: r.left, right: r.right,
           radius: cs.borderTopLeftRadius, shadow: cs.boxShadow, bg: cs.backgroundColor };
})"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_play_is_a_round_neon_tube_and_the_other_buttons_round_and_tinted(open_page, color, profile):
    buttons = open_page("movie", profile, "none").evaluate(BUTTONS)
    play = [b for b in buttons if b["play"]]
    rest = [b for b in buttons if not b["play"]]
    assert len(play) == 1 and rest
    assert play[0]["shadow"].count("inset") == 2 and color(play[0]["bg"])[:3] == (255, 36, 72)
    for b in buttons:
        assert b["w"] == pytest.approx(b["h"], abs=0.5) and float(b["radius"].removesuffix("px")) >= b["h"] / 2, b
    for b in rest:
        r, g, bl, a = color(b["bg"])
        assert min(r, g, bl) == 255 and 0.04 <= a <= 0.12 and "inset" in b["shadow"], b
    edges = sorted((b["left"], b["right"]) for b in buttons)
    assert all(nxt[0] - cur[1] >= 8 for cur, nxt in zip(edges, edges[1:])), edges


def test_the_phone_backdrop_fades_into_the_page(open_page, style):
    s = style(open_page("movie", "phone", "none"), ".itemBackdrop", "mask-image")
    assert "linear-gradient" in s["mask-image"] and "transparent" in s["mask-image"].replace("rgba(0, 0, 0, 0)", "transparent")


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_track_dropdowns_are_tinted_fields(open_page, color, profile):
    page = open_page("movie", profile, "none")
    s = page.evaluate(
        """() => { const e = [...document.querySelectorAll('.trackSelections select.emby-select-withcolor:not([disabled])')]
        .find((x) => x.offsetParent);
      if (!e) return null; const cs = getComputedStyle(e);
      return { radius: cs.borderTopLeftRadius, bg: cs.backgroundColor, bw: cs.borderTopWidth, bc: cs.borderTopColor }; }"""
    )
    assert s is not None
    r, g, b, a = color(s["bg"])
    assert s["radius"] == "10px" and min(r, g, b) == 255 and 0.04 <= a <= 0.12, s
    assert s["bw"] == "1px" and min(color(s["bc"])[:3]) == 255, s


@pytest.mark.parametrize("route", ["movie", "show", "season"])
def test_no_jellyfin_blue_on_title_pages(open_page, route):
    # Cards without artwork included: Jellyfin fills them from a palette of its blues.
    assert checks.blue_hits(open_page(route, "desktop", "none")) == {}


def test_settings_dropdowns_are_tinted_fields_without_an_underline(open_page, style, color):
    page = open_page("display", "desktop", "none")
    s = style(page, ".MuiFilledInput-root", "border-top-left-radius", "background-color")
    under = style(page, ".MuiFilledInput-root", "display", pseudo="::before")
    r, g, b, a = color(s["background-color"])
    assert s["border-top-left-radius"] == "10px" and min(r, g, b) == 255 and a <= 0.12, s
    assert under["display"] == "none"


SECONDARY = (246, 243, 240, 0.62)
LINK_HOVER = (255, 124, 145)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_the_details_line_steps_back_from_the_title(open_page, style, color, profile):
    page = open_page("movie", profile, "none")
    item = style(page, ".detailRibbon .itemMiscInfo-primary > .mediaInfoItem", "color")
    badge = style(page, ".detailRibbon .mediaInfoOfficialRating", "color", "border-top-color", "border-top-left-radius")
    assert color(item["color"]) == pytest.approx(SECONDARY, abs=0.01)
    assert color(badge["color"]) == pytest.approx(SECONDARY, abs=0.01)
    assert badge["border-top-color"] == badge["color"] and badge["border-top-left-radius"] == "6px"


PROSE = (
    "A retired harbour pilot returns to the island where his brother vanished thirty years ago, and finds the "
    "case files rewritten, the witnesses scattered, and the lighthouse keeper unwilling to say what the tide "
    "carried in that night. Old friends close ranks as he follows a trail of letters, debts and half-remembered "
    "songs, until the storm season cuts the ferry and leaves him alone with the people who know the truth."
)
LINES = """(text) => { const o = document.querySelector('.detailPagePrimaryContainer .overview'); o.textContent = text;
  const r = document.createRange(), node = o.firstChild, lines = new Map();
  for (let i = 0; i < text.length; i++) { r.setStart(node, i); r.setEnd(node, i + 1); const q = r.getClientRects()[0];
    if (q) lines.set(Math.round(q.top), (lines.get(Math.round(q.top)) || 0) + 1); }
  return [...lines.values()]; }"""


def test_the_overview_runs_about_75_characters_a_line(open_page):
    # Characters of real prose per line, not zeros: a ch is wider than the average letter.
    lines = open_page("movie", "desktop", "none", variant="prose").evaluate(LINES, PROSE)
    assert len(lines) >= 5 and all(66 <= n <= 84 for n in lines[:-1]), lines


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_tags_links_and_credit_labels_step_back(open_page, style, color, profile):
    page = open_page("movie", profile, "none")
    for sel in (".itemTags a", ".itemExternalLinks a", ".detailsGroupItem .label"):
        assert color(style(page, sel, "color")["color"]) == pytest.approx(SECONDARY, abs=0.01), sel


def test_links_light_up_crimson_on_hover(open_page, color):
    page = open_page("movie", "desktop", "none", variant="link-hover")
    for sel in (".itemTags a", ".itemExternalLinks a", ".detailsGroupItem a"):
        link = page.locator(f"{sel} >> visible=true").first
        link.hover()
        page.wait_for_timeout(300)
        assert color(link.evaluate("(e) => getComputedStyle(e).color"))[:3] == LINK_HOVER, sel
    page.mouse.move(0, 0)


STRIPES = ".backdropImage.displayingBackdropImage { background: repeating-linear-gradient(90deg, #fff 0 12px, #000 12px 24px) !important; }"
ONLY_BACKDROP = ".mainAnimatedPage, .MuiAppBar-root, .backgroundContainer { visibility: hidden !important; }"


def test_the_backdrop_softens_into_a_blur_toward_the_bottom(open_page, tmp_path):
    # Sharp at the top, the same image blurred toward the bottom (spec 6.7).
    from PIL import Image, ImageStat

    page = open_page("movie", "desktop", "none", variant="stripes")
    page.add_style_tag(content=STRIPES)
    page.wait_for_timeout(300)
    page.screenshot(path=str(tmp_path / "b.png"), style=ONLY_BACKDROP, animations="disabled")
    im = Image.open(tmp_path / "b.png").convert("L")
    top = ImageStat.Stat(im.crop((200, 60, 1240, 80))).stddev[0]
    bottom = ImageStat.Stat(im.crop((200, 860, 1240, 880))).stddev[0]
    assert top > 60 and bottom < top / 4, (top, bottom)


BAR_IMAGE = (
    ".backdropImage.displayingBackdropImage"
    " { background: linear-gradient(90deg, #000 1150px, #fff 1150px 1170px, #000 1170px) !important; }"
)


def test_the_blur_lies_on_the_sharp_image(open_page, tmp_path):
    # A bright bar right of centre: the blurred copy keeps it where the sharp image has it.
    from PIL import Image

    page = open_page("movie", "desktop", "none", variant="bar")
    page.add_style_tag(content=BAR_IMAGE)
    page.wait_for_timeout(300)
    page.screenshot(path=str(tmp_path / "b.png"), style=ONLY_BACKDROP, animations="disabled")
    im = Image.open(tmp_path / "b.png").convert("L")

    def peak(y):
        cols = [sum(im.getpixel((x, row)) for row in range(y, y + 20)) for x in range(im.width)]
        return cols.index(max(cols))

    assert abs(peak(60) - peak(860)) <= 10, (peak(60), peak(860))


def test_the_blur_reaches_the_side_edges(open_page, tmp_path):
    # No sharp strip where the blurred copy meets the window's edges.
    from PIL import Image, ImageStat

    page = open_page("movie", "desktop", "none", variant="stripes")
    page.add_style_tag(content=STRIPES)
    page.wait_for_timeout(300)
    page.screenshot(path=str(tmp_path / "b.png"), style=ONLY_BACKDROP, animations="disabled")
    im = Image.open(tmp_path / "b.png").convert("L")
    top = ImageStat.Stat(im.crop((200, 60, 1240, 80))).stddev[0]
    edges = [ImageStat.Stat(im.crop(box)).stddev[0] for box in ((0, 860, 48, 880), (1392, 860, 1440, 880))]
    assert all(e < top / 4 for e in edges), (top, edges)


THUMB = """() => { const e = document.querySelector('.listItemImage.listItemImage-large'); const r = e.getBoundingClientRect();
  return [r.width / r.height, getComputedStyle(e).borderTopLeftRadius]; }"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_episode_thumbnails_are_16_9_with_rounded_corners(open_page, profile):
    ratio, radius = open_page("season", profile, "none").evaluate(THUMB)
    assert ratio == pytest.approx(16 / 9, abs=0.02) and radius == "8px", (ratio, radius)


def test_an_episode_row_takes_a_faint_fill_on_hover(open_page, color):
    page = open_page("season", "desktop", "none", variant="row-hover")
    row = page.locator(".listItem.listItem-largeImage >> visible=true").first
    row.hover()
    page.wait_for_timeout(300)
    # Fainter than Jellyfin's own 8% hover, and on the card corners.
    bg, radius = row.evaluate("(e) => [getComputedStyle(e).backgroundColor, getComputedStyle(e).borderTopLeftRadius]")
    r, g, b, a = color(bg)
    assert min(r, g, b) == 255 and 0.02 <= a <= 0.05 and radius == "12px", (bg, radius)
    page.mouse.move(0, 0)


def test_detail_buttons_stay_round_on_a_320px_phone(open_page):
    # A series page shows six buttons: they wrap rather than squeeze.
    page = open_page("show", "phone", "none", viewport=(320, 780))
    buttons = page.evaluate(BUTTONS)
    assert len(buttons) >= 5, buttons
    for b in buttons:
        assert b["w"] == pytest.approx(b["h"], abs=0.5) and b["right"] <= 320, b
    assert page.evaluate("document.documentElement.scrollWidth") <= 320


def test_play_brightens_on_hover(open_page, color):
    page = open_page("movie", "desktop", "none", variant="play-hover")
    play = page.locator(".mainDetailButtons > .btnPlay >> visible=true").first
    before = color(play.evaluate("(e) => getComputedStyle(e).backgroundColor"))
    play.hover()
    page.wait_for_timeout(400)
    after = color(play.evaluate("(e) => getComputedStyle(e).backgroundColor"))
    assert before[3] == pytest.approx(0.12, abs=0.01)
    assert after[:3] == (255, 36, 72) and after[3] == pytest.approx(0.22, abs=0.01), after
    page.mouse.move(0, 0)


# Jellyfin renders the overview as paragraphs inside a <bdi>, inside the clamped box.
PARAGRAPHS = "<bdi><p>" + PROSE + "</p><p>" + PROSE + "</p></bdi>"
CLAMP = """(html) => { const o = document.querySelector('.detailPagePrimaryContainer .overview');
  if (html) { o.innerHTML = html; o.classList.add('detail-clamp-text'); }
  const r = o.getBoundingClientRect(), lh = parseFloat(getComputedStyle(o).lineHeight), lines = [];
  const w = document.createTreeWalker(o, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) { const g = document.createRange(); g.selectNodeContents(n);
    for (const q of g.getClientRects()) lines.push([q.top - r.top, q.bottom - r.top]); }
  const shown = lines.filter(([t]) => t < r.height);
  return { h: r.height, lh, first: Math.min(...lines.map(([t]) => t)), partial: shown.filter(([t, b]) => b > r.height + 1).length,
           lines: new Set(shown.map(([t]) => Math.round(t / lh))).size }; }"""


@pytest.mark.parametrize("profile, lines", [("desktop", 6), ("phone", 12)])
def test_the_clamped_overview_shows_whole_lines_from_its_top(open_page, profile, lines):
    # Margins inside the clamped box left a gap above the text, and on Firefox for Windows a
    # half line under the ellipsis. The clamp now holds lines only.
    got = open_page("movie", profile, "none", variant="clamp").evaluate(CLAMP, PARAGRAPHS)
    assert got["first"] < got["lh"] / 2, got
    assert got["h"] == pytest.approx(lines * got["lh"], abs=1) and got["partial"] == 0, got


def test_the_unfolded_overview_keeps_its_paragraphs_and_its_place(open_page):
    page = open_page("movie", "desktop", "none", variant="unfold")
    clamped = page.evaluate(CLAMP, PARAGRAPHS)
    top = page.evaluate("() => document.querySelector('.detailPagePrimaryContainer .overview').getBoundingClientRect().top")
    page.evaluate("() => document.querySelector('.detailPagePrimaryContainer .overview').classList.remove('detail-clamp-text')")
    open_ = page.evaluate(CLAMP, None)
    gap = page.evaluate("""() => { const [a, b] = document.querySelectorAll('.detailPagePrimaryContainer .overview p');
      return b.getBoundingClientRect().top - a.getBoundingClientRect().bottom; }""")
    assert open_["first"] == pytest.approx(clamped["first"], abs=1) and open_["h"] > clamped["h"], (clamped, open_)
    assert page.evaluate(
        "() => document.querySelector('.detailPagePrimaryContainer .overview').getBoundingClientRect().top"
    ) == pytest.approx(top, abs=1)
    assert gap >= open_["lh"] / 2, gap


SHOW_MORE = """() => { const o = document.querySelector('.detailPagePrimaryContainer .overview');
  const b = document.querySelector('.detailPagePrimaryContainer .overview-expand'); b.classList.remove('hide');
  const t = o.getBoundingClientRect(), q = b.getBoundingClientRect(), cs = getComputedStyle(b);
  return { text_right: t.right, label_right: q.right - parseFloat(cs.paddingRight), text_bottom: t.bottom,
           label_top: q.top + parseFloat(cs.paddingTop) }; }"""


@pytest.mark.parametrize("profile, viewport", [("desktop", None), ("desktop", (2560, 1300)), ("phone", None)])
def test_show_more_sits_under_the_end_of_the_text(open_page, profile, viewport):
    got = open_page("movie", profile, "none", viewport=viewport, variant="show-more").evaluate(SHOW_MORE)
    assert got["label_right"] == pytest.approx(got["text_right"], abs=2), got
    assert 0 <= got["label_top"] - got["text_bottom"] <= 16, got


CAST = """() => { const c = document.querySelector('#castCollapsible .personCard'); if (!c) return null;
  const s = c.querySelector('.cardScalable'), r = s.getBoundingClientRect();
  const radius = (e) => getComputedStyle(e).borderTopLeftRadius;
  return { w: r.width, h: r.height, scalable: radius(s), image: radius(c.querySelector('.cardImageContainer')),
           ring: getComputedStyle(s, '::after').borderTopLeftRadius,
           place: getComputedStyle(c.querySelector('.cardImageContainer')).backgroundPositionY,
           // How far the menu button's centre sits from the circle's, in radii.
           menu: (() => { const m = c.querySelector('.cardOverlayButton'); if (!m) return 0; const q = m.getBoundingClientRect();
             const dx = q.left + q.width / 2 - r.left - r.width / 2, dy = q.top + q.height / 2 - r.top - r.height / 2;
             return Math.hypot(dx, dy) / (r.width / 2); })() }; }"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", ["movie", "show"])
def test_cast_and_crew_are_circles(open_page, profile, route):
    got = open_page(route, profile, "none").evaluate(CAST)
    if got is None:
        pytest.skip("no cast on this title")
    assert got["w"] == pytest.approx(got["h"], abs=1), got
    assert got["scalable"] == got["image"] == got["ring"] == "50%", got
    # Portraits keep the face: the crop leans to the top third.
    assert got["place"] == "25%", got
    assert got["menu"] < 0.95, got  # on the portrait, not in the empty corner
