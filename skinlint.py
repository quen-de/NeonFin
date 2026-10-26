"""The skin's build-time rules (DEVELOPMENT.md, "Skin rules"). Stdlib only."""

from __future__ import annotations

import re

from cssscan import code_mask, declarations, leaf_rules, line_of, selectors

# The only selectors that may carry live glass (a backdrop-filter other than
# none). Each addition is a decision against the glass budget.
GLASS_ALLOWLIST = frozenset(
    {
        ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root",
        ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiBox-root:not(:last-child)",
        # Library pages: the header's second row.
        ".MuiAppBar-root > .MuiToolbar-root + .MuiToolbar-root",
        # Menus, desktop pages only: phones and the player turn it off.
        ".actionSheet",
        ".MuiPopover-paper",
        # The sign-in panel, desktop only: phones turn it off.
        "#loginPage > .margin-auto-y",
    }
)
PLUGIN_DIR = "skin/plugins/"
PLUGIN_HEADER = re.compile(r"\s*/\*\s*plugin:\s*(?P<name>[^;*]+?)\s*;\s*roots:\s*(?P<roots>[^*]+?)\s*\*/")
FILTERS = ("backdrop-filter", "-webkit-backdrop-filter")
# Text added through content would show in one language to everyone.
# content may only be empty or absent: any string, attr(), url(), counter() or quote shows
# something. Not justify-content and the like, which the lookbehind leaves alone.
CONTENT = re.compile(r"(?<![\w-])content\s*:\s*([^;}]*)")
CONTENT_EMPTY = {'""', "''", "none", "normal"}
# Emotion classes (css-1x2y3z) change on every jellyfin-web build.
EMOTION = re.compile(r"\.css-[0-9a-z]+\b")
# Every colour comes from the palette in the tokens file, so one block restyles the skin.
# Masks read only alpha, so their stops are not colours anyone sees.
TOKENS = "skin/00-tokens.css"
NAMED_COLOURS = (
    "aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown"
    " burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan"
    " darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid"
    " darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet"
    " deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro"
    " ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki"
    " lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan lightgoldenrodyellow"
    " lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray"
    " lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine"
    " mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen"
    " mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace"
    " olive olivedrab orange orangered orchid palegoldenrod palegreen paleturquoise palevioletred"
    " papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue"
    " saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey"
    " snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow"
    " yellowgreen"
    # System colours: the browser's own, which a palette cannot reach either.
    " accentcolor accentcolortext activetext buttonborder buttonface buttontext canvas canvastext field"
    " fieldtext graytext highlight highlighttext linktext mark marktext selecteditem selecteditemtext"
    " visitedtext"
).split()
# Hex, also escaped as %23 inside a data URI, colour functions, and the named colours as whole
# words (tan-spin and tan() are not colours).
COLOUR = re.compile(
    r"(?:#|%23)[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\("
    rf"|(?<![\w-])(?:{'|'.join(NAMED_COLOURS)})(?![\w(-])",
    re.IGNORECASE,
)
MASKS = ("mask-image", "-webkit-mask-image", "mask", "-webkit-mask")


def _code(css: str) -> str:
    return "".join(c if m else " " for c, m in zip(css, code_mask(css)))


def _bare(value: str) -> str:
    return value.replace("!important", "").strip()


def plugin_roots(css: str) -> list[str] | None:
    m = PLUGIN_HEADER.match(css)
    return [r.strip() for r in m["roots"].split(",") if r.strip()] if m else None


def _glass(where: str, prelude: str, decls: list[tuple[str, str]]) -> list[str]:
    out: list[str] = []
    webkit: list[str] = []
    for prop, value in decls:
        if prop in FILTERS and re.search(r"\b(?:var|url)\(", value):
            out.append(f"{where}: {prop} must use literal values, never var() or url()")
        if prop == "-webkit-backdrop-filter":
            webkit.append(value)
        elif prop == "backdrop-filter":
            if value not in webkit:
                out.append(f"{where}: backdrop-filter needs an identical -webkit-backdrop-filter declared before it")
            if _bare(value) != "none":
                out += [
                    f"{where}: glass on {s!r}, which is not on the glass allowlist" for s in selectors(prelude) if s not in GLASS_ALLOWLIST
                ]
    if webkit and not any(p == "backdrop-filter" for p, _ in decls):
        out.append(f"{where}: -webkit-backdrop-filter without backdrop-filter")
    return out


def lint(files: dict[str, str]) -> list[str]:
    """Problems in the skin sources, as 'path:line: message'."""
    problems: list[str] = []
    roots: dict[str, list[str]] = {}
    for name, css in files.items():
        if name.startswith(PLUGIN_DIR):
            found = plugin_roots(css)
            if not found:
                problems.append(f"{name}:1: a plugin file starts with /* plugin: <Name>; roots: <selector>, ... */")
            roots[name] = found or []
    every_root = sorted({r for rs in roots.values() for r in rs})
    for name, css in files.items():
        code = _code(css)
        problems += [f"{name}:{line_of(css, m.start())}: @import is not allowed" for m in re.finditer(r"@import\b", code)]
        problems += [
            f"{name}:{line_of(css, m.start())}: @font-face belongs to build.py, which embeds the font"
            for m in re.finditer(r"@font-face\b", code)
        ]
        mask = code_mask(css)
        problems += [
            f"{name}:{line_of(css, m.start())}: content adds visible text; only empty strings are allowed"
            for m in CONTENT.finditer(css)
            if mask[m.start()] and re.sub(r"\s*!important\s*$", "", m.group(1).strip()) not in CONTENT_EMPTY
        ]
        for rule in leaf_rules(css):
            where = f"{name}:{line_of(css, rule.offset)}"
            decls = declarations(rule.body)
            problems += _glass(where, rule.prelude, decls)
            if any(p == "will-change" for p, _ in decls):
                problems.append(f"{where}: will-change is not allowed")
            if name != TOKENS:
                problems += [
                    f"{where}: {prop} writes out a colour; take it from the palette in {TOKENS}"
                    for prop, value in declarations(rule.body, keep_strings=True)
                    if prop not in MASKS and COLOUR.search(re.sub(r"--[\w-]+", "", value))
                ]
            if rule.prelude.startswith("@") or any(c.startswith("@keyframes") for c in rule.context):
                continue
            for sel in selectors(rule.prelude):
                if EMOTION.search(sel):
                    problems.append(f"{where}: {sel!r} uses an emotion hash class, which changes on every Jellyfin build")
                if "[aria-label" in sel:
                    problems.append(f"{where}: {sel!r} selects by aria-label, which is localized")
                if name in roots:
                    variables_only = sel == ":root" and decls and all(p.startswith("--") for p, _ in decls)
                    if roots[name] and not variables_only and not any(r in sel for r in roots[name]):
                        problems.append(f"{where}: {sel!r} selects outside this plugin's roots")
                    if variables_only:
                        problems += [
                            f"{where}: {prop} belongs to the skin or Jellyfin; a plugin file sets only its plugin's variables"
                            for prop, _ in decls
                            if prop.startswith(("--nf-", "--jf-"))
                        ]
                else:
                    leaked = [r for r in every_root if r in sel]
                    if leaked:
                        problems.append(f"{where}: core file selects plugin markup ({leaked[0]})")
    return sorted(problems, key=lambda p: (p.split(":")[0], int(p.split(":")[1])))
