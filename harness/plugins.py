"""Plugins the skin supports, and how the harness switches them off.

A plugin is off when the browser never loads anything it serves: every request
under its URL prefixes is aborted, so its scripts never run and the page renders
as on a server without it.
"""

from __future__ import annotations

from urllib.parse import urlsplit

PLUGINS: dict[str, tuple[str, ...]] = {
    "media-bar": ("/MediaBar/",),
    "media-bar-enhanced": ("/MediaBarEnhanced/",),
    "home-screen-sections": ("/HomeScreen/",),
    "jellyfin-enhanced": ("/JellyfinEnhanced/",),
    "custom-tabs": ("/CustomTabs/",),
    "plugin-pages": ("/PluginPages/",),
}


class PluginStateError(ValueError):
    pass


def parse_state(spec: str) -> frozenset[str]:
    """The plugins switched off by a state: all (none off), none (all off) or without:<name>[,<name>]."""
    if spec == "all":
        return frozenset()
    if spec == "none":
        return frozenset(PLUGINS)
    if spec.startswith("without:"):
        names = frozenset(n.strip() for n in spec.removeprefix("without:").split(",") if n.strip())
        unknown = sorted(names - PLUGINS.keys())
        if unknown or not names:
            raise PluginStateError(f"unknown plugins {', '.join(unknown) or '(none given)'}; known: {', '.join(PLUGINS)}")
        return names
    raise PluginStateError(f"plugin state is all, none or without:<names>, not {spec!r}")


def blocks(url: str, off: frozenset[str]) -> bool:
    path = urlsplit(url).path
    return any(prefix in path for name in off for prefix in PLUGINS[name])
