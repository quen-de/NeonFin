"""Repository hygiene a public repository depends on."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_local_and_generated_files_are_ignored():
    ignored = (ROOT / ".gitignore").read_text().split()
    for entry in (".env", "dist/", "harness/runs/", "harness/config.local.json"):
        assert entry in ignored, entry


def test_licence_is_mit():
    assert (ROOT / "LICENSE").read_text().startswith("MIT License")
