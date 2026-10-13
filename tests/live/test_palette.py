"""One palette block restyles the whole skin: no colour is written out anywhere else."""

import pytest

from harness import checks

pytestmark = pytest.mark.live

# Every palette input moved off its default; the defaults must then be gone from the page.
SWAP = checks.SWAP_PALETTE
DEFAULTS = [(255, 36, 72), (25, 211, 197), (5, 6, 10), (9, 11, 18), (18, 20, 32), (246, 243, 240), (255, 255, 255), (0, 0, 0)]
# Jellyfin and its plugins paint plain white and black of their own; only the skin's
# distinctive colours tell a written-out value apart there.
OWN = DEFAULTS[:6]


@pytest.mark.parametrize(
    ("route", "profile"),
    [
        ("home", "desktop"),
        ("home", "phone"),
        ("movies", "desktop"),
        ("movie", "desktop"),
        ("movie", "phone"),
        ("search", "desktop"),
        ("usermenu", "desktop"),
        ("actionsheet", "desktop"),
        ("display", "desktop"),
    ],
)
def test_one_palette_block_restyles_every_page(open_page, route, profile):
    page = open_page(route, profile, "all", after=SWAP)
    assert checks.palette_hits(page, OWN) == {}
