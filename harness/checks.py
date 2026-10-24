"""Checks a run makes on each captured page: live glass, Jellyfin's blue, text contrast."""

from __future__ import annotations

import functools
import pathlib
import re

from PIL import Image

JS = pathlib.Path(__file__).resolve().parent / "js"

# Text that must stay readable over whatever is behind it, by route name; "*"
# applies to every route. Selectors of absent elements are simply skipped.
# Title pages put their text straight on the backdrop.
TITLE_TEXT = (
    ".detailRibbon .nameContainer > h1",
    ".detailRibbon .nameContainer > h3",
    ".detailRibbon .itemMiscInfo-primary > .mediaInfoItem",
    ".trackSelections .selectLabel",
    ".tagline",
    ".detailPagePrimaryContainer .overview",
    ".itemGenres",
    ".itemTags",
    ".itemTags a",
    ".itemExternalLinks a",
    ".detailsGroupItem .label",
    ".detailsGroupItem a",
)
# Library pages: the header's second row and the A to Z rail sit over the poster grid.
LIBRARY_BAR = ".MuiAppBar-root > .MuiToolbar-root + .MuiToolbar-root"
LIBRARY_TEXT = (
    f"{LIBRARY_BAR} .MuiTypography-root",
    f"{LIBRARY_BAR} .MuiChip-label",
    ".alphaPicker-fixed-right .MuiToggleButton-root",
)
# Sign-in: the panel's text over the splash screen or the city light.
SIGN_IN_TEXT = (
    "#loginPage h1",
    "#loginPage .inputLabel",
    "#loginPage .checkboxLabel",
    "#loginPage .raised",
    "#loginPage .loginDisclaimer",
)
# Settings pages: headings, labels and the help under each field, on the page ground.
SETTINGS_TEXT = (
    ".userPreferencesPage .sectionTitle",
    ".userPreferencesPage .MuiTypography-h2",
    ".userPreferencesPage .inputLabel",
    ".userPreferencesPage .checkboxLabel",
    ".userPreferencesPage .fieldDescription",
    ".userPreferencesPage .listItemBodyText",
)
TEXT_TARGETS: dict[str, tuple[str, ...]] = {
    "*": (".MuiAppBar-root > .MuiToolbar-root:first-child .MuiButton-root",),
    "home": tuple(f"#slides-container .slide.active {s}" for s in (".plot", ".misc-info", ".genre")),
    "movies": LIBRARY_TEXT,
    "series": LIBRARY_TEXT,
    "movie": TITLE_TEXT,
    "show": TITLE_TEXT,
    "season": TITLE_TEXT,
    "episode": TITLE_TEXT,
    "noresults": ("#searchPage .noItemsMessage",),
    "suggestions": ("#searchPage .searchSuggestionsList .button-link",),
    "usermenu": ("#app-user-menu .MuiMenuItem-root",),
    "actionsheet": (".actionSheet .actionSheetItemText", ".actionSheet .actionSheetItemAsideText"),
    "login": SIGN_IN_TEXT,
    "picker": SIGN_IN_TEXT + ("#divUsers .cardText",),
    # The player: time, remaining and title over the video.
    "osd": (
        ".videoOsdBottom .osdPositionText",
        ".videoOsdBottom .osdDurationText",
        ".videoOsdBottom .endsAtText",
        ".osdHeader .videoOsd-appBar .MuiTypography-root",
    ),
    "prefs": SETTINGS_TEXT,
    "display": SETTINGS_TEXT,
    "playback": SETTINGS_TEXT,
    "subtitles": SETTINGS_TEXT,
    "homeprefs": SETTINGS_TEXT,
    "profile": SETTINGS_TEXT,
    "quickconnect": SETTINGS_TEXT,
    "calendar": (".je-calendar-nav .je-calendar-view-btn", ".je-calendar-legend-item"),
    "jepanel": ("#jellyfin-enhanced-panel h3", "#jellyfin-enhanced-panel .tab-button"),
}


@functools.cache
def _js(name: str) -> str:
    return (JS / name).read_text()


def at_rest(page) -> None:
    page.evaluate(_js("at_rest.js"))


def glass_elements(page) -> list[str]:
    return page.evaluate(_js("glass.js"))


