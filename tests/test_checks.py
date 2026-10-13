import pytest
from PIL import Image
from playwright.sync_api import sync_playwright

from harness import checks, session
from harness.profiles import PROFILES


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as pw:
        b = session.launch(pw)
        ctx, p = session.new_page(b, PROFILES["desktop"], None, None)
        yield p
        b.close()


def test_glass_counts_visible_blur_including_pseudo_elements(page):
    page.set_content("""<style>
      .g { -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); width: 50px; height: 50px; }
      .p::before { content: ''; display: block; width: 10px; height: 10px; backdrop-filter: blur(2px); }
      .off { position: absolute; top: 5000px; } .gone { display: none; }
    </style><div class=g id=a></div><div class=p></div><div class='g off'></div><div class='g gone'></div>""")
    assert checks.glass_elements(page) == ["div#a.g", "div.p::before"]


def test_blue_hits_count_only_paint_a_user_sees(page):
    page.set_content("""<p style="color:#00a4dc">blue text</p>
      <div style="background:#00a4dc;width:9px;height:9px"></div>
      <div style="border-top:0 solid #00a4dc;width:9px;height:9px"></div>
      <div style="background:#19d3c5;width:9px;height:9px"></div>
      <div style="background:color-mix(in srgb, #00a4dc 50%, transparent);width:9px;height:9px"></div>""")
    assert checks.blue_hits(page) == {"p color": 1, "div background": 2}


def test_contrast_ratio_matches_wcag():
    assert checks.contrast_ratio((255, 255, 255), (0, 0, 0)) == pytest.approx(21.0)
    assert checks.contrast_ratio((118, 118, 118), (255, 255, 255)) == pytest.approx(4.54, abs=0.01)


def test_blend_applies_alpha():
    assert checks.blend((255, 255, 255, 0.5), (0, 0, 0)) == (127.5, 127.5, 127.5)


def test_brightest_decile_ignores_a_few_hot_pixels():
    img = Image.new("RGB", (100, 10), (0, 0, 0))
    for x in range(5):
        img.putpixel((x, 0), (255, 255, 255))
    assert checks.brightest_decile(img, (0, 0, 100, 10), 1) == (0, 0, 0)
    img.paste((255, 255, 255), (0, 0, 100, 2))
    assert checks.brightest_decile(img, (0, 0, 100, 10), 1) == (255, 255, 255)


def test_contrast_failures_end_to_end(page, tmp_path, monkeypatch):
    monkeypatch.setitem(checks.TEXT_TARGETS, "t", (".bad", ".good"))
    page.set_content("""<body style="margin:0;background:#fff">
      <p class=good style="color:#000;margin:0;font-size:16px">Readable</p>
      <p class=bad style="color:#bbb;margin:0;font-size:16px">Faint</p></body>""")
    fails = checks.contrast_failures(page, "t", tmp_path / "c.png")
    assert [f["text"] for f in fails] == ["Faint"]


def test_contrast_flags_colours_it_cannot_read(page, tmp_path, monkeypatch):
    # An unreadable colour must fail, not pass as white.
    monkeypatch.setitem(checks.TEXT_TARGETS, "t", (".odd",))
    page.set_content("""<body style="margin:0;background:#000">
      <p class=odd style="color:lab(95% 0 0);margin:0;font-size:16px">Odd</p></body>""")
    fails = checks.contrast_failures(page, "t", tmp_path / "c.png")
    assert [(f["text"], f["ratio"]) for f in fails] == [("Odd", None)]


def test_contrast_ignores_icons_inside_the_text(page, tmp_path, monkeypatch):
    # A yellow star beside a rating is not the background the digits sit on.
    monkeypatch.setitem(checks.TEXT_TARGETS, "t", (".rating",))
    page.set_content("""<body style="margin:0;background:#000">
      <p class=rating style="display:inline-block;color:#fff;margin:0;font-size:16px"><span class=material-icons
        style="display:inline-block;width:16px;height:16px;background:#ffd400"></span><svg width=16 height=16>
        <rect width=16 height=16 fill="#ffd400"/></svg>7.1</p></body>""")
    assert checks.contrast_failures(page, "t", tmp_path / "c.png") == []


