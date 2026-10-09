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
