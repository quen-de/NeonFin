# Contributing

## Reporting

Open an issue with the bug form: it asks for the Jellyfin and NeonFin versions, the browser,
the plugins, and a screenshot. Check first that the problem goes away with NeonFin removed
from Custom CSS; if it does not, it belongs to Jellyfin or a plugin.

## Fixing a style

1. Set up as in [DEVELOPMENT.md](DEVELOPMENT.md), and bring up the
   [demo server](DEVELOPMENT.md#demo-server).
2. Keep to the skin rules in DEVELOPMENT.md; the build refuses a skin that breaks them.
3. `uv run pytest` must pass, and the live tests on the demo where they cover your page.
4. In the pull request, show the page before and after, taken on the demo server.

The repository never names a particular server: screenshots, item ids, host names and user
names come from the demo server or nowhere.

Pull requests are squash-merged and the maintainer writes the final commit message, so your
branch's commit messages are yours. The repository's git hooks are opt-in (DEVELOPMENT.md).
