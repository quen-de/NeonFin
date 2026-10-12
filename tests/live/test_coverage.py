"""The harness reaches every page milestone 2 styles, and the contrast check reads their text."""

import pytest

from harness import checks

pytestmark = pytest.mark.live

VISIBLE = "(sels) => sels.filter((s) => [...document.querySelectorAll(s)].some((e) => e.offsetParent && e.innerText.trim()))"


def test_an_episode_page_opens_under_its_series_name(open_page):
    page = open_page("episode", "desktop", "none")
    assert page.locator(".detailRibbon .nameContainer > h1.parentName").count() == 1


def test_a_search_that_matches_nothing_says_so(open_page):
    assert open_page("noresults", "desktop", "none").locator("#searchPage .noItemsMessage").is_visible()


def test_contrast_reads_the_title_page_links_and_credits(open_page):
    found = open_page("movie", "desktop", "none").evaluate(VISIBLE, list(checks.TEXT_TARGETS["movie"]))
    for sel in (".itemTags a", ".itemExternalLinks a", ".detailsGroupItem .label", ".detailsGroupItem a"):
        assert sel in found, sel


@pytest.mark.parametrize("route", ["movies", "series"])
def test_contrast_reads_the_library_toolbar_and_rail(open_page, route):
    found = open_page(route, "desktop", "none").evaluate(VISIBLE, list(checks.TEXT_TARGETS.get(route, ())))
    assert len(found) == 3, found


def test_the_dialog_route_opens_add_to_playlist(open_page):
    page = open_page("dialog", "desktop", "none")
    assert page.locator(".formDialog .formDialogHeaderTitle").is_visible()
    assert page.locator(".formDialog .button-submit").count() == 1


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_the_picker_route_shows_two_made_up_users(open_page, profile):
    page = open_page("picker", profile, "none")
    assert page.locator("#divUsers .card .cardText").all_inner_texts() == ["Alex", "Sam"]


def test_contrast_reads_the_player_text(osd):
    found = osd("desktop").evaluate(VISIBLE, list(checks.TEXT_TARGETS.get("osd", ())))
    for sel in (".videoOsdBottom .osdPositionText", ".videoOsdBottom .osdDurationText", ".osdHeader .videoOsd-appBar .MuiTypography-root"):
        assert sel in found, sel
