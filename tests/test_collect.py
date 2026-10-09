import pytest
from playwright.sync_api import sync_playwright

from harness import collect, session
from harness.profiles import PROFILES


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as pw:
        b = session.launch(pw)
        ctx, p = session.new_page(b, PROFILES["desktop"], None, None)
        yield p
        b.close()


HTML = """<style>.card{backdrop-filter:blur(4px);color:rgb(1,2,3)}.x::before{content:'*'}
.gone{display:none}</style>
<div class=card>a</div><div class='x'>b</div><div class=gone>c</div>
<div id=slides><p>s</p></div>"""


def test_styles_keys_visible_elements_and_pseudo(page):
    page.set_content(HTML)
    s = collect.styles(page, ["#slides"])
    labels = {v["label"] for v in s.values()}
    assert "div.card" in labels and "div.x" in labels and "div.x::before" in labels
    assert not any("gone" in label for label in labels)
    assert not any(label == "p" for label in labels)  # inside a volatile subtree
    card = next(v for v in s.values() if v["label"] == "div.card")
    assert card["s"]["color"] == "rgb(1, 2, 3)"
    assert collect.backdrop_count(s) == 1


def test_styles_keys_are_stable_across_reloads(page):
    page.set_content(HTML)
    a = set(collect.styles(page, []))
    page.set_content(HTML)
    assert a == set(collect.styles(page, []))


def test_css_selectors_counts_rules_and_strips_dynamic_pseudo(page):
    page.set_content("<div class=a></div>")
    rules, sels = collect.css_selectors(page, ".a:hover{x:1}@media (min-width:1px){.b::after{y:2}}@keyframes k{from{}}")
    assert rules == 2
    assert sels == [".a", ".b"]


def test_matched_reports_only_rendered_hits(page):
    page.set_content("<div class=a></div><div class=b style=display:none></div>")
    assert collect.matched(page, [".a", ".b", ".c", "::bad("]) == [0]


def test_styles_keys_survive_portal_reordering(page):
    # MUI mounts body-level portals lazily, so their order varies between loads.
    a_html = "<div class=footer>f</div><div id=app-menu><ul><li>m</li></ul></div><div class=pop>p</div>"
    b_html = "<div class=pop>p</div><div id=app-menu><ul><li>m</li></ul></div><div class=footer>f</div>"
    page.set_content(a_html)
    a = {v["label"]: k for k, v in collect.styles(page, []).items()}
    page.set_content(b_html)
    b = {v["label"]: k for k, v in collect.styles(page, []).items()}
    assert a == b


def test_css_selectors_keep_focus_within_and_focus_visible_whole(page):
    page.set_content("<div class=card><a class=x></a></div>")
    _, sels = collect.css_selectors(page, ".card:focus-within .x{a:1}.x:focus-visible{b:2}")
    assert sels == [".card .x", ".x"]
