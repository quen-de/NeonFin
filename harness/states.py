"""Interactions that put a page into a state worth capturing."""

from __future__ import annotations

import json


def usermenu(page):
    page.locator("button[aria-label='User Menu']").click()


def select(page):
    page.locator(".MuiSelect-select").first.click()


def actionsheet(page):
    page.locator(".btnMoreCommands >> visible=true").first.click()


def tooltip(page):
    # Plugins (Jellyfin Enhanced) inject hidden header buttons; hover a visible MUI one.
    page.locator(".MuiAppBar-root .MuiIconButton-root[aria-label] >> visible=true").first.hover()


def osd(page):
    page.locator(".mainDetailButtons button[data-action='resume'], .mainDetailButtons button[data-action='play']").first.click()
    page.wait_for_function("() => { const v = document.querySelector('video'); return !!v && v.currentTime >= 10; }", timeout=90_000)
    # Pause on an exact position: the progress slider width follows it. The
    # OSD drops time updates under 700 ms apart by Date, which is frozen, so
    # let one second pass first or the slider keeps its first value.
    page.evaluate("""() => new Promise((resolve) => {
      const v = document.querySelector('video');
      v.pause();
      window.__harnessAdvanceClock(1000);
      v.addEventListener('seeked', resolve, { once: true });
      v.currentTime = 10;
    })""")
    page.mouse.move(200, 200)
    page.mouse.move(400, 400)  # wake the OSD


def api_path(path):
    """Match a server API path whatever its case: Jellyfin's client asks for users/public and
    users/authenticatebyname in lower case. `path` is lower case."""
    return lambda url: path in url.lower()


def dialog(page):
    actionsheet(page)
    page.locator(".actionSheet [data-id='addtoplaylist']").click()


# Made-up users for the sign-in picker, which a server can hide. The harness answers the
# request itself; the picker only appears if the answer was used.
PICKER_USERS = [
    {"Name": "Alex", "Id": "0" * 31 + "1", "HasPassword": True, "HasConfiguredPassword": True},
    {"Name": "Sam", "Id": "0" * 31 + "2", "HasPassword": False, "HasConfiguredPassword": False},
]


def picker(page):
    body = json.dumps(PICKER_USERS)
    page.route(api_path("/users/public"), lambda route: route.fulfill(status=200, content_type="application/json", body=body))
    page.reload()


def jepanel(page):
    # Jellyfin Enhanced opens its panel on "?"; its user menu entry is a translated label.
    page.keyboard.press("?")


STATES = {f.__name__: f for f in (usermenu, select, actionsheet, tooltip, osd, dialog, picker, jepanel)}
