"""Check API login as the harness account and write harness/config.local.json.

Picks the first item by sort name in each slot, so reruns pick the same items; the player titles
are the first films that fit (pick_player_titles).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

from harness.config import config_path

CLIENT = 'MediaBrowser Client="neonfin-harness", Device="harness", DeviceId="neonfin-harness", Version="0.1"'


def merge_local(old: dict, found: dict) -> dict:
    """New item ids over the old file; every other key the developer set is kept."""
    return {**found, **{k: v for k, v in old.items() if k != "items"}}


def _streams(film: dict) -> tuple[dict, dict, dict]:
    source = (film.get("MediaSources") or [{}])[0]
    streams = source.get("MediaStreams", [])
    video = next((s for s in streams if s.get("Type") == "Video"), {})
    audio = next((s for s in streams if s.get("Type") == "Audio"), {})
    return source, video, audio


# HDR a browser is asked about as HDR. Dolby Vision alone is a different question, and a
# browser that cannot answer it makes the server convert for a reason that is not HDR.
HDR_TYPES = {"HDR10", "HDR10Plus", "HLG", "DOVIWithHDR10", "DOVIWithHDR10Plus", "DOVIWithHLG"}


def pick_player_titles(films: list[dict]) -> dict[str, str]:
    """The player measurement's two films, first in the order given (sort name), 720 lines or
    more: play_direct, an H.264 MP4 with AAC sound that any browser plays as is; play_hdr, an
    HEVC HDR10 or HLG film (Dolby Vision only with one of those under it), with AAC sound if
    one has it, so that only the picture can need converting."""
    direct = hdr = hdr_aac = None
    for film in films:
        source, video, audio = _streams(film)
        if (video.get("Height") or 0) < 720:
            continue
        containers = set((source.get("Container") or "").split(","))
        plain = video.get("Codec") == "h264" and video.get("VideoRange") == "SDR"
        if direct is None and plain and containers & {"mp4", "m4v", "mov"} and audio.get("Codec") == "aac":
            direct = film["Id"]
        if video.get("Codec") == "hevc" and video.get("VideoRangeType") in HDR_TYPES:
            hdr = hdr or film["Id"]
            if audio.get("Codec") == "aac":
                hdr_aac = hdr_aac or film["Id"]
    picked = {"play_direct": direct, "play_hdr": hdr_aac or hdr}
    return {k: v for k, v in picked.items() if v}


def main() -> int:
    local = config_path(os.environ)
    base = os.environ["JELLYFIN_URL"].rstrip("/")

    def call(path, body=None, token=None):
        auth = CLIENT + (f', Token="{token}"' if token else "")
        req = urllib.request.Request(
            base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": auth},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    auth = call("/Users/AuthenticateByName", {"Username": os.environ["JELLYFIN_THEME_USER"], "Pw": os.environ["JELLYFIN_THEME_PASSWORD"]})
    tok, uid = auth["AccessToken"], auth["User"]["Id"]
    views = call(f"/Users/{uid}/Views", token=tok)["Items"]
    lib = {v.get("CollectionType"): v["Id"] for v in views}

    def first(parent, kind):
        q = urllib.parse.urlencode(
            {"ParentId": parent, "IncludeItemTypes": kind, "Recursive": "true", "SortBy": "SortName", "Limit": 1, "userId": uid}
        )
        return call(f"/Items?{q}", token=tok)["Items"][0]["Id"]

    series = first(lib["tvshows"], "Series")
    season = call(f"/Shows/{series}/Seasons?userId={uid}", token=tok)["Items"][0]["Id"]
    episode = call(f"/Shows/{series}/Episodes?seasonId={season}&userId={uid}&limit=1", token=tok)["Items"][0]["Id"]
    data = {
        "items": {
            "user_id": uid,
            "movies_library": lib["movies"],
            "series_library": lib["tvshows"],
            "movie": first(lib["movies"], "Movie"),
            "series": series,
            "season": season,
            "playable": episode,
        },
        "search_term": "the",
        "volatile": ["#slides-container", "#randomItemButton .je-dice-face"],
    }
    q = urllib.parse.urlencode(
        {
            "ParentId": lib["movies"],
            "IncludeItemTypes": "Movie",
            "Recursive": "true",
            "SortBy": "SortName",
            "Fields": "MediaSources",
            "userId": uid,
        }
    )
    data["items"] |= pick_player_titles(call(f"/Items?{q}", token=tok)["Items"])
    data = merge_local(json.loads(local.read_text()) if local.exists() else {}, data)
    local.write_text(json.dumps(data, indent=2) + "\n")
    print(f"login ok; wrote {local.name} with {len(data['items'])} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
