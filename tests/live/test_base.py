import pytest

pytestmark = pytest.mark.live


@pytest.mark.parametrize("plugin_state", ["all", "none"])
def test_page_ground_type_and_browser_surfaces(open_page, style, color, plugin_state):
    page = open_page("home", "desktop", plugin_state)
    html = style(page, "html", "background-color", "caret-color", "scrollbar-color")
    assert color(html["background-color"]) == (5, 6, 10, 1.0)
    assert color(html["caret-color"]) == (255, 36, 72, 1.0)
    assert html["scrollbar-color"].startswith("rgba(255, 255, 255, 0.18)")
    assert style(page, "body", "font-family")["font-family"].startswith("-apple-system")


@pytest.mark.parametrize("plugin_state", ["all", "none"])
def test_city_light_behind_the_page(open_page, style, plugin_state):
    page = open_page("home", "desktop", plugin_state)
    bg = style(page, ".backgroundContainer", "background-image")["background-image"]
    assert bg.count("radial-gradient") == 3 and "linear-gradient" in bg


def test_keyboard_focus_draws_the_crimson_ring(open_page, color):
    page = open_page("home", "desktop", "none", variant="keyboard")
    page.keyboard.press("Tab")
    ring = page.evaluate("""() => { const cs = getComputedStyle(document.activeElement);
      return [document.activeElement.tagName, cs.outlineStyle, cs.outlineWidth, cs.outlineColor]; }""")
    assert ring[0] != "BODY"
    assert ring[1:3] == ["solid", "2px"] and color(ring[3])[:3] == (255, 36, 72)
