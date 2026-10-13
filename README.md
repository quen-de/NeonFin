# NeonFin

A fast glass-and-neon web skin for Jellyfin 12.

Status: early development, not ready for use.

## Principles

- Never slower than plain Jellyfin. Every effect is measured against it.
- Glass only where it reads as glass: the header and menus, never on cards or over video.
- Works with or without popular plugins: Media Bar Enhanced, Home Screen Sections, Jellyfin Enhanced, Custom Tabs.
- One stylesheet, no external requests: system fonts for the interface, one embedded display face.

## Install

1. `python3 build.py` writes `dist/neonfin.css`.
2. Paste its contents into the Custom CSS field of your server's branding settings.

Jellyfin 12, modern layout, desktop browsers and phones. The legacy layout is not styled for, and TV apps do not load custom CSS.

## Plugin notes

Media Bar Enhanced gives each slide its own dot, and above its maximum number of dots shows a
counter instead. Its stylesheet imports a web font from Google; the skin sets the hero in its
own face, so the font itself is never downloaded, but the import still is. The original Media
Bar plugin is not supported.

## Change the palette

Every colour in the skin comes from eight tokens. To restyle it, add a block after the skin
in Custom CSS and set only the ones you want to change. For a cyan neon:

    :root { --nf-neon: #00e5ff; }

The eight, with their defaults:

    :root {
      --nf-neon: #ff2448;   /* accent: Play, focus rings, lit titles, progress */
      --nf-teal: #19d3c5;   /* second accent, in the background light */
      --nf-ink: #05060a;    /* page background */
      --nf-ink-2: #090b12;  /* raised background */
      --nf-chrome: #121420; /* header, menus and panels */
      --nf-paper: #f6f3f0;  /* text */
      --nf-light: #fff;     /* highlights, rims and washes */
      --nf-shade: #000;     /* shadows */
    }

The defaults keep every label readable over the brightest artwork. A lighter ink or chrome,
or a darker paper, can cost that.

## Licence

MIT. The embedded sign font is a subset of Big Shoulders Display, under the SIL Open Font
License 1.1 (`skin/fonts/OFL.txt`).
