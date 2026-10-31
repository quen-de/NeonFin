"""The demo server's definition: licences, the server pin, and what stays on this machine."""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"


def library() -> dict:
    return json.loads((DEMO / "library.json").read_text())


def plugin_plan() -> dict:
    return json.loads((DEMO / "plugins.json").read_text())


def test_one_demo_film_is_the_hdr_clip():
    assert sum(bool(m.get("hdr")) for m in library()["movies"]) == 1


def test_every_clip_plays_well_past_ten_seconds():
    # The player state pauses ten seconds in.
    lib = library()
    runtimes = [m["runtime_s"] for m in lib["movies"]] + [e["runtime_s"] for e in lib["series"]["episodes"]]
    assert all(r >= 60 for r in runtimes), runtimes


def test_every_plugin_comes_from_a_repository_it_names():
    plan = plugin_plan()
    repos = {r["name"] for r in plan["repositories"]}
    assert all(r["url"].startswith("https://") for r in plan["repositories"])
    for p in plan["plugins"]:
        assert p["repository"] in repos and p["styled"], p


def test_the_demo_server_is_pinned_and_reachable_from_this_machine_only():
    text = (DEMO / "compose.yml").read_text()
    # Jellyfin 12 images are tagged 12.<minor>.<build date>-<time>; 12.3 alone moves.
    assert re.search(r"^\s*image: jellyfin/jellyfin:12\.\d+\.\d{8}-\d{6}\s*$", text, re.M), text
    assert '"127.0.0.1:${DEMO_PORT:-8096}:8096"' in text


def test_demo_state_is_never_committed():
    ignored = set((ROOT / ".gitignore").read_text().split())
    assert {"demo/.data/", "demo/.env", "demo/config.json"} <= ignored
