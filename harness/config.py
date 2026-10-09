"""Run configuration: secrets from the environment, server specifics from a local file."""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass, field

LOCAL = pathlib.Path(__file__).resolve().parent / "config.local.json"
ENV_KEYS = ("JELLYFIN_URL", "JELLYFIN_THEME_USER", "JELLYFIN_THEME_PASSWORD")
ITEM_KEYS = ("user_id", "movies_library", "series_library", "movie", "series", "season", "playable")


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


def load(env=os.environ, local_path: pathlib.Path = LOCAL) -> Config:
    missing = [k for k in ENV_KEYS if not env.get(k)]
    if missing:
        raise ConfigError(f"missing env {', '.join(missing)}; see DEVELOPMENT.md")
    if not local_path.exists():
        raise ConfigError(f"missing {local_path}; run `python -m harness.discover`")
    data = json.loads(local_path.read_text())
    absent = sorted(set(ITEM_KEYS) - set(data.get("items", {})))
    if absent:
        raise ConfigError(f"config.local.json items missing: {', '.join(absent)}")
    return Config(
        url=env["JELLYFIN_URL"].rstrip("/"),
        user=env["JELLYFIN_THEME_USER"],
        password=env["JELLYFIN_THEME_PASSWORD"],
        items=dict(data["items"]),
        search_term=data.get("search_term", "the"),
        volatile=list(data.get("volatile", [])),
    )
