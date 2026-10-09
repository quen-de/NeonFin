"""The skin's build-time rules (spec section 7.1). Stdlib only."""

from __future__ import annotations

import re

from cssscan import code_mask, declarations, leaf_rules, line_of, selectors

# The only selectors that may carry live glass (a backdrop-filter other than
# none). Each addition is a decision against the glass budget (spec 5.2).
GLASS_ALLOWLIST = frozenset(
    {
        ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root",
        ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiBox-root:not(:last-child)",
    }
)
PLUGIN_DIR = "skin/plugins/"
PLUGIN_HEADER = re.compile(r"\s*/\*\s*plugin:\s*(?P<name>[^;*]+?)\s*;\s*roots:\s*(?P<roots>[^*]+?)\s*\*/")
FILTERS = ("backdrop-filter", "-webkit-backdrop-filter")
# Text added through content would show in one language to everyone.
CONTENT_TEXT = re.compile(r"""\bcontent\s*:\s*(?:"[^"]+"|'[^']+')""")
# Emotion classes (css-1x2y3z) change on every jellyfin-web build.
EMOTION = re.compile(r"\.css-[0-9a-z]+\b")


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
            for m in CONTENT_TEXT.finditer(css)
            if mask[m.start()]
        ]
        for rule in leaf_rules(css):
            where = f"{name}:{line_of(css, rule.offset)}"
            decls = declarations(rule.body)
            problems += _glass(where, rule.prelude, decls)
            if any(p == "will-change" for p, _ in decls):
                problems.append(f"{where}: will-change is not allowed")
            if rule.prelude.startswith("@") or any(c.startswith("@keyframes") for c in rule.context):
                continue
            for sel in selectors(rule.prelude):
                if EMOTION.search(sel):
                    problems.append(f"{where}: {sel!r} uses an emotion hash class, which changes on every Jellyfin build")
                if "[aria-label" in sel:
                    problems.append(f"{where}: {sel!r} selects by aria-label, which is localized")
                if name in roots:
                    if roots[name] and not any(r in sel for r in roots[name]):
                        problems.append(f"{where}: {sel!r} selects outside this plugin's roots")
                else:
                    leaked = [r for r in every_root if r in sel]
                    if leaked:
                        problems.append(f"{where}: core file selects plugin markup ({leaked[0]})")
    return sorted(problems, key=lambda p: (p.split(":")[0], int(p.split(":")[1])))
