import json
import os
import pathlib
import subprocess
import sys

import pytest

HOOKS = pathlib.Path(__file__).resolve().parents[1] / ".githooks"


@pytest.fixture
def run_hook(tmp_path):
    cfg = tmp_path / "config.local.json"
    cfg.write_text(json.dumps({"neutrality_terms": ["acme-home"]}))

    def run(message: str) -> subprocess.CompletedProcess:
        msg = tmp_path / "COMMIT_EDITMSG"
        msg.write_text(message)
        return subprocess.run(
            [sys.executable, str(HOOKS / "commit-msg"), str(msg)],
            capture_output=True,
            text=True,
            env={**os.environ, "NEONFIN_LOCAL_CONFIG": str(cfg)},
        )

    return run


def test_plain_message_passes(run_hook):
    assert run_hook("Add the header capsules\n\nThey float over the page.\n").returncode == 0


@pytest.mark.parametrize(
    "trailer",
    [
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
        "co-authored-by: Some Bot <bot@anthropic.com>",
        "Claude-Session: https://claude.ai/code/session_abc",
    ],
)
def test_ai_trailers_are_rejected(run_hook, trailer):
    r = run_hook(f"Add x\n\n{trailer}\n")
    assert r.returncode == 1
    assert "AI attribution" in r.stderr


def test_human_co_author_passes(run_hook):
    assert run_hook("Add x\n\nCo-Authored-By: Jane Doe <jane@example.com>\n").returncode == 0


def test_instance_terms_are_rejected_case_insensitively(run_hook):
    r = run_hook("Fix the ACME-Home header\n")
    assert r.returncode == 1
    assert "instance term" in r.stderr


def test_git_comment_lines_are_ignored(run_hook):
    assert run_hook("Add x\n# Co-Authored-By: Claude\n").returncode == 0


def test_hooks_are_executable():
    for name in ("commit-msg", "pre-commit"):
        assert os.access(HOOKS / name, os.X_OK), name
