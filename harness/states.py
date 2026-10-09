"""Interactions that put a page into a state worth capturing."""

from __future__ import annotations


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


STATES = {f.__name__: f for f in (usermenu, select, actionsheet, tooltip, osd)}
