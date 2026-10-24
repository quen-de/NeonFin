# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

People who watch a Jellyfin 12 server, in three typical groups:

- The person running the server, on desktop browsers (Safari, Chrome, Firefox), who also
  curates the library.
- Its regular viewers on phones: Chrome Android and the Jellyfin Android app (a WebView).
- Guests signing in from their own devices, who know Jellyfin less well.

Their jobs, in no fixed order: browse and discover (the home rows and the libraries),
continue watching, and search for a known title. Some playback happens in the web player.

## Product Purpose

NeonFin, a web skin for Jellyfin 12: one stylesheet that re-dresses jellyfin-web, built
fresh over vanilla Jellyfin.

Success means an interface that feels as finished as a commercial streaming service, with
glass that reads as glass, at a render, navigation and scrolling cost close to vanilla
Jellyfin's, measured on every change.

## Positioning

For personal libraries rather than a commercial service's licensed shelf: a server owner's
own collection, often in more than one language. It works on any Jellyfin 12 server and
carries no server's brand.

## Operating Context

- Delivered as Jellyfin's branding Custom CSS. It reaches desktop browsers, Chrome Android
  and the Jellyfin Android app. Native TV clients never load it, and Jellyfin 12 does not
  load it on the admin dashboard.
- Popular plugins compose much of a typical home page: Media Bar Enhanced (a hero
  slideshow), Home Screen Sections (configurable rows), Jellyfin Enhanced (language flags, a
  random pick, Seerr search and more), Custom Tabs and Plugin Pages. Any of them may be
  missing.
- Development renders real pages of a Jellyfin server with the local build (`harness/`),
  the demo server or any other, so a change is seen on real content before it ships.

## Capabilities and Constraints

- CSS only: no markup or JavaScript changes. Selectors anchor on stable class names, never
  on emotion hashes (`css-xxxx`), which change on every jellyfin-web rebuild.
- Jellyfin 12 mixes legacy `emby-*` components with MUI ones; both must be styled.
- Performance is a hard constraint. First render, route changes and scrolling stay fast
  and smooth on every target, and every effect justifies its cost, measured against
  vanilla Jellyfin with the harness.
- Targets: Safari, Chrome and Firefox on desktop; Chrome Android and the Android app's
  WebView on phones. TV is out of scope.
- No network fetches from the stylesheet itself: system fonts for the interface, one
  embedded display face, no `@import` inside the skin.

## Brand Commitments

- The skin carries no server brand. It frames whatever logo and name the server provides.
- Dark interface only; no light mode.
- Glass is the core material, done properly: translucent surfaces with something visible
  behind them.
- Crimson neon is the skin's accent, overridable through one token.
- Plugin features are styled when present and never hidden; the skin is complete without
  them.

## Evidence on Hand

- A demo server anyone can run (`demo/`): open movies with TMDB posters and backdrops, the
  supported plugins installed.
- Harness captures of every key page on desktop and phone, and paired performance runs of
  vanilla Jellyfin against the skin.
- No user research beyond the developer's own judgement, and no analytics.

## Product Principles

1. Speed is part of the look. An effect that costs render time or smooth scrolling does
   not ship.
2. Glass must read as glass: something visible behind it, never a tinted slab.
3. A guest who barely knows Jellyfin finds continue-watching and search without help.
4. Style what is there. Jellyfin and plugin features keep working, CSS never hides a
   function, and a missing plugin leaves no gap.
5. Generalist by default: nothing in the skin belongs to one server.
