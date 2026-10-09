# Sign font

`neonfin-sign-800.woff2` is a subset of Big Shoulders Display (Copyright 2019 The Big
Shoulders Project Authors), licensed under the SIL Open Font License 1.1 (`OFL.txt`). The
licence declares no Reserved Font Name. The subset is renamed "NeonFin Sign".

Rebuild it from the variable source in google/fonts:

    curl -fsSL -o /tmp/bsd.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/bigshouldersdisplay/BigShouldersDisplay%5Bwght%5D.ttf"
    uv run python skin/fonts/make_subset.py /tmp/bsd.ttf skin/fonts/neonfin-sign-800.woff2

It keeps weight 800 and every non-lowercase character from U+0020 to U+017F plus common
punctuation. Signs are always uppercase; other scripts fall back to the system font.
