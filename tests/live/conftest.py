"""Live tests: the local build injected into real pages of a Jellyfin server.

They need the env vars and harness/config.local.json the harness uses (see
DEVELOPMENT.md) and are skipped without them. Run them with `-m live`. Pages are
opened once per argument set and shared, so tests that hover or click ask for
their own variant.
"""

import re

import pytest
from playwright.sync_api import sync_playwright

import build
from harness import config, plugins, session
from harness.profiles import PROFILES, ROUTES

ROUTE = {r.name: r for r in ROUTES}
STYLE_JS = """([sel, props, pseudo]) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const cs = getComputedStyle(el, pseudo);
  const out = {};
  for (const p of props) out[p] = cs.getPropertyValue(p);
  const r = el.getBoundingClientRect();
  out.rect = [r.left, r.top, r.width, r.height];
  return out;
}"""


def color_of(value: str) -> tuple[float, float, float, float]:
    m = re.match(r"rgba?\(([\d.]+), ([\d.]+), ([\d.]+)(?:, ([\d.]+))?\)", value)
    if m:
        return (float(m[1]), float(m[2]), float(m[3]), float(m[4] or 1))
    m = re.match(r"color\(srgb ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)(?: / ([\d.]+))?\)", value)
    if m:
        return (round(float(m[1]) * 255), round(float(m[2]) * 255), round(float(m[3]) * 255), float(m[4] or 1))
    raise ValueError(f"not a colour: {value!r}")


@pytest.fixture(scope="session")
def cfg():
    try:
        return config.load()
    except config.ConfigError as e:
        pytest.skip(str(e))


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as pw:
        b = session.launch(pw)
        yield b
        b.close()


@pytest.fixture(scope="session")
def skin_css():
    return build.build()


@pytest.fixture(scope="session")
def open_page(cfg, browser, skin_css):
    states, opened = {}, {}

    def get(route="home", profile="desktop", plugin_state="all", media=(), viewport=None, variant=""):
        key = (route, profile, plugin_state, tuple(media), viewport, variant)
        if key not in opened:
            prof = PROFILES[profile]
            if profile not in states:
                states[profile] = session.login_state(browser, cfg, prof)
            ctx, page = session.new_page(browser, prof, states[profile], session.Override(skin_css), plugins.parse_state(plugin_state))
            if media:
                cdp = ctx.new_cdp_session(page)
                cdp.send("Emulation.setEmulatedMedia", {"features": [{"name": n, "value": v} for n, v in media]})
            if viewport:
                page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
            session.open_route(page, cfg, ROUTE[route], cfg.volatile)
            opened[key] = (ctx, page)
        return opened[key][1]

    yield get
    for ctx, _ in opened.values():
        ctx.close()


@pytest.fixture(scope="session")
def style():
    def get(page, selector, *props, pseudo=None):
        return page.evaluate(STYLE_JS, [selector, list(props), pseudo])

    return get


@pytest.fixture(scope="session")
def color():
    return color_of


def rows_of(path) -> list[tuple[float, float, float]]:
    """Mean colour of each pixel row of an image."""
    from PIL import Image

    im = Image.open(path).convert("RGB")
    w, h = im.size
    data = list(getattr(im, "get_flattened_data", im.getdata)())
    return [tuple(sum(p[i] for p in data[y * w : (y + 1) * w]) / w for i in range(3)) for y in range(h)]


@pytest.fixture(scope="session")
def rows():
    return rows_of
