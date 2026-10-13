"""Jellyfin Enhanced's own surfaces: its settings panel and its calendar take the palette."""

import pytest

from harness import checks, session
from harness.profiles import PROFILES, ROUTES

pytestmark = pytest.mark.live

ROUTE = {r.name: r for r in ROUTES}
INK_2 = (9, 11, 18)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_the_panel_is_solid(open_page, style, color, profile):
    panel = style(open_page("jepanel", profile, "all"), "#jellyfin-enhanced-panel", "backdrop-filter", "background-color")
    assert panel["backdrop-filter"] == "none" and color(panel["background-color"])[:3] == INK_2, panel


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_every_panel_tab_is_free_of_blue(open_page, profile):
    page = open_page("jepanel", profile, "all", variant="tabs")
    tabs = page.locator("#jellyfin-enhanced-panel .tab-button")
    assert tabs.count() > 1
    for i in range(tabs.count()):
        # On phones the tabs are a list whose pages cover it once open: click through the DOM.
        tabs.nth(i).dispatch_event("click")
        page.wait_for_timeout(300)
        assert checks.blue_hits(page) == {}, tabs.nth(i).inner_text()


def test_a_swapped_palette_reaches_the_panel(open_page, color):
    page = open_page("jepanel", "desktop", "all", after=checks.SWAP_PALETTE)
    bar = page.evaluate(
        "() => getComputedStyle(document.querySelector('#jellyfin-enhanced-panel .tab-button.active'), '::before').backgroundColor"
    )
    assert color(bar)[:3] == (0, 229, 255), bar


def test_the_panel_buttons_are_tinted_pills(open_page, style, color):
    page = open_page("jepanel", "desktop", "all")
    for sel in ("#releaseNotesBtn", "#clearTranslationCacheButton"):
        b = style(page, f"#jellyfin-enhanced-panel {sel}", "background-color", "border-top-left-radius")
        if b is None:
            continue
        assert color(b["background-color"])[3] <= 0.15 and b["border-top-left-radius"] == "999px", (sel, b)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_the_calendar_view_in_use_is_a_selected_pill(open_page, style, color, profile):
    b = style(open_page("calendar", profile, "all"), ".je-calendar-nav .je-calendar-view-btn.active", "background-color", "box-shadow")
    r, g, bl, a = color(b["background-color"])
    assert (r, g, bl) == (255, 36, 72) and 0.15 <= a <= 0.25 and "inset" in b["box-shadow"], b


def test_the_plugin_takes_the_palette_on_a_fresh_load(cfg, browser, skin_css):
    # The plugin picks a theme once, the first time it needs a colour, and keeps it: a palette
    # that lands after that never reaches it. A fresh page shows which one it picked.
    prof = PROFILES["desktop"]
    ctx, page = session.new_page(browser, prof, session.login_state(browser, cfg, prof), session.Override(skin_css))
    session.open_route(page, cfg, ROUTE["home"], cfg.volatile)
    picked = page.evaluate("() => window.JellyfinEnhanced?.themer?.activeTheme?.key ?? null")
    ctx.close()
    if picked is None:
        pytest.skip("this Jellyfin Enhanced build exposes no theme detection")
    assert picked == "jellyfish"
