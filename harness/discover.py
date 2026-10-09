"""Check API login as the harness account and write harness/config.local.json.

Picks the first item by sort name in each slot, so reruns pick the same items.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

from harness.config import LOCAL

CLIENT = 'MediaBrowser Client="neonfin-harness", Device="harness", DeviceId="neonfin-harness", Version="0.1"'


def merge_local(old: dict, found: dict) -> dict:
    """New item ids over the old file; every other key the developer set is kept."""
    return {**found, **{k: v for k, v in old.items() if k != "items"}}


def main() -> int:
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
    data = merge_local(json.loads(LOCAL.read_text()) if LOCAL.exists() else {}, data)
    LOCAL.write_text(json.dumps(data, indent=2) + "\n")
    print(f"login ok; wrote {LOCAL.name} with {len(data['items'])} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
