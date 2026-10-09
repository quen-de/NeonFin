# NeonFin

A fast glass-and-neon web skin for Jellyfin 12.

Status: early development, not ready for use.

## Principles

- Never slower than plain Jellyfin. Every effect is measured against it.
- Glass only where it reads as glass: the header and menus, never on cards or over video.
- Works with or without popular plugins: Media Bar, Home Screen Sections, Jellyfin Enhanced, Custom Tabs.
- One stylesheet, no external requests: system fonts for the interface, one embedded display face.

## Install

1. `python3 build.py` writes `dist/neonfin.css`.
2. Paste its contents into the Custom CSS field of your server's branding settings.

Jellyfin 12, modern layout, desktop browsers and phones. The legacy layout is not styled for, and TV apps do not load custom CSS.

## Plugin notes

Media Bar shows one dot per slide only while it has no more slides than dots. With more
slides, each dot stands for a run of them, so the lit dot stays put for several slides.
That is the plugin's design, not the skin. Raise its maximum number of dots to the number
of slides, or lower the number of slides, to give each slide its own dot.

## Change the accent

Add this after the skin in Custom CSS:

    :root { --nf-neon: #3da9fc; }

## Licence

MIT. The embedded sign font is a subset of Big Shoulders Display, under the SIL Open Font
License 1.1 (`skin/fonts/OFL.txt`).
