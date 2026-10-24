# Developing NeonFin

## Setup

- Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and Google Chrome (the harness drives branded Chrome).
- `uv sync` installs the harness and the dev tools.

## Tests and lint

- `uv run pytest` runs the offline tests. CI runs the same.
- `uv run ruff check . && uv run ruff format --check .` lints.

## Hooks

`git config core.hooksPath .githooks` turns them on. They are the maintainer's checks; turn
them on if you want the same.

- `pre-commit` runs what CI runs: lint, format and the offline tests.
- `commit-msg` rejects AI attribution trailers, the maintainer's policy for this
  repository's history, and any term from `neutrality_terms` in `harness/config.local.json`.

`harness/config.local.json` is gitignored. Its `neutrality_terms` list names what must never
appear in the repository: your server's name, host names, people, addresses. The neutrality
test checks every tracked file against it.

## Skin rules

`python3 build.py` refuses a skin that breaks these, naming the file and line; the checks live
in `skinlint.py` and the offline tests run them too.

- Colours come from the palette in `skin/00-tokens.css`. No other file writes one out.
- Glass is literal, on the allowlist in `skinlint.py`, with `-webkit-backdrop-filter` first.
- No `@import`, no `@font-face` (the build embeds the font), no `will-change`, and `content`
  only as an empty string: the skin adds no visible text.
- Selectors never use an emotion hash class (it changes on every Jellyfin build) or
  `aria-label` (it is translated).
- The built sheet has no comments, so a comment can never be all that separates two tokens:
  `1px/* x */solid` fails.
- A plugin file in `skin/plugins/` starts with `/* plugin: <Name>; roots: <selector>, ... */`
  and selects only under those roots, and core files never select them. Its one exception is
  a `:root` block of custom properties, where it may hand its plugin's own variables the
  palette; it may not set the skin's `--nf-*` or Jellyfin's `--jf-*` tokens.
- A preset in `palettes/` starts with
  `/* NeonFin palette: <Name>. Paste after the skin in Custom CSS. */` and sets only the nine
  palette inputs, in hex. A new preset needs only its file: the picker offers every one.

## The harness

The harness renders real pages of a Jellyfin 12 server with your local build injected, so
nothing is ever written to the server.

1. Create a dedicated Jellyfin user for it, then export:
   `JELLYFIN_URL`, `JELLYFIN_THEME_USER`, `JELLYFIN_THEME_PASSWORD`; or use the demo server
   below, which does all of this.
2. `uv run python -m harness.discover` writes `harness/config.local.json` with the items the
   routes need. It keeps any other keys you add (such as `neutrality_terms`).
