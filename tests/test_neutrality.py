"""Nothing tracked may name the development server, its owner or their setup.

The denylist is itself instance-specific, so it lives in the gitignored
harness/config.local.json under "neutrality_terms"; without it these tests skip.
"""

import json
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCAL = ROOT / "harness" / "config.local.json"


def neutrality_terms() -> list[str]:
    if not LOCAL.exists():
        pytest.skip("no harness/config.local.json")
    terms = json.loads(LOCAL.read_text()).get("neutrality_terms") or []
    if not terms:
        pytest.skip("no neutrality_terms in harness/config.local.json")
    return [t.lower() for t in terms]


def hits(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return sorted({t for t in terms if t in low})


def repository_files() -> list[pathlib.Path]:
    """Tracked files plus untracked ones that are not ignored (about to be committed)."""
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"], capture_output=True, check=True
    ).stdout
    return [ROOT / p for p in out.decode().split("\0") if p]


def test_repository_files_name_nothing_from_the_instance():
    terms = neutrality_terms()
    found = {}
    for path in repository_files():
        rel = path.relative_to(ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            text = ""
        h = hits(text + "\n" + rel, terms)
        if h:
            found[rel] = h
    assert not found, f"instance terms in: {found}"
