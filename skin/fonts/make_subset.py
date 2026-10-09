"""Make the sign font subset from Big Shoulders Display (SIL OFL 1.1).

Source: github.com/google/fonts, ofl/bigshouldersdisplay/BigShouldersDisplay[wght].ttf.
Pins the weight axis at 800, keeps every non-lowercase character from U+0020 to
U+017F plus common typographic punctuation (signs are always uppercase), and
renames the family to "NeonFin Sign" so it never shadows an installed Big Shoulders.

Usage: uv run python skin/fonts/make_subset.py SOURCE.ttf skin/fonts/neonfin-sign-800.woff2
"""

import sys
import unicodedata

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

EXTRA = (0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x20AC)
SIGN_CHARS = sorted({c for c in range(0x20, 0x180) if unicodedata.category(chr(c)) not in ("Ll", "Cc")} | set(EXTRA))
FAMILY = "NeonFin Sign"


def rename(font: TTFont) -> None:
    names = {1: FAMILY, 4: f"{FAMILY} ExtraBold", 6: FAMILY.replace(" ", "") + "-ExtraBold", 16: FAMILY, 17: "ExtraBold"}
    table = font["name"]
    for rec in list(table.names):
        if rec.nameID in names:
            table.setName(names[rec.nameID], rec.nameID, rec.platformID, rec.platEncID, rec.langID)


def main(src: str, out: str) -> int:
    font = instancer.instantiateVariableFont(TTFont(src), {"wght": 800})
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=SIGN_CHARS)
    sub.subset(font)
    rename(font)
    font.flavor = "woff2"
    font.save(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
