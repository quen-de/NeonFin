import re

import pytest

pytestmark = pytest.mark.live

# The test server has no disabled or invalid field to open, so mark one the way MUI does, then
# read it once the field's transition has run.
READ = """() => { const cs = getComputedStyle(document.querySelector('.MuiFilledInput-root')); return [cs.backgroundColor, cs.boxShadow,
  getComputedStyle(document.documentElement).getPropertyValue('--jf-palette-error-main').trim()]; }"""


def mark(page, cls):
    page.evaluate("(cls) => document.querySelector('.MuiFilledInput-root').classList.add(cls)", cls)
    page.wait_for_timeout(500)
    return page.evaluate(READ)


def test_a_disabled_settings_field_looks_inactive(open_page, color):
    bg, _, _ = mark(open_page("display", "desktop", "none", variant="disabled-field"), "Mui-disabled")
    assert color(bg)[3] <= 0.04, bg


def test_an_invalid_settings_field_shows_the_theme_error_colour(open_page, color):
    _, shadow, error = mark(open_page("display", "desktop", "none", variant="error-field"), "Mui-error")
    rim = color(re.search(r"(?:rgba?|color)\([^)]*\)", shadow)[0])
    want = tuple(int(error[i : i + 2], 16) for i in (1, 3, 5)) if error else (244, 67, 54)
    assert rim[:3] == want, (shadow, error)
