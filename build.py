#!/usr/bin/env python3
"""Build NeonFin into one self-contained stylesheet, dist/neonfin.css.

Concatenates skin/ in cascade order (numbered core files, then one file per
plugin, then the files numbered 99), embeds the sign font as a data: URI,
enforces the skin rules in skinlint.py, and stamps the commit into a header
comment. Stdlib only, so any deploy script can run it with a system python3.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import pathlib
import re
import subprocess
import sys

import skinlint
from cssscan import BuildError, brace_scan, line_of

ROOT = pathlib.Path(__file__).resolve().parent
TOKENS = "skin/00-tokens.css"
LATE = 99  # numbered files from here on come after the plugin files
FONT_FILE = "skin/fonts/neonfin-sign-800.woff2"
FONT_FAMILY = "NeonFin Sign"
FONT_WEIGHT = 800
HEADER_RE = re.compile(r"^/\* neonfin ([0-9a-f]{40}|unknown)(-dirty)?")


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
    return font_face(root) + "\n".join(parts[name] for name in names)


def fork_state(root: pathlib.Path) -> tuple[str, bool]:
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
    sha, dirty = fork_state(root)
    return header(sha, dirty) + assemble(root)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build dist/neonfin.css")
    ap.add_argument("-o", "--out", default=str(ROOT / "dist" / "neonfin.css"))
    args = ap.parse_args(argv)
    try:
        css = build(ROOT)
        font = len(font_face(ROOT).encode())
    except BuildError as e:
        print(f"build: {e}", file=sys.stderr)
        return 1
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(css, encoding="utf-8")
    raw = css.encode("utf-8")
    print(f"wrote {out} ({len(raw):,} bytes, {len(raw) - font:,} without the font, {len(gzip.compress(raw)):,} gzip)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