def test_contrast_reads_colours_at_rest_not_mid_transition(page, tmp_path, monkeypatch):
    # A colour caught mid-transition reads as oklab(), which the check cannot judge.
    monkeypatch.setitem(checks.TEXT_TARGETS, "t", (".fading",))
    page.set_content("""<body style="margin:0;background:#000">
      <p class=fading style="color:color(srgb 1 1 1 / 0.2);transition:color 10s;margin:0;font-size:16px">Fading</p></body>""")
    page.evaluate("""() => { const p = document.querySelector('.fading'); getComputedStyle(p).color;
      p.style.color = 'color(srgb 1 1 1 / 0.9)'; }""")
    assert checks.contrast_failures(page, "t", tmp_path / "c.png") == []


def test_blue_hits_read_colours_at_rest(page):
    page.set_content("<div id=d style='width:9px;height:9px;background:#000;transition:background-color 10s'></div>")
    page.evaluate("() => { const d = document.getElementById('d'); getComputedStyle(d).backgroundColor; d.style.backgroundColor = '#00a4dc'; }")
    assert checks.blue_hits(page) == {"div#d background": 1}


def test_checks_survive_a_transition_that_cannot_finish(page, tmp_path, monkeypatch):
    # finish() throws on a transition with no end in sight; the check reads what is there.
    monkeypatch.setitem(checks.TEXT_TARGETS, "t", (".stuck",))
    page.set_content("""<body style="margin:0;background:#000">
      <p class=stuck style="color:#fff;transition:color 10s;margin:0;font-size:16px">Stuck</p></body>""")
    page.evaluate("""() => { const p = document.querySelector('.stuck'); getComputedStyle(p).color;
      p.style.color = '#eee'; p.getAnimations()[0].playbackRate = 0; }""")
    checks.contrast_failures(page, "t", tmp_path / "c.png")  # must not raise
    checks.blue_hits(page)


def test_paint_reads_text_colour_only_where_text_is_drawn(page):
    page.set_content("""<div id=a style="color:rgb(1, 2, 3);width:9px;height:9px"></div>
      <p id=b style="color:rgb(1, 2, 3)">text</p><span class=material-icons style="color:rgb(4, 5, 6)">star</span>
      <div id=z style="width:0;height:0;background:rgb(7, 8, 9)"></div>""")
    got = checks.paint(page)
    assert "body > div#a color" not in got and got["body > p#b color"] == ["rgb(1, 2, 3)"]
    assert got["body > span.material-icons[star] color"] == ["rgb(4, 5, 6)"]
    assert not any("rgb(7, 8, 9)" in v for vs in got.values() for v in vs)


def test_unmoved_keeps_only_colours_the_swap_left_in_place():
    before = {
        "div.x bg": ["rgb(32, 32, 32)"],
        "div.y bg": ["rgb(255, 36, 72)"],
        "div.z bg": ["rgba(255, 255, 255, 0.5)"],
        "div.v bg": ["rgba(40, 40, 40, 0.1)"],
        "div.c bg": ["rgba(0, 0, 0, 0)"],
        "div > span.material-icons[star] color": ["rgb(242, 176, 30)"],
    }
    after = {**before, "div.y bg": ["rgb(0, 229, 255)"]}
    assert checks.unmoved(before, after) == {"div.x bg": ["rgb(32, 32, 32)"]}


@pytest.mark.parametrize(
    ("key", "on_purpose"),
    [
        ("div.star-rating-container > span.material-icons.community-rating-star.star color", True),
        ("a.itemAction > span.material-icons[star] color", True),
        ("div.jellyseerr-rating > svg fill", True),
        ("svg > g#layer1 fill", True),
        ("g#layer1 > path fill", True),
        ("div.je-calendar-legend-item > span.je-msym-rounded color", True),
        ("div.je-calendar-agenda-indicators > button.je-calendar-play-btn bg", True),
        ("span.MuiCheckbox-root > svg.MuiSvgIcon-root fill", False),
        ("svg.MuiSvgIcon-root > path fill", False),
        ("div.MuiButton-startIcon > svg bg", False),
        ("div > h3 color", False),
    ],
)
def test_only_stars_artwork_and_calendar_categories_keep_their_colours(key, on_purpose):
    assert checks.fixed_on_purpose(key) is on_purpose
