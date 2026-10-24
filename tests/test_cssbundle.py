import io
import json

from harness import cssbundle


def test_strip_imports_drops_every_import_and_keeps_rules():
    out = cssbundle.strip_imports('@import url("https://fonts.example/f.css");\n.a{x:1}\n')
    assert "@import" not in out and ".a{x:1}" in out


def test_strip_imports_without_imports_is_identity():
    assert cssbundle.strip_imports(".a{}") == ".a{}"


class Response(io.BytesIO):
    headers: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_a_server_without_custom_css_probes_as_empty(monkeypatch):
    # Jellyfin leaves unset fields out of its JSON: a fresh server sends no CustomCss at all.
    body = json.dumps({"SplashscreenEnabled": True}).encode()
    monkeypatch.setattr(cssbundle.urllib.request, "urlopen", lambda req, timeout: Response(body))
    assert cssbundle.probe_branding("http://server")["custom_css"] == ""
