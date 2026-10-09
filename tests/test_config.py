import json

import pytest

from harness import config, run

ENV = {"JELLYFIN_URL": "http://jf.test:8096/", "JELLYFIN_THEME_USER": "u", "JELLYFIN_THEME_PASSWORD": "p"}
ITEMS = {k: "x" for k in ("user_id", "movies_library", "series_library", "movie", "series", "season", "playable")}


def test_load_reads_env_and_local(tmp_path):
    local = tmp_path / "c.json"
    local.write_text(json.dumps({"items": ITEMS, "volatile": [".v"]}))
    cfg = config.load(ENV, local)
    assert cfg.url == "http://jf.test:8096"
    assert cfg.search_term == "the" and cfg.volatile == [".v"]


def test_load_names_missing_env(tmp_path):
    with pytest.raises(config.ConfigError, match="JELLYFIN_THEME_PASSWORD"):
        config.load({k: v for k, v in ENV.items() if k != "JELLYFIN_THEME_PASSWORD"}, tmp_path / "c.json")


def test_load_names_missing_items(tmp_path):
    local = tmp_path / "c.json"
    local.write_text(json.dumps({"items": {"movie": "x"}}))
    with pytest.raises(config.ConfigError, match="playable"):
        config.load(ENV, local)


def test_load_requires_user_id(tmp_path):
    # Jellyfin 12.1's preference pages render nothing without ?userId=.
    local = tmp_path / "c.json"
    local.write_text(json.dumps({"items": {k: v for k, v in ITEMS.items() if k != "user_id"}}))
    with pytest.raises(config.ConfigError, match="user_id"):
        config.load(ENV, local)


def test_prepare_outdir_refuses_existing(tmp_path):
    run.prepare_outdir(tmp_path, "baseline")
    with pytest.raises(FileExistsError):
        run.prepare_outdir(tmp_path, "baseline")
