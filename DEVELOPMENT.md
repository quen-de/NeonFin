# Developing NeonFin

## Setup

- Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and Google Chrome (the harness drives branded Chrome).
- `uv sync` installs the harness and the dev tools.

## Tests and lint

- `uv run pytest` runs the offline tests. CI runs the same.
- `uv run ruff check . && uv run ruff format --check .` lints.

## Hooks

`git config core.hooksPath .githooks` turns them on.

- `pre-commit` runs the offline tests.
- `commit-msg` rejects AI attribution trailers and any term from `neutrality_terms` in
  `harness/config.local.json`.

`harness/config.local.json` is gitignored. Its `neutrality_terms` list names what must never
appear in the repository: your server's name, host names, people, addresses. The neutrality
test checks every tracked file against it.

## The harness

The harness renders real pages of a Jellyfin 12 server with your local build injected, so
nothing is ever written to the server.

1. Create a dedicated Jellyfin user for it, then export:
   `JELLYFIN_URL`, `JELLYFIN_THEME_USER`, `JELLYFIN_THEME_PASSWORD`.
2. `uv run python -m harness.discover` writes `harness/config.local.json` with the items the
   routes need. It keeps any other keys you add (such as `neutrality_terms`).
3. `uv run python -m harness.run --label NAME --css dist` captures every route on desktop and
   phone into `harness/runs/NAME/` (`--css live` uses the server's own custom CSS).
4. `uv run python -m harness.compare harness/runs/A harness/runs/B` diffs two runs.

## Gates

A change is judged against plain Jellyfin on the same server, in the same plugin state:

    uv run python -m harness.run --label base --css vanilla --plugins all --trials 7
    uv run python -m harness.run --label skin --css dist --plugins all --trials 7
    uv run python -m harness.gates harness/runs/base harness/runs/skin --scope home

`--plugins` takes `all`, `none` or `without:<name>[,<name>]` (names in `harness/plugins.py`):
the harness aborts a plugin's requests so the page renders as if it were not installed.
`uv run python -m harness.sheet harness/runs/skin` writes a contact sheet per device.

## Live tests

`uv run pytest -m live` runs `tests/live/` against your server with the local build
injected (same env vars and local config as the harness). They are skipped without them,
and never run in CI or the pre-commit hook. Run them in their own pytest process: their
session-wide browser blocks the browsers the offline tests start for themselves.