def see_through(default: dict, reduced: dict) -> list[str]:
    """Surfaces that are glass by default and still show the page through once the system asks
    for less transparency: blurred, filled with anything less than opaque, or faded. Both are
    collect.styles snapshots of the same route. A surface drawn at opacity 0 or hidden, such
    as a closed menu MUI keeps mounted, shows nothing at all."""
    out = []
    for key, v in default.items():
        if v["s"].get("backdrop-filter", "none") in ("none", "") or key not in reduced:
            continue
        s = reduced[key]["s"]
        if s.get("visibility") == "hidden" or float(s.get("opacity") or 1) == 0:
            continue
        fill = colour_values(s.get("background-color", ""))
        if s.get("backdrop-filter", "none") not in ("none", "") or not fill or fill[0][3] < 1 or float(s.get("opacity") or 1) < 1:
            out.append(reduced[key]["label"])
    return sorted(out)


def blue_hits(page) -> dict[str, int]:
    at_rest(page)
    return page.evaluate(_js("blue.js"))


def palette_hits(page, colours) -> dict[str, int]:
    """Paint still in any of these (r, g, b) colours, by element and property."""
    at_rest(page)
    return page.evaluate(_js("palette.js"), [list(c) for c in colours])


# Every palette input moved off its default. Run after the skin, a colour that stays put was
# written out somewhere instead of taken from the palette.
SWAP_PALETTE = """:root { --nf-neon: #00e5ff; --nf-teal: #ffb000; --nf-ink: #140a1e; --nf-ink-2: #1a0f26;
  --nf-chrome: #2a1838; --nf-paper: #e6f2ff; --nf-light: #fff8e0; --nf-shade: #100008; --nf-on-neon: #201000; }"""
COLOUR_VALUE = re.compile(
    r"rgba?\(([\d.]+), ([\d.]+), ([\d.]+)(?:, ([\d.]+))?\)|color\(srgb ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)(?: / ([\d.]+))?\)"
)
# Colours the palette is not meant to move: rating stars, artwork drawn in SVG (studio and
# rating logos), and the categories Jellyfin Enhanced's calendar codes by colour. Icons MUI
# draws in its theme colour are not artwork.
ON_PURPOSE = re.compile(r"\bstar\b|jellyseerr-rating > svg |je-calendar-(?:legend-item|agenda-event-marker|play-btn)")
ARTWORK = re.compile(r"(?:^|> )(?:svg|g|path)\b[^>]* (?:fill|stroke)$")


def colour_values(value: str) -> list[tuple[float, float, float, float]]:
    out = []
    for m in COLOUR_VALUE.finditer(value):
        if m[1] is not None:
            out.append((float(m[1]), float(m[2]), float(m[3]), float(m[4] or 1)))
        else:
            out.append((float(m[5]) * 255, float(m[6]) * 255, float(m[7]) * 255, float(m[8] or 1)))
    return out


def neutral(c) -> bool:
    """Black, white, clear, and the faint gray veils Jellyfin lays over things."""
    r, g, b, a = c
    return a == 0 or (r, g, b) in ((0, 0, 0), (255, 255, 255)) or (r == g == b and a <= 0.2)


def fixed_on_purpose(key: str) -> bool:
    return bool(ON_PURPOSE.search(key)) or ("MuiSvgIcon" not in key and bool(ARTWORK.search(key)))


def paint(page) -> dict[str, list[str]]:
    at_rest(page)
    return page.evaluate(_js("colours.js"))


def unmoved(before: dict[str, list[str]], after: dict[str, list[str]]) -> dict[str, list[str]]:
    """What an element painted the same before and after the palette swap, neutrals and the
    colours kept on purpose aside: a colour written out instead of taken from the palette."""
    out = {}
    for key in sorted(before.keys() & after.keys()):
        if fixed_on_purpose(key):
            continue
        same = sorted(v for v in set(before[key]) & set(after[key]) if any(not neutral(c) for c in colour_values(v)))
        if same:
            out[key] = same
    return out


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


def text_items(page, route_name: str) -> list[dict]:
    """The text the contrast check samples on a route: the visible matches of its targets and
    of the targets every route has."""
    at_rest(page)
    selectors = TEXT_TARGETS["*"] + TEXT_TARGETS.get(route_name, ())
    return page.evaluate(_js("contrast.js"), list(selectors))


def contrast_failures(page, route_name: str, shot_path) -> list[dict]:
    items = text_items(page, route_name)
    selectors = TEXT_TARGETS["*"] + TEXT_TARGETS.get(route_name, ())
    if not items:
        return []
    # Three ids outrank any skin rule that colours the text with !important.
    hide = f":is({', '.join(selectors)}):not(#_):not(#_):not(#_) {{ color: transparent !important; text-shadow: none !important; }}"
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
