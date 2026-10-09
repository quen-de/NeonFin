"""Page-side collectors: computed styles, CSS parsing, selector matching."""

from __future__ import annotations

import functools
import pathlib

JS = pathlib.Path(__file__).resolve().parent / "js"

PROPS = (
    "display",
    "position",
    "top",
    "right",
    "bottom",
    "left",
    "z-index",
    "width",
    "height",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "color",
    "background-color",
    "background-image",
    "opacity",
    "visibility",
    "backdrop-filter",
    "filter",
    "box-shadow",
    "transform",
    "border-top-width",
    "border-top-style",
    "border-top-color",
    "border-right-color",
    "border-bottom-width",
    "border-bottom-color",
    "border-left-color",
    "border-top-left-radius",
    "border-bottom-right-radius",
    "font-family",
    "font-size",
    "font-weight",
    "line-height",
    "letter-spacing",
    "text-align",
    "overflow-x",
    "overflow-y",
    "flex-direction",
    "justify-content",
    "align-items",
    "gap",
    "outline-style",
    "cursor",
)


@functools.cache
def _js(name: str) -> str:
    return (JS / name).read_text()


def styles(page, volatile) -> dict:
    return page.evaluate(_js("styles.js"), {"props": list(PROPS), "volatile": list(volatile)})


def css_selectors(page, css_text: str) -> tuple[int, list[str]]:
    res = page.evaluate(_js("parse_css.js"), css_text)
    return res["rules"], res["selectors"]


def matched(page, selectors: list[str]) -> list[int]:
    return page.evaluate(_js("matched.js"), selectors)


def backdrop_count(snapshot: dict) -> int:
    return sum(1 for v in snapshot.values() if v["s"].get("backdrop-filter", "none") not in ("none", ""))
