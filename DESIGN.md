---
name: NeonFin
description: A fast glass-and-neon web skin for Jellyfin 12, dark only, one stylesheet.
colors:
  neon: "#ff2448"
  teal: "#19d3c5"
  ink: "#05060a"
  ink-2: "#090b12"
  chrome: "#121420"
  paper: "#f6f3f0"
  light: "#ffffff"
  shade: "#000000"
  on-neon: "#ffffff"
  neon-deep: "#b21932"
  oxblood: "#4a0a15"
  sign: "#ffe5e9"
  neon-text: "#ff7c91"
  text: "#f6f3f0f0"
  text-2: "#f6f3f09e"
  rim: "#ffffff29"
  chrome-deep: "#0e1019"
  chrome-tint: "#12142066"
  chrome-solid: "#0e1019eb"
  selected: "#ff244833"
  error: "#f44336"
typography:
  sign-row:
    fontFamily: "NeonFin Sign, Arial Narrow, sans-serif"
    fontSize: "2.1rem"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "0.08em"
  sign-title:
    fontFamily: "NeonFin Sign, Arial Narrow, sans-serif"
    fontSize: "2.6rem"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "0.06em"
  sign-login:
    fontFamily: "NeonFin Sign, Arial Narrow, sans-serif"
    fontSize: "1.9rem"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "0.08em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, sans-serif"
  label-nav:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontWeight: 500
    letterSpacing: "0.01em"
  label-action:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontWeight: 600
  label-indicator:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, sans-serif"
    fontSize: "12px"
    fontWeight: 700
rounded:
  flag: "3px"
  badge: "6px"
  thumb: "8px"
  field: "10px"
  card: "12px"
  menu: "14px"
  pill: "999px"
  round: "50%"
spacing:
  capsule-gap: "10px"
  capsule-height: "42px"
  pill-height: "34px"
  button-secondary: "44px"
  button-play: "52px"
  phone-gutter: "16px"
components:
  button-play:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.light}"
    rounded: "{rounded.pill}"
    size: "{spacing.button-play}"
  button-secondary:
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    size: "{spacing.button-secondary}"
  button-disabled:
    textColor: "{colors.text-2}"
    rounded: "{rounded.pill}"
  button-error:
    textColor: "{colors.light}"
    rounded: "{rounded.pill}"
  header-capsule:
    backgroundColor: "{colors.chrome-tint}"
    rounded: "{rounded.pill}"
    height: "{spacing.capsule-height}"
    padding: "0 5px"
  header-pill:
    textColor: "{colors.text-2}"
    rounded: "{rounded.pill}"
    height: "{spacing.pill-height}"
    padding: "0 12px"
  header-pill-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.light}"
    rounded: "{rounded.pill}"
  card:
    backgroundColor: "{colors.ink-2}"
    textColor: "{colors.text-2}"
    rounded: "{rounded.card}"
  field:
    textColor: "{colors.text}"
    rounded: "{rounded.field}"
  search-field:
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    height: "48px"
    padding: "0 48px 0 50px"
  menu:
    rounded: "{rounded.menu}"
  dialog:
    backgroundColor: "{colors.ink-2}"
    rounded: "{rounded.menu}"
  tooltip:
    backgroundColor: "{colors.chrome-deep}"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    padding: "5px 12px"
  toast:
    backgroundColor: "{colors.chrome-deep}"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    padding: "10px 18px"
  sign-in-panel:
    rounded: "{rounded.menu}"
    width: "min(440px, 100% - 32px)"
    padding: "28px 28px 24px"
---

# Design System: NeonFin

Colour values above are the default (Crimson) palette as rendered. The source of truth is
`skin/00-tokens.css`: nine inputs set in hex, everything else mixed from them with
`color-mix(in srgb, ...)`, so a preset or a user block that changes the inputs changes every
derived value. `build.py` concatenates `skin/` (numbered core files, then `skin/plugins/*.css`,
then `99-*`) into `dist/neonfin.css` and enforces the rules in `skinlint.py`.

