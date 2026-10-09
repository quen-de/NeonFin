"""Checks a run makes on each captured page: live glass, Jellyfin's blue, text contrast."""

from __future__ import annotations

import functools
import pathlib

from PIL import Image

JS = pathlib.Path(__file__).resolve().parent / "js"

# Text that must stay readable over whatever is behind it, by route name; "*"
# applies to every route. Selectors of absent elements are simply skipped.
# Title pages put their text straight on the backdrop.
TITLE_TEXT = (
    ".detailRibbon .nameContainer > h1",
    ".detailRibbon .itemMiscInfo-primary > .mediaInfoItem",
    ".trackSelections .selectLabel",
    ".detailPagePrimaryContainer .overview",
    ".itemGenres",
    ".itemTags",
)
TEXT_TARGETS: dict[str, tuple[str, ...]] = {
    "*": (".MuiAppBar-root > .MuiToolbar-root:first-child .MuiButton-root",),
    "home": ("#slides-container .slide.active .plot", "#slides-container .slide.active .spec-line"),
    "movie": TITLE_TEXT,
    "show": TITLE_TEXT,
    "season": TITLE_TEXT,
    "usermenu": ("#app-user-menu .MuiMenuItem-root",),
    "actionsheet": (".actionSheet .actionSheetItemText", ".actionSheet .actionSheetItemAsideText"),
}


@functools.cache
def _js(name: str) -> str:
    return (JS / name).read_text()


def glass_elements(page) -> list[str]:
    return page.evaluate(_js("glass.js"))


def blue_hits(page) -> dict[str, int]:
    return page.evaluate(_js("blue.js"))


def relative_luminance(rgb) -> float:
    def channel(c: float) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb[:3]
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(a, b) -> float:
    hi, lo = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def blend(rgba, bg) -> tuple[float, float, float]:
    r, g, b, a = rgba
    return tuple(a * c + (1 - a) * k for c, k in zip((r, g, b), bg))


def brightest_decile(img: Image.Image, rect, dpr: float) -> tuple[int, int, int]:
    """The colour at the 90th luminance percentile inside rect (CSS pixels: left, top, right, bottom)."""
    box = img.crop(tuple(round(v * dpr) for v in rect))
    pixels = list(getattr(box, "get_flattened_data", box.getdata)())  # getdata is deprecated from Pillow 12
    if not pixels:
        raise ValueError(f"empty sample box {rect}")
    pixels.sort(key=relative_luminance)
    return pixels[min(len(pixels) - 1, int(0.9 * len(pixels)))]


def contrast_failures(page, route_name: str, shot_path) -> list[dict]:
    selectors = TEXT_TARGETS["*"] + TEXT_TARGETS.get(route_name, ())
    items = page.evaluate(_js("contrast.js"), list(selectors))
    if not items:
        return []
    hide = ", ".join(selectors) + " { color: transparent !important; text-shadow: none !important; }"
    # Icons beside the text (a rating's star) are not the background it sits on.
    hide += (
        ", ".join(f"{s} {icon}" for s in selectors for icon in ("img", "svg", ".material-icons")) + " { visibility: hidden !important; }"
    )
    # A critic rating paints its icon as its own background.
    hide += ".mediaInfoCriticRating { background-image: none !important; }"
    page.screenshot(path=str(shot_path), style=hide, animations="disabled")
    img = Image.open(shot_path).convert("RGB")
    dpr = page.evaluate("devicePixelRatio")
    failures = []
    for item in items:
        need = 3.0 if item["large"] else 4.5
        if item["color"] is None:
            failures.append({"label": item["label"], "text": item["text"], "ratio": None, "need": need, "colour": item["raw"]})
            continue
        bg = brightest_decile(img, item["rect"], dpr)
        ratio = contrast_ratio(blend(item["color"], bg), bg)
        if ratio < need:
            failures.append({"label": item["label"], "text": item["text"], "ratio": round(ratio, 2), "need": need})
    return failures
