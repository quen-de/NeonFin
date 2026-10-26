"""Repository hygiene a public repository depends on."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_local_and_generated_files_are_ignored():
    ignored = (ROOT / ".gitignore").read_text().split()
    for entry in (".env", "build/", "harness/runs/", "harness/config.local.json"):
        assert entry in ignored, entry
    # The release build is committed, so jsDelivr can serve it from the tag.
    assert "dist/" not in ignored