## Overview

**Creative North Star: "Jellyfin After Dark"**

The artwork is the city outside, the interface is the glass you look through, and neon is how
the street speaks. Pages sit on ink lit by a fixed, static city glow (crimson top right, teal
left, crimson low) or on the title's own backdrop. Navigation floats as glass capsules, row and
page titles are lit signs, and Play is the one thing that glows as a tube. It refuses the
streaming default of flat black slabs with gray chrome, and it refuses expensive effects: speed
is part of the look, so every effect is painted once, revealed by opacity, or dropped.

The skin is CSS only, carries no server's brand, adds no visible text, and styles plugin
features when present without depending on them. Dark only; no light mode.

**Key Characteristics:**
- One accent (`--nf-neon`) carries every lit thing: Play, focus, selection, progress, sign glow.
- Live glass on a short allowlist (header capsules, library toolbar, menus, sign-in panel), desktop only.
- Content is never glass: depth on cards comes from tint, a hairline, a top rim and a soft shadow.
- Lit-sign titles in an embedded condensed display face; everything else in the platform's own UI font.
- Round forms: pills and circles for controls, 12px cards, 14px menus.

## Colors

One crimson accent over cool near-black ink, with a teal second light that only ever tints the
background (and one plugin status badge).

### The nine inputs (`skin/00-tokens.css`)

| Token | Paints |
|---|---|
| `--nf-neon` | The accent: Play tubes, focus outline and card ring, selected pills, progress bars, checkboxes, active dots, played and favourite marks, the sign glow |
| `--nf-on-neon` | Labels and ticks drawn on the accent (count badges, checkbox ticks, selection text). Defaults to `var(--nf-light)` |
| `--nf-teal` | Second ambient light in the page background |
| `--nf-ink` | Page ground, dialog backdrop, every dimming gradient (hero, title pages, OSD) |
| `--nf-ink-2` | Raised ground: dialogs, drawer, card placeholders, option lists, solid fallbacks |
| `--nf-chrome` | Glass and solid chrome: capsules, menus, panels |
| `--nf-paper` | Text, at two alphas |
| `--nf-light` | White highlights: rims, washes, hover fills, labels on tubes |
| `--nf-shade` | Shadows, and the dark end of the deepened mixes |

### Derived tokens

- **Neon deep** (`neon 70%` into `shade`): text selection ground, Seerr "on its way" badge, MUI primary dark.
- **Oxblood** (`neon 29%` into `shade`): avatar ground, settings list icons, user-picker tiles, subtitle preview.
- **Sign pink** (`neon 12%` into `light`): lit-sign text.
- **Crimson for text** (`neon 60%` into `light`, `--nf-neon-text`): any accent coloured text (link hover, active A to Z letter, filter reset, focused sign-in label, search suggestion on hover or focus, Up Next countdown). Lighter than the accent so it passes AA on dark chrome.
- **Text / text-2** (`paper` at 94% / 62% alpha): primary and secondary text.
- **Rim** (`light` at 16%): top-edge highlights and hairlines on tinted controls.
- **Chrome deep** (`chrome 70%` into `ink`), **chrome tint** (`chrome` at 40%, the glass fill), **chrome solid** (`chrome-deep` at 92%, phone chrome).
- **Selected / selected edge** (`neon` at 20% fill, inset 1px at 75%): the "you are here" pill.
- **Error** (`--jf-palette-error-main`, fallback `#f44336`): the server theme's own error colour, kept on purpose; not one of the nine.

Washes are always `color-mix(in srgb, var(--nf-light) N%, transparent)`: 3% disabled field, 4% list hover, 6% field and search fill, 8% tinted button and hover fill, 10% field hover, 12% icon-button hover, 14% tinted button hover, 18% scrollbar thumb and progress track.

