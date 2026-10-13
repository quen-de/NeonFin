"""The palette picker, opened as a file in the browser the harness uses."""

import re

import pytest
from playwright.sync_api import sync_playwright

import build
from harness import session


@pytest.fixture(scope="module")
def picker(tmp_path_factory):
    path = tmp_path_factory.mktemp("picker") / "palette.html"
    path.write_text(build.palette_page(), encoding="utf-8")
    with sync_playwright() as pw:
        b = session.launch(pw)
        page = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
        page.goto(path.as_uri())
        yield page
        b.close()


def choose(page, name):
    page.locator(f"[data-preset='{name}']").click()


def type_colour(page, token, value):
    field = page.locator(f"[data-token='{token}'] input[type=text]")
    field.fill(value)
    field.dispatch_event("change")


def output(page):
    return page.locator("#output").input_value()


def test_every_preset_file_is_offered(picker):
    offered = picker.locator("[data-preset]").evaluate_all("(bs) => bs.map((b) => b.dataset.preset)")
    assert offered == list(build.palette_presets())


def test_the_default_palette_has_nothing_to_paste_and_reads_well(picker):
    choose(picker, "Crimson")
    assert "nothing to paste" in output(picker)
    assert picker.locator(".contrast-row").count() == 8
    assert picker.locator(".contrast-row.is-failing").count() == 0 and picker.locator("#warning").is_hidden()


@pytest.mark.parametrize("name", ["Cyan neon", "Amber", "Violet", "Acid green"])
def test_every_preset_reads_well(picker, name):
    choose(picker, name)
    assert picker.locator(".contrast-row.is-failing .contrast-label").all_inner_texts() == []


def test_a_preset_outputs_only_the_tokens_it_changes(picker):
    choose(picker, "Cyan neon")
    out = output(picker)
    assert out.startswith("/* NeonFin palette. Paste after the skin in Custom CSS. */\n:root {")
    assert "--nf-neon: #00e5ff;" in out and "--nf-on-neon: #000000;" in out and "--nf-paper" not in out
    assert picker.locator("[data-preset='Cyan neon']").get_attribute("aria-pressed") == "true"


def test_editing_one_colour_outputs_that_token_alone(picker):
    choose(picker, "Crimson")
    type_colour(picker, "neon", "0F8")
    assert re.findall(r"--nf-[\w-]+: [^;]+;", output(picker)) == ["--nf-neon: #00ff88;"]


def test_a_value_that_is_not_a_colour_is_ignored(picker):
    choose(picker, "Crimson")
    type_colour(picker, "ink", "dark")
    assert "nothing to paste" in output(picker)
    assert picker.locator("[data-token='ink'] input[type=text]").input_value() == "#05060a"


def test_the_preview_draws_in_the_palette(picker):
    choose(picker, "Violet")
    got = picker.evaluate("() => getComputedStyle(document.querySelector('.pv-progress > span')).backgroundColor")
    assert got == "rgb(168, 85, 255)"


def test_an_unreadable_palette_is_flagged_before_copying(picker):
    choose(picker, "Crimson")
    type_colour(picker, "ink", "#f0f0f0")
    assert "Text on the page" in picker.locator(".contrast-row.is-failing .contrast-label").all_inner_texts()
    assert picker.locator("#warning").is_visible()


def test_the_page_fits_a_phone(picker):
    picker.set_viewport_size({"width": 360, "height": 800})
    try:
        assert picker.evaluate("() => document.documentElement.scrollWidth") <= 360
    finally:
        picker.set_viewport_size({"width": 1280, "height": 900})


def test_the_whole_block_shows_on_a_phone(picker):
    # Nine changed colours are twelve lines: the field grows to them instead of scrolling.
    picker.set_viewport_size({"width": 390, "height": 844})
    try:
        choose(picker, "Crimson")
        for token, value in (("neon", "#00e5ff"), ("teal", "#ff3dbb"), ("ink", "#04070a"), ("ink-2", "#08101a"),
                             ("chrome", "#0f1a24"), ("paper", "#eeeeee"), ("light", "#fafafa"), ("shade", "#010101"),
                             ("on-neon", "#000000")):
            type_colour(picker, token, value)
        assert picker.evaluate("() => { const o = document.getElementById('output'); return o.scrollHeight <= o.clientHeight; }")
    finally:
        picker.set_viewport_size({"width": 1280, "height": 900})
