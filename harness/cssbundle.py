"""The CSS a run is measured against, and what a browser downloads to get it."""

from __future__ import annotations

import json
import urllib.request

from cssscan import split_imports


def strip_imports(css: str) -> str:
    """The CSS without its @import statements: imported sheets (web fonts) carry no selectors to match."""
    return split_imports(css)[1]


def probe_branding(base: str) -> dict:
    """What a browser downloads to get the custom CSS, and the CSS itself."""
    url = f"{base}/Branding/Configuration"
    wire = urllib.request.Request(url, headers={"Accept-Encoding": "gzip, br"})
    with urllib.request.urlopen(wire, timeout=30) as r:
        wire_bytes = len(r.read())
        encoding = r.headers.get("Content-Encoding", "identity")
    with urllib.request.urlopen(url, timeout=30) as r:
        custom_css = json.loads(r.read()).get("CustomCss") or ""
    return {"wire_bytes": wire_bytes, "encoding": encoding, "custom_css": custom_css}
