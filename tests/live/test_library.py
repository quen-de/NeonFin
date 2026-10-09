import pytest

from harness import checks

pytestmark = pytest.mark.live

GROUP = """() => [...document.querySelectorAll('.MuiToolbar-root .MuiButtonGroup-contained > .MuiButton-contained')]
  .filter((b) => b.offsetParent).map((b) => { const cs = getComputedStyle(b), r = b.getBoundingClientRect();
    return { text: b.innerText.trim(), w: r.width, h: r.height, left: r.left, right: r.right,
             radius: parseFloat(cs.borderTopLeftRadius), shadow: cs.boxShadow, bg: cs.backgroundColor }; })"""


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", ["movies", "series"])
def test_no_jellyfin_blue_on_libraries(open_page, profile, route):
    assert checks.blue_hits(open_page(route, profile, "none")) == {}


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_play_all_is_the_neon_tube_and_shuffle_a_round_tinted_button(open_page, color, profile):
    buttons = open_page("movies", profile, "none").evaluate(GROUP)
    assert len(buttons) >= 2, buttons
    play, rest = buttons[0], buttons[1:]
    assert play["shadow"].count("inset") == 2 and color(play["bg"])[:3] == (255, 36, 72), play
    assert play["radius"] >= play["h"] / 2, play
    for b in rest:
        r, g, bl, a = color(b["bg"])
        assert b["w"] == pytest.approx(b["h"], abs=0.5) and b["radius"] >= b["h"] / 2, b
        assert min(r, g, bl) == 255 and 0.04 <= a <= 0.12 and "inset" in b["shadow"], b
    assert all(nxt["left"] - cur["right"] >= 6 for cur, nxt in zip(buttons, buttons[1:])), buttons


def test_the_filter_dot_is_crimson(open_page, style, color):
    dot = style(open_page("movies", "desktop", "none"), ".MuiToolbar-root .MuiBadge-dot", "background-color")
    assert color(dot["background-color"])[:3] == (255, 36, 72)


def test_the_item_count_is_a_quiet_tinted_chip(open_page, style, color):
    chip = style(open_page("movies", "desktop", "none"), ".MuiToolbar-root .MuiChip-filled", "background-color", "color")
    r, g, b, a = color(chip["background-color"])
    assert min(r, g, b) == 255 and a <= 0.1, chip
