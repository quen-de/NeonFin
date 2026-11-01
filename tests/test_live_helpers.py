"""The live tests' own helpers, on plain pages: no server needed."""

import importlib.util
import pathlib
import time

import pytest
from playwright.sync_api import sync_playwright

from harness import session
from harness.profiles import PROFILES

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("live_conftest", ROOT / "tests" / "live" / "conftest.py")
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as pw:
        b = session.launch(pw)
        ctx, p = session.new_page(b, PROFILES["desktop"], None, None)
        yield p
        b.close()


def test_a_style_is_read_once_the_elements_transition_ends(page):
    # A plugin's dot fades to the accent as its slide comes up: read mid-fade, it is neither colour.
    page.set_content(
        "<style>#dot { background-color: rgb(255 255 255 / 0.28); transition: background-color 0.5s; }"
        " #dot.active { background-color: rgb(255, 36, 72); }</style><div id=dot></div>"
    )
    page.evaluate("() => { getComputedStyle(dot).backgroundColor; dot.classList.add('active'); }")
    assert page.evaluate(live.STYLE_JS, ["#dot", ["background-color"], None])["background-color"] == "rgb(255, 36, 72)"


def test_a_style_read_does_not_wait_on_an_endless_animation(page):
    page.set_content("<style>@keyframes pulse { to { opacity: 0.5; } } #glow { animation: pulse 1s infinite; }</style><div id=glow></div>")
    start = time.monotonic()
    assert page.evaluate(live.STYLE_JS, ["#glow", ["animation-name"], None])["animation-name"] == "pulse"
    assert time.monotonic() - start < 1
