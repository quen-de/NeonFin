"""Every colour a page paints moves with the palette, except the few kept on purpose."""

import pytest

from harness import checks

pytestmark = pytest.mark.live

# Pages whose every surface is drawn from the palette. Each task that recolours a surface adds
# the pages it shows on.
COLOUR_ROUTES = [
    ("movies", "desktop"),
    ("movies", "phone"),
    ("homeprefs", "desktop"),
    ("quickconnect", "desktop"),
    ("prefs", "desktop"),
    ("display", "desktop"),
    ("display", "phone"),
    ("playback", "desktop"),
    ("subtitles", "desktop"),
    ("profile", "desktop"),
]


@pytest.mark.parametrize(("route", "profile"), COLOUR_ROUTES)
def test_every_colour_moves_with_the_palette(open_page, route, profile):
    before = checks.paint(open_page(route, profile, "all"))
    after = checks.paint(open_page(route, profile, "all", after=checks.SWAP_PALETTE))
    assert checks.unmoved(before, after) == {}
