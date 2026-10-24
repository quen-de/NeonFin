"""The release workflow, and the committed release matching the version it claims."""

import pathlib
import subprocess

import pytest

import build

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
DIST = ROOT / "dist" / "neonfin.css"
ASSETS = ("neonfin.css", "palette.html", "palettes/acid.css", "palettes/amber.css", "palettes/cyan.css", "palettes/violet.css")


def tracked(path: pathlib.Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel], capture_output=True).returncode == 0


def test_releases_are_built_and_checked_from_version_tags():
    text = WORKFLOW.read_text()
    assert 'tags: ["v*"]' in text and "contents: write" in text
    assert 'test "$GITHUB_REF_NAME" = "v$version"' in text
    assert 'cmp "$RUNNER_TEMP/neonfin.css" dist/neonfin.css' in text
    assert "build.py --notes" in text and "gh release create" in text
    assert [a for a in ASSETS if a not in text] == []


def test_the_release_runs_every_check_ci_runs():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    checks = [line.split("uv run", 1)[1].strip() for line in ci.splitlines() if "run: uv run" in line]
    assert checks and [c for c in checks if c not in WORKFLOW.read_text()] == [], checks


def test_the_committed_stylesheet_is_the_release_of_the_current_version():
    if not tracked(DIST):
        pytest.skip("no release committed yet: dist/neonfin.css is not tracked")
    assert build.parse_header(DIST.read_text(encoding="utf-8")) == (build.version(), False)


def test_the_readme_installs_the_committed_release():
    if not tracked(DIST):
        pytest.skip("no release committed yet: dist/neonfin.css is not tracked")
    ident, _ = build.parse_header(DIST.read_text(encoding="utf-8"))
    assert f"cdn.jsdelivr.net/gh/quen-de/NeonFin@v{ident}/dist/neonfin.css" in (ROOT / "README.md").read_text()


def test_the_release_steps_include_the_browser_check_the_readme_promises():
    # The README says Firefox and Safari are checked at each release.
    steps = (ROOT / "DEVELOPMENT.md").read_text().split("## Releasing", 1)[1]
    assert "playwright install firefox webkit" in steps
    for engine in ("firefox", "webkit"):
        assert f"harness.shots --engine {engine} --out" in steps, engine