### Presets (`palettes/*.css`)

Crimson is the default. Each preset sets only the inputs it changes, in hex, and starts with
`/* NeonFin palette: <Name>. Paste after the skin in Custom CSS. */`.

| Preset | neon | on-neon | teal | ink / ink-2 / chrome |
|---|---|---|---|---|
| Cyan neon | `#00e5ff` | `#000` | `#ff3dbb` | `#04070a` / `#08101a` / `#0f1a24` |
| Amber | `#ffb020` | `#000` | default | `#070605` / `#0d0b08` / `#1a1610` |
| Violet | `#a855ff` | default | `#2ee6d6` | `#06050b` / `#0b0914` / `#161225` |
| Acid green | `#b6ff2e` | `#000` | `#ff2bd6` | `#050704` / `#090c07` / `#131a10` |

`palettes/picker.html` (built to `dist/palette.html`) previews any palette and checks it.

### Named Rules

**The Dark Label Rule.** A light accent needs dark labels: any palette whose neon is light sets `--nf-on-neon: #000`. Never paint text on the accent in `--nf-light` directly; use `--nf-on-neon`.

**The Nine Inputs Rule.** Every colour comes from the palette in `skin/00-tokens.css`. No other file writes a colour literal (masks excepted: they read only alpha). A new shade is a `color-mix` of tokens, written where it is used or added to the tokens file.

**The Teal Stays Outside Rule.** Teal lights the city behind the page. It never marks a control; the only non-background use is a plugin status badge, because a status is not a control.

**The Text Crimson Rule.** Accent coloured text uses `--nf-neon-text`, never `--nf-neon`: the raw accent fails 4.5:1 on glass over a bright image.

## Typography

