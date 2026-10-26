"""The release workflow, and the committed release matching the version it claims."""

import pathlib
import subprocess

import pytest

import build

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
DIST = ROOT / "dist" / "neonfin.css"


def tracked(path: pathlib.Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel], capture_output=True).returncode == 0


def test_the_release_runs_every_check_ci_runs():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    checks = [line.split("uv run", 1)[1].strip() for line in ci.splitlines() if "run: uv run" in line]
    assert checks and [c for c in checks if c not in WORKFLOW.read_text()] == [], checks


def test_the_committed_stylesheet_is_the_release_of_the_current_version():
    if not tracked(DIST):
        pytest.skip("no release committed yet: dist/neonfin.css is not tracked")
    assert build.parse_header(DIST.read_text(encoding="utf-8")) == (build.version(), False)
