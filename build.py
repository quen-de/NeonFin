#!/usr/bin/env python3
"""Build NeonFin into one self-contained stylesheet, dist/neonfin.css.

Concatenates skin/ in cascade order (numbered core files, then one file per
plugin, then the files numbered 99), embeds the sign font as a data: URI,
enforces the skin rules in skinlint.py, strips comments, and stamps the commit
into a header comment. It also writes dist/palette.html, the palette picker,
from palettes/. Stdlib only, so any deploy script can run it with a system
python3.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import pathlib
import re
import subprocess
import sys

import skinlint
from cssscan import BuildError, brace_scan, declarations, leaf_rules, line_of, strip_comments

ROOT = pathlib.Path(__file__).resolve().parent
TOKENS = "skin/00-tokens.css"
LATE = 99  # numbered files from here on come after the plugin files
FONT_FILE = "skin/fonts/neonfin-sign-800.woff2"
FONT_FAMILY = "NeonFin Sign"
FONT_WEIGHT = 800
PICKER = "palettes/picker.html"
HEADER_RE = re.compile(r"^/\* neonfin ([0-9a-f]{40}|unknown)(-dirty)?")
# The palette's inputs, in the order a picker shows them; each is a --nf- token.
PALETTE = ("neon", "teal", "ink", "ink-2", "chrome", "paper", "light", "shade", "on-neon")
PRESET_HEADER = re.compile(r"/\* NeonFin palette: ([^.]+)\. Paste after the skin in Custom CSS\. \*/\n")


def preset_tokens(css: str) -> dict[str, str]:
    """The --nf- properties a stylesheet's :root rules set, by name without the prefix."""
    out: dict[str, str] = {}
    for rule in leaf_rules(css):
        if rule.prelude == ":root":
            out |= {p.removeprefix("--nf-"): v for p, v in declarations(rule.body) if p.startswith("--nf-")}
    return out


def hex6(value: str) -> str:
    """A hex colour as #rrggbb, lower case."""
    v = value.strip().lower()
    return "#" + "".join(c * 2 for c in v[1:]) if re.fullmatch(r"#[0-9a-f]{3}", v) else v


def palette_presets(root: pathlib.Path | None = None) -> dict[str, dict[str, str]]:
    """The default palette as Crimson, every input spelt out, then each preset by its display
    name with the inputs it changes."""
    root = root or ROOT
    tokens = preset_tokens((root / TOKENS).read_text(encoding="utf-8"))
    defaults = {}
    for name in PALETTE:
        ref = re.fullmatch(r"var\(--nf-([\w-]+)\)", tokens[name])
        defaults[name] = hex6(tokens[ref[1]] if ref else tokens[name])
    out = {"Crimson": defaults}
    for path in sorted((root / "palettes").glob("*.css")):
        css = path.read_text(encoding="utf-8")
        head = PRESET_HEADER.match(css)
        if not head:
            raise BuildError(f"palettes/{path.name} starts with /* NeonFin palette: <Name>. Paste after the skin in Custom CSS. */")
        out[head[1]] = {k: hex6(v) for k, v in preset_tokens(css).items()}
    return out


def palette_page(root: pathlib.Path | None = None) -> str:
    """The palette picker: its template with the sign font, the tokens scoped to its preview
    and the presets filled in."""
    root = root or ROOT
    path = root / PICKER
    if not path.exists():
        raise BuildError(f"missing {PICKER}")
    tokens = strip_comments((root / TOKENS).read_text(encoding="utf-8")).replace(":root", ".nf-preview", 1)
    page = path.read_text(encoding="utf-8")
    for mark, value in (("/*@FONT@*/", font_face(root)), ("/*@TOKENS@*/", tokens), ("/*@PRESETS@*/null", json.dumps(palette_presets(root)))):
        if mark not in page:
            raise BuildError(f"{PICKER} has no {mark} mark")
        page = page.replace(mark, value)
    return page


def skin_files(root: pathlib.Path | None = None) -> list[str]:
    """Repo-relative source paths in cascade order."""
    root = root or ROOT
    if not (root / TOKENS).exists():
        raise BuildError(f"missing {TOKENS}")
    skin = root / "skin"
    numbered = sorted(skin.glob("[0-9][0-9]-*.css"))
    early = [p for p in numbered if int(p.name[:2]) < LATE]
    late = [p for p in numbered if int(p.name[:2]) >= LATE]
    plugins = sorted((skin / "plugins").glob("*.css"))
    return [p.relative_to(root).as_posix() for p in early + plugins + late]


def font_face(root: pathlib.Path | None = None) -> str:
    path = (root or ROOT) / FONT_FILE
    if not path.exists():
        raise BuildError(f"missing {FONT_FILE}")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return (
        f'@font-face {{ font-family: "{FONT_FAMILY}"; src: url(data:font/woff2;base64,{data}) format("woff2"); '
        f"font-weight: {FONT_WEIGHT}; font-style: normal; font-display: swap; }}\n"
    )


def check_braces(name: str, css: str) -> None:
    scan = brace_scan(css)
    if scan.strays:
        raise BuildError(f"{name} is brace-unbalanced: stray '}}' at line {line_of(css, scan.strays[0])}")
    if scan.open:
        raise BuildError(f"{name} is brace-unbalanced: {scan.open} block(s) left open")


def assemble(root: pathlib.Path | None = None) -> str:
    root = root or ROOT
    names = skin_files(root)
    parts = {name: (root / name).read_text(encoding="utf-8") for name in names}
    for name, css in parts.items():
        check_braces(name, css)
    problems = skinlint.lint(parts)
    if problems:
        raise BuildError("skin rules broken:\n  " + "\n  ".join(problems))
    stripped = []
    for name in names:
        try:
            stripped.append(strip_comments(parts[name]))
        except BuildError as e:
            raise BuildError(f"{name}: {e}") from None
    return font_face(root) + "".join(stripped)


def repo_state(root: pathlib.Path) -> tuple[str, bool]:
    try:
        sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True
    return sha, bool(dirty)


def header(sha: str, dirty: bool) -> str:
    return f"/* neonfin {sha}{'-dirty' if dirty else ''} */\n"


def parse_header(css: str) -> tuple[str, bool] | None:
    m = HEADER_RE.match(css)
    return (m.group(1), bool(m.group(2))) if m else None


def build(root: pathlib.Path | None = None) -> str:
    root = root or ROOT
    sha, dirty = repo_state(root)
    return header(sha, dirty) + assemble(root)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build dist/neonfin.css")
    ap.add_argument("-o", "--out", default=str(ROOT / "dist" / "neonfin.css"))
    args = ap.parse_args(argv)
    try:
        css = build(ROOT)
        font = len(font_face(ROOT).encode())
        picker = palette_page(ROOT)
    except BuildError as e:
        print(f"build: {e}", file=sys.stderr)
        return 1
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(css, encoding="utf-8")
    raw = css.encode("utf-8")
    print(f"wrote {out} ({len(raw):,} bytes, {len(raw) - font:,} without the font, {len(gzip.compress(raw)):,} gzip)")
    page = out.parent / "palette.html"
    page.write_text(picker, encoding="utf-8")
    print(f"wrote {page} (the palette picker)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