**Display Font:** NeonFin Sign, a subset of Big Shoulders Display weight 800, embedded by `build.py` as a woff2 data URI (with `"Arial Narrow", sans-serif` per glyph outside the subset)
**Body Font:** the platform UI stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif`), applied to html, form controls and MUI roots

**Character:** a tall condensed sign face, uppercase and glowing, set against whatever font the device already speaks. Nothing is downloaded for interface text.

### Hierarchy
- **Row sign** (800, 2.1rem desktop / 1.5rem phone, line-height 1.05, 0.08em, uppercase, `--nf-sign` with the sign glow): every row title on home, title pages and search.
- **Title sign** (800, 2.6rem desktop, line-height 1.05, 0.06em, uppercase, sign glow): the item name on title pages. Phones keep Jellyfin's size. Desktop pads the heading 0.6em (with a -0.6em margin) so the glow survives the ellipsis clip.
- **Sign-in sign** (800, 1.9rem desktop / 1.5rem phone, 0.08em, uppercase, sign glow): the sign-in heading.
- **Body** (system, Jellyfin's sizes): title-page overview capped at 54ch; folded, its paragraphs run inline so the clamp cuts whole lines.
- **Labels**: header items 500 at 0.01em, no uppercase; tube and card first-line labels 600; settings headings 600 (working pages carry no signs); indicator badges 12px 700; search field 1.1rem; toasts 0.95rem; tooltips 0.75rem; slide counter in tabular numerals.

### Named Rules

**The Lit Sign Rule.** Signs are for titles a viewer reads to choose what to watch: rows, the title page name, the sign-in heading. Settings and other working pages use semibold interface type instead.

**The No Added Text Rule.** The skin never writes words: `content` is only ever `""`, so buttons stay icon-only and nothing shows in one language to everyone.

## Layout

The skin keeps Jellyfin's own layout and switches on its `.layout-desktop` and `.layout-mobile`
classes, not on widths. Exceptions: dialogs square off below `80em` wide or `45em` tall, and
the Media Bar counter centring defers to the plugin's own rule for phones held upright
(`max-width: 767px` and portrait).

- **Header**: no bar. A transparent app bar holds two capsules 42px tall, 10px apart, never wrapping; the navigation capsule shrinks and scrolls sideways (scrollbar hidden) rather than pushing the actions to a second row. The avatar sits outside both.
- **Library toolbar**: the header's second row becomes a 42px capsule with `margin: 3px 3.3%`, keeping its 48px row so the grid does not move. On phones it is a solid panel of auto height, 22px radius.
- **Rows**: 2.2em between rows on desktop, 1.1em on phones. The scroller pads 12px top and 16px bottom (10px bottom on phones) so the lift and the ring's glow are not cut.
- **Title pages**: detail buttons wrap with a 10px gap rather than squeeze out of round. Overview and its Show more control share a 54ch column; Show more sits under the end of the text at the column's edge.
- **Search**: phones run the field edge to edge inside a 16px gutter.
- **Sign-in**: one centred panel `min(440px, 100% - 32px)`; on desktop the user picker shows three tiles a row, phones keep Jellyfin's two.
- **Hero (Media Bar Enhanced)**: desktop keeps title, details and plot in a dimmed left column (`max-width: 34vw`, plot clamped to 3 lines); phones centre the details over ink that rises from the bottom.
- **Safe areas**: the phone action sheet pads its bottom by `env(safe-area-inset-bottom)`; the phone sign-in panel by `18px + env(safe-area-inset-bottom)`.
- **Readability bands**: wherever text or glass sits over imagery, an ink gradient sits under it (72% to 60% at 56px to clear by 160px under the header; library desktop band to 96px; title ribbon 64% to 72%; OSD bars 80% top, 86% bottom).

## Elevation & Depth

Three layers, and only the top one is real glass. **Ambient**: the city light on
`.backgroundContainer`, painted once, or the title's backdrop blurred once with `filter`
(`blur(36px) saturate(1.7) brightness(0.95)`; on desktop the image stays sharp at the top and a
masked copy blurs from 22% to 62% down). **Content**: rows, cards, title details; never
`backdrop-filter`. **Chrome**: the live glass, on desktop only.

### Glass recipes (literal, `-webkit-backdrop-filter` first)
- **Capsule glass** (`saturate(180%) blur(20px)`, fill `--nf-chrome-tint`, `--nf-chrome-edge`): header capsules and library toolbar.
- **Menu glass** (`saturate(180%) blur(22px)`, fill `chrome` at 55%, 72% for MUI menus which have no dimmed page behind them): action sheets, MUI popovers, the sign-in panel (55%).
- **Phone and over-video chrome**: the same shapes, no blur. Capsules use `--nf-chrome-solid`; menus and the phone sign-in panel `chrome-deep` at 96%.

### Shadow Vocabulary
- **Chrome edge** (`inset 0 1px 0 light 22%, inset 0 0 0 1px light 7%, 0 10px 26px -12px shade 70%`): every capsule and glass panel.
- **Card drop** (`0 14px 28px -18px shade 90%`): under card artwork.
- **Card hairline** (`inset 0 0 0 1px light 10%, inset 0 1px 0 light 18%`): on the artwork itself.
- **Menu drop** (`0 18px 48px shade 50%`) and **dialog drop** (`0 24px 64px shade 60%`).
- **Badge drop** (`0 2px 6px shade 50%`): count and played indicators off cards.
- **Neon tube** (`inset 0 0 0 2px neon, 0 0 18px neon 80%, inset 0 0 14px neon 60%`): Play and primary actions only.
- **Neon ring** (`inset 0 0 0 2px neon, 0 0 22px 2px neon 55%`): the lit card.
- **Sign glow** (text-shadow `0 0 2px light 60%, 0 0 10px neon 90%, 0 0 26px neon 55%`): lit signs.

### Named Rules

**The Real Glass Rule.** Glass only where something visible moves behind it: the header capsules, the library toolbar, menus and the sign-in panel, on desktop. Never on cards, in scrollers, on hover, over video, or behind a dimmed dialog. A new glass selector must be added to `GLASS_ALLOWLIST` in `skinlint.py` as a decision against the budget (desktop: at most three live surfaces plus one open menu; phones: none).

**The Literal Filter Rule.** Filter chains are literal: no `var()` or `url()` inside them, and nothing that contains glass gets `opacity`, `filter`, `mask` or `will-change`.

**The One Glow Rule.** Outer glow belongs to Play. The selected pill, the active section and selected menu items are lit by fill and an inset edge, never a glow.

## Shapes

Controls are pills or circles (`999px`, `50%`): capsules, header items, tinted and tube buttons,
fields in search, scroll arrows, tooltips, toasts, the A to Z rail, progress bars. Artwork has
soft corners: cards 12px, menus and dialogs 14px, episode thumbnails and the scrub preview 8px,
dropdowns and MUI filled fields 10px, age rating 6px, language flags 3px. Corners always follow
the artwork: Jellyfin's placeholder, blurhash and overlay layers take the card radius so nothing
pokes out. Circular artwork is reserved for people: cast and crew portraits and the sign-in user
picker are circles, the portrait crop at `50% 25%` so faces stay in frame. Full-screen dialogs
are square. Card indicators form one tab in the card's top corner (`0 12px 0 10px`, mirrored in
RTL).

## Components

### Buttons
- **Neon tube (Play and primary)**: `neon` 12% fill, the tube shadow, white label with a `0 0 8px neon 90%` text glow; hover 22% fill. Title-page Play is a 52px circle; the card's play disc mixes 16% neon into 70% ink so it reads over any poster (30% on hover); library Play All is a 34px pill; legacy submit, MUI contained buttons, the Media Bar Play and the Seerr Request button all use it. Focus on a tube takes a white outline, since crimson vanishes in its glow.
- **Round tinted (secondary)**: `light` 8% fill, inset 1px rim, `--nf-text` icon; hover 14%. 44px on title pages, 34px in the library toolbar, 36px scroll arrows (top rim only). Icon-only. Disabled toolbar buttons drop to 0.4 opacity.
- **Raised secondary pill**: other legacy raised buttons, the same tint and rim, hover 14%.
- **Disabled submit**: a dim pill, `light` 6%, rim, `--nf-text-2` label, no glow.
- **Error (destructive)**: a solid pill, `error` 70% into `shade` so white labels reach 4.5:1, 18% light inset edge, no glow, same on hover and focus.
- **Icon buttons** (Jellyfin's round ones): white on a 12% wash on hover and press; keyboard focus turns the icon `--nf-neon-text`.

### Navigation
- **Header capsules**: see Layout and Elevation. Items are 34px pills in `--nf-text-2`; hover `--nf-text` on an 8% wash; the current section is the selected pill (`--nf-selected`, `--nf-selected-edge`, white text). Avatar on oxblood with a rim ring. A Jellyfin Enhanced tray sits in the actions capsule as more 34px pills.
- **Phone**: the same shapes solid; the menu button is its own 42px solid circle. The drawer is solid `ink-2` with a rim on its edge; items are pills, the current one the selected pill.

### Cards and rows
- **Card**: artwork at 12px with the hairline and card drop; placeholder `ink-2`, its type icon at `light` 22%. Text under it `--nf-text-2`, first line `--nf-text` 600. Cards without artwork use five steps of `neon` 12% to 36% into `ink-2`.
- **Lit card**: the ring is pre-painted on a pseudo-element at opacity 0. Pointer hover lifts the artwork 4px at once and fades the ring in over 180ms; it goes out at once. Keyboard focus, not focus a click leaves on a card's button, lifts and glows with a 180ms glide and suppresses the global outline (kept in forced colours). Touch screens get no hover state.
- **Indicators**: counts and the watched check are accent pills with `--nf-on-neon` text; on cards they merge into one tinted tab (`neon` 52% over `ink-2` at 42%), not blurred. Played and favourite icons are crimson. Progress bars are 4px pills, crimson on an 18% track.
- **Rows**: titles are row signs; the see-all chevron in `--nf-text-2`. The home "My Media" row hides its own title, and hides the name under each library tile that has artwork (the artwork carries the name), visually only: screen readers keep both. A tile without artwork keeps its name.

### Title pages
- Backdrop under the whole page, ink ramping in under the text (120px soft ramp above the ribbon, ribbon 64% to 72%, page panel 72% to 82% by 480px). The in-page backdrop fades out from 55% down.
- Name as the title sign; the details line in `--nf-text-2`; the age rating keeps its outline at 6px.
- Tags, external links and credit labels in `--nf-text-2`, links lighting `--nf-neon-text` on hover.
- Buttons: Play tube first, then round tinted buttons, wrapping on narrow phones.
- Episode lists: 16:9 thumbnails at 8px; the row rounds to 12px with a 4% wash on hover.
- Cast and crew: round portraits; the card menu button moves onto the portrait's edge (`right: 8%; bottom: 8%`).

### Inputs and fields
- **Dropdowns and MUI filled fields**: `light` 6% fill, 1px border at 14% (inset on MUI), 10px radius; hover 10% fill and 22% border. Focus turns the border `neon` 80% and the label `--nf-neon`. MUI's underline is removed, so the error state lives on the rim in `--nf-error`. Disabled MUI fields go flat (3% fill, 7% rim); a disabled select stays plain text.
- **Search**: a 48px pill with the magnifier inside at 16px, `light` 6% fill, 14% border; focus adds a 3px `neon` 30% halo. Suggestions read in `--nf-text` and light `--nf-neon-text` only on hover or focus. No results is one quiet `--nf-text-2` line.
- **Checkboxes**: crimson fill with a `--nf-on-neon` tick; keyboard focus rings the box (`0 0 0 2px ink-2, 0 0 0 4px neon`).

### Library toolbar
One capsule holding Play All (tube pill), shuffle, filter, sort, view and paging (34px round tinted buttons, 6 to 8px apart, never MUI's divided strips). The item count is a quiet chip, a 12% rim on the capsule's glass. The active-filter dot is crimson; the reset action `--nf-neon-text`. The A to Z rail is a solid `chrome-solid` pill, letters `--nf-text-2`, the active letter `--nf-neon-text` 700.

### Menus, dialogs, tooltips, toasts
- **Menus and action sheets**: menu glass at 14px on desktop pages; solid over video and on phones. Items round to 8px with an 8% hover wash; desktop MUI rows are 40px, phones keep finger-sized ones. Only the current choice is lit: a crimson check, or the selected pill on MUI items; other icons `--nf-text-2`. On phones a sheet rises full width from the bottom edge, top corners 14px.
- **Dialogs**: solid `ink-2`, 14px, dialog drop, a rim drawn over header and footer, over the page dimmed in ink. Full screen and small windows go square with no rim.
- **Tooltips and toasts**: small solid `chrome-deep` pills with a top rim.

### Player
No glass over video. Top and bottom bars sit on ink gradients Jellyfin fades by opacity. Icons white with a soft dark shadow. Sliders: crimson played part, white handle with a small drop. The scrub bubble is `chrome-deep` at 8px. The now-playing bar is `chrome-solid` with a top rim. The Up Next countdown is `--nf-neon-text`.

### Settings
Working pages: lists on `chrome-tint` at 12px, list icons on oxblood, headings semibold, the subtitle preview on an oxblood-to-ink gradient. Fields, checkboxes and buttons as above.

### Sign-in and user picker
One panel (menu glass desktop, solid phone, 14px) holds the form, other ways in and the disclaimer; the heading is a sign. A server splash stays sharp behind it at `brightness(0.4)`. Forgot password and the disclaimer step back to `--nf-text-2`; disclaimer links `--nf-neon-text`, underlined. The focused field label is `--nf-neon-text`. The user picker shows round oxblood tiles; focus is the ring, not the outline.

### Plugin surfaces (`skin/plugins/`)
- **Media Bar Enhanced** (`#slides-container`): the hero fades into ink at bottom and left (and under the capsules on desktop); Play a tube pill; Trailer, info, favourite and arrows round tinted, their plugin blur removed; dots at `light` 28%, active and progress fill crimson; the slide counter a tinted chip, and counter and progress line centred on screen. Interface face replaces the plugin's web font.
- **Home Screen Sections** (`.discoverCard-`): the media-type label becomes a quiet dark chip (`ink-2` 78%, rim).
- **Jellyfin Enhanced** (`.je-`, `.jellyseerr-`, `#jellyfin-enhanced-panel`): hands the plugin the palette through its theme variables (with `--blur: 0px`); header tray pills; flags at 3px with a hairline; its panel a solid `ink-2` dialog; Seerr type chips dark, Request a tube, status badges teal deepened for available, `--nf-neon-deep` for pending, dark for gone; ratings `--nf-text-2`; the calendar's active view the selected pill.