3. `uv run python -m harness.run --label NAME --css dist` captures every route on desktop and
   phone into `harness/runs/NAME/` (`--css live` uses the server's own custom CSS).
   The `picker` route shows the sign-in page's user picker with two made-up users that the
   harness answers itself from the first request on, so no request about real users reaches
   the server. Every page the harness opens refuses writes: a plugin's settings and Seerr
   requests, signing in by any route or out, the server's own writes a stray click could
   make (favourites, played marks, ratings, settings, playlists, item edits and deletes),
   and the dashboard's, live TV's and remote control's (`WRITES` in `harness/session.py`).
4. `uv run python -m harness.compare harness/runs/A harness/runs/B` diffs two runs.

## Gates

A change is judged against plain Jellyfin on the same server, in the same plugin state.
Speed comes from a paired bench, the other checks from capture-only runs:

    uv run python -m harness.bench --label speed --plugins all --plugins none
    uv run python -m harness.captures --label checks --plugins all --plugins none
    uv run python -m harness.gates --bench harness/runs/speed \
        harness/runs/checks-dist-all harness/runs/checks-dist-none --scope all

The bench alternates vanilla and skin trials in one process, so drift between runs cannot
tilt the comparison, and stops a cell (plugin state, profile, route) once its verdict is
clear, after at least four pairs; a close call gets the full seven. While iterating on one
cost, bench just that cell: `--profiles desktop --routes home`. `--bench` repeats in
`harness.gates`: benches of one build pool their pairs, so a borderline cell can be measured
further without losing the pairs it has. The gate passes only on complete evidence from one
committed build: every speed cell for all plugins on and off, a capture of every route for
each benched state, nothing built from uncommitted CSS. Accepted exceptions to the speed
ratios live in `harness/gates.py`, each with its own ceiling. A ratio fails only when the
skin's excess is also over a floor (25 ms of main-thread work over the scroll), and page ready
may run up to 50 ms past vanilla's slowest load: a page that does little work, like the demo's
ten-film grids, is not judged on a few milliseconds.

Captures are not timed, so `harness.captures` runs them side by side (`--jobs`, default 4).
Timed work runs alone, across every checkout on the machine: a timed run waits for captures to
finish and captures wait for it. Without file locks (Windows) the harness only warns.

`--plugins` takes `all`, `none` or `without:<name>[,<name>]` (names in `harness/plugins.py`),
and repeats for several states: the harness aborts a plugin's requests so the page renders
as if it were not installed. `harness.run` still captures and times one CSS mode in one go,
and `harness.gates VANILLA_RUN SKIN_RUN` still judges two such runs.
`uv run python -m harness.sheet harness/runs/skin` writes a contact sheet per device.

A route that cannot exist without a plugin (Jellyfin Enhanced's calendar and panel) is
skipped, not failed, in a state with that plugin off. A capture that finds its session ended
signs in again once and says so in the gate notes.

## Player timing

    uv run python -m harness.player --label player

Times the video player with the skin against plain Jellyfin, in pairs like the speed bench:
the first frame after Play, the controls coming back after a mouse move (a tap on phones), and
frames while they show. `python -m harness.discover` picks the films: an H.264 MP4 every
browser plays as is, and an HEVC HDR10 or HLG film, played once as the browser handles it and
once with HEVC hidden from the page so the server has to convert it. Playback reports stay swallowed, and
each trial ends its own conversion on the server. Nothing is gated; `player.json` keeps every
trial.

## Live tests

`uv run pytest -m live` runs `tests/live/` against your server with the local build
injected (same env vars and local config as the harness). They are skipped without them,
and never run in CI or the pre-commit hook. Run them in their own pytest process: their
session-wide browser blocks the browsers the offline tests start for themselves.

## Demo server

`uv run python demo/setup.py` brings up Jellyfin 12 in Docker on `127.0.0.1:8096`, with the
supported plugins and a library of Blender open movies (stand-in clips, TMDB metadata). It
writes the accounts' random passwords and an API key to `demo/.env` and the harness's items to
`demo/config.json`, both gitignored. Run anything against it in a subshell:

    ( set -a; . demo/.env; set +a; uv run pytest -m live )

`NEONFIN_CONFIG` in `demo/.env` points the harness at `demo/config.json`, so a config for
another server in `harness/config.local.json` is left alone; `neutrality_terms` are always
read from `harness/config.local.json`. Setup can be rerun at any time. `--port` picks another
port. To start over: `docker compose -f demo/compose.yml down`, then delete `demo/.data/`.

`uv run python -m harness.shots` retakes the README's screenshots on the demo server and
refuses any other.

## Releasing

`dist/neonfin.css` is the stylesheet of the latest release and changes only in release
commits; everything else builds into `build/`.

1. Set `version` in `pyproject.toml`. Move the entries under `## [Unreleased]` in
   `CHANGELOG.md` to a new `## [X.Y.Z] - YYYY-MM-DD` section, and put the version in the
   README's `@import` URL.
2. `uv run python build.py --release` writes `dist/neonfin.css`. It refuses a version with no
   CHANGELOG entries.
3. Check the other engines on the demo server, since the README says Firefox and Safari are
   checked at each release. Once: `uv run playwright install firefox webkit`. Then, in the
   demo's subshell, `uv run python -m harness.shots --engine firefox --out DIR` and
   `uv run python -m harness.shots --engine webkit --out DIR`, with `DIR` outside the
   repository, and look at every image for broken layout.
4. Commit "Release X.Y.Z" with those four files, tag it with
   `git tag -a vX.Y.Z -m "NeonFin X.Y.Z"`, and push the commit and the tag.

The tag runs `.github/workflows/release.yml`: the checks CI runs, the tag against the
version, the committed stylesheet against a fresh release build, then a GitHub Release with
`neonfin.css`, `palette.html` and the four presets. Asset names carry no version, so
`releases/latest/download/neonfin.css` always serves the latest release.
