"""Run configuration: secrets from the environment, server specifics from a local file."""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass, field

LOCAL = pathlib.Path(__file__).resolve().parent / "config.local.json"
ENV_KEYS = ("JELLYFIN_URL", "JELLYFIN_THEME_USER", "JELLYFIN_THEME_PASSWORD")
ITEM_KEYS = ("user_id", "movies_library", "series_library", "movie", "series", "season", "playable")
ROOT = LOCAL.parent.parent


def config_path(env=os.environ) -> pathlib.Path:
    """The server's local config: NEONFIN_CONFIG, relative to the repo root unless absolute,
    else harness/config.local.json. The neutrality terms stay in config.local.json whichever
    server is in use."""
    chosen = env.get("NEONFIN_CONFIG")
    if not chosen:
        return LOCAL
    path = pathlib.Path(chosen)
    return path if path.is_absolute() else ROOT / path


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    url: str
    user: str
    password: str
    items: dict[str, str]
    search_term: str = "the"
    volatile: list[str] = field(default_factory=list)


def load(env=os.environ, local_path: pathlib.Path | None = None) -> Config:
    local_path = local_path or config_path(env)
    missing = [k for k in ENV_KEYS if not env.get(k)]
    if missing:
        raise ConfigError(f"missing env {', '.join(missing)}; see DEVELOPMENT.md")
    if not local_path.exists():
        raise ConfigError(f"missing {local_path}; run `python -m harness.discover`")
    data = json.loads(local_path.read_text())
    absent = sorted(set(ITEM_KEYS) - set(data.get("items", {})))
    if absent:
        raise ConfigError(f"{local_path.name} items missing: {', '.join(absent)}")
    return Config(
        url=env["JELLYFIN_URL"].rstrip("/"),
        user=env["JELLYFIN_THEME_USER"],
        password=env["JELLYFIN_THEME_PASSWORD"],
        items=dict(data["items"]),
        search_term=data.get("search_term", "the"),
        volatile=list(data.get("volatile", [])),
    )
