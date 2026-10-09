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
    page.wait_for_timeout(300)
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