## Do's and Don'ts

### Do:
- **Do** take every colour from the nine inputs in `skin/00-tokens.css`, mixing with `color-mix(in srgb, ...)`; draw labels on the accent in `--nf-on-neon`.
- **Do** keep each picker contrast pair: text on ink 4.5:1; text-2 on ink 4.5:1; text-2 on chrome-deep 4.5:1; neon-text on chrome-deep 4.5:1; sign on ink 3:1; neon on ink 3:1; on-neon on neon 3:1; on-neon on neon-deep 4.5:1. Text over artwork gets an ink band so it passes AA over a white image.
- **Do** keep the focus ring visible everywhere: `outline: 2px solid var(--nf-neon) !important; outline-offset: 2px`, white on neon tubes, the card ring replacing it only where box shadows render (`forced-colors: none`).
- **Do** use `--nf-fast` (180ms) with `--nf-ease` (`cubic-bezier(0.2, 0.8, 0.2, 1)`) for hover and focus transitions, on colour, background, box-shadow or opacity only. The hero slideshow is the page's one moving element.
- **Do** honour `prefers-reduced-motion` (transitions and animations to 0.01ms, no card lift, the loading spinner left running) and `prefers-reduced-transparency`, `prefers-contrast: more` and `forced-colors: active` (every glass and phone-chrome surface turns solid `ink-2`).
- **Do** keep the built sheet at 60,000 bytes or less without the embedded font (`tests/test_build.py`), and judge every change against plain Jellyfin with the harness: never slower to render, navigate or scroll.
- **Do** scope plugin files: start with `/* plugin: <Name>; roots: <selector>, ... */` and select only under those roots; the only exception is a `:root` block handing the plugin's own variables the palette.
- **Do** write `-webkit-backdrop-filter` before `backdrop-filter`, both literal, on an allowlisted selector.

### Don't:
- **Don't** put glass on cards, in scrollers, on hover, over video, behind a dimmed dialog, or on phones.
- **Don't** give anything but Play and primary actions the neon tube or an outer glow; disabled and error buttons are plain pills.
- **Don't** use `@import`, `@font-face` (the build embeds the font), `will-change`, or `content` other than `""`.
- **Don't** select on emotion hash classes (`.css-xxxx`) or on `aria-label`; core files never select plugin roots, and plugin files never set `--nf-*` or `--jf-*`.
- **Don't** hide a Jellyfin or plugin function. Visually hiding a redundant label (My Media) keeps it for screen readers.
- **Don't** name a server, host, person or library item anywhere in the skin or its docs.
- **Don't** let a comment be all that separates two tokens: the build strips comments.
