"""Repository hygiene a public repository depends on."""

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_local_and_generated_files_are_ignored():
    ignored = (ROOT / ".gitignore").read_text().split()
    for entry in (".env", "build/", "harness/runs/", "harness/config.local.json"):
        assert entry in ignored, entry
    # The release build is committed, so jsDelivr can serve it from the tag.
    assert "dist/" not in ignored


def test_licence_is_mit():
    assert (ROOT / "LICENSE").read_text().startswith("MIT License")


# Built from parts, so that this file does not match itself.
DEAD = re.compile("(?i)" + r"\bspec(?:'s)?\s+(?:section\s+)?\d" + "|" + r"\bspec" + "'s" + r"\b" + "|" + r"\bmile" + r"stones?\b")


def tracked_text() -> dict[str, str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True).stdout.decode()
    texts = {}
    for rel in filter(None, out.split("\0")):
        try:
            texts[rel] = (ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return texts


def test_nothing_points_to_private_planning_documents():
    found = {rel: [n for n, line in enumerate(text.splitlines(), 1) if DEAD.search(line)] for rel, text in tracked_text().items()}
    assert {rel: lines for rel, lines in found.items() if lines and rel != "CHANGELOG.md"} == {}
