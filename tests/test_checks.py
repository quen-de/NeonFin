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
