"""Each preset, pasted after the skin, recolours every page and keeps it readable."""

import pytest

import build
from harness import checks

pytestmark = pytest.mark.live

PRESETS = sorted(p.stem for p in (build.ROOT / "palettes").glob("*.css"))
# The defaults a preset may replace, as painted; white and black are Jellyfin's own too.
DEFAULTS = {"neon": (255, 36, 72), "teal": (25, 211, 197), "ink": (5, 6, 10), "ink-2": (9, 11, 18), "chrome": (18, 20, 32)}


def preset(name: str) -> str:
    return "\n" + (build.ROOT / "palettes" / f"{name}.css").read_text()


def rgb(value: str) -> tuple[int, int, int]:
    h = build.hex6(value)
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


@pytest.mark.parametrize("name", PRESETS)
@pytest.mark.parametrize(
    ("route", "profile", "plugin_state"),
    [
        ("home", "desktop", "all"),
        ("home", "phone", "all"),
        ("home", "desktop", "none"),
        ("movie", "desktop", "all"),
        ("login", "desktop", "none"),
        ("display", "desktop", "all"),
    ],
)
def test_each_preset_keeps_text_readable(open_page, tmp_path, name, route, profile, plugin_state):
    page = open_page(route, profile, plugin_state, after=preset(name))
    assert checks.contrast_failures(page, route, tmp_path / "c.png") == []


@pytest.mark.parametrize("name", PRESETS)
def test_each_preset_replaces_the_colours_it_changes(open_page, name):
    tokens = build.preset_tokens(preset(name))
    page = open_page("home", "desktop", "all", after=preset(name))
    assert checks.palette_hits(page, [rgb(tokens["neon"])]) != {}
    # A near-black ink a step from the default is the same paint to the check: only defaults
    # the preset moves further than its tolerance are looked for.
    moved = [DEFAULTS[t] for t in tokens if t in DEFAULTS and max(abs(a - b) for a, b in zip(rgb(tokens[t]), DEFAULTS[t])) > 2]
    assert checks.palette_hits(page, moved) == {}


LABEL = """() => { const e = document.createElement('div'); e.className = 'countIndicator'; e.textContent = '3';
  document.body.append(e); const cs = getComputedStyle(e), out = [cs.color, cs.backgroundColor]; e.remove(); return out; }"""


@pytest.mark.parametrize("name", ["crimson", *PRESETS])
def test_labels_on_the_accent_stay_readable(open_page, color, name):
    page = open_page("home", "desktop", "all", after="" if name == "crimson" else preset(name))
    fg, bg = (color(v) for v in page.evaluate(LABEL))
    assert checks.contrast_ratio(fg, bg) >= 3, (name, fg, bg)
