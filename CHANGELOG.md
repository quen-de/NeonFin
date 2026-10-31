# Changelog

NeonFin follows [semantic versioning](https://semver.org). A major release renames or removes
a palette token, or moves to a new Jellyfin major version. A minor release styles new pages
or plugins. A patch fixes what is already styled.

## [Unreleased]

## [1.1.0] - 2026-10-31

### Added

- A row with more cards than the screen holds fades out at the screen's edge, a hint that it
  scrolls on; the fade lifts at the row's end. On phones it needs scroll-driven animations
  (Chrome, the Android app, Safari 26), so Firefox on a phone shows the row without it.

### Fixed

- On a short phone, Media Bar Enhanced's progress bar no longer sits against the Play button,
  and a details line that wraps no longer runs into the genres.
- Links that plugins add to the phone drawer line up with Jellyfin's own and stay inside it:
  Jellyfin Enhanced's no longer clip at its edge, and Media Bar Enhanced's no longer make it
  scroll sideways.
- A custom tab, which Jellyfin draws without an icon, takes a plain tab icon in the header and
  the drawer.
- The trailer volume control Media Bar Enhanced 3.11 added beside its mute button is tinted
  and filled in the accent, instead of blurred and Jellyfin blue.

## [1.0.0] - 2026-10-25

### Added

- The skin for Jellyfin 12's modern layout: the header's glass capsules and menus, home rows
  and cards, title pages, libraries and their toolbar, search, dialogs, tooltips and toasts,
  the player's controls, the settings pages, and the sign-in page with its user picker.
- Styles for Media Bar Enhanced, Home Screen Sections and Jellyfin Enhanced; tested alongside
  Custom Tabs and Plugin Pages.
- A palette of nine tokens, four presets (Cyan neon, Amber, Violet, Acid green) and a picker
  page that checks readability and writes the block to paste.
- Solid surfaces and still motion when the system asks for less transparency, more contrast,
  forced colours or less motion.
