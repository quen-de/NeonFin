import http.server
import json
import threading

import pytest

from harness import run


@pytest.fixture
def server():
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append((self.path, self.headers.get("Authorization")))
            body = json.dumps([{"Name": "B", "Version": "2.0.0.0"}, {"Name": "A", "Version": "1.0.0.0"}]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}", seen
    httpd.shutdown()


def test_runs_record_plugin_versions_with_the_admin_key(server):
    url, seen = server
    assert run.plugin_versions(url, "k") == {"A": "1.0.0.0", "B": "2.0.0.0"}
    assert seen == [("/Plugins", 'MediaBrowser Token="k"')]


def test_without_a_key_plugin_versions_are_unknown(server):
    url, seen = server
    assert run.plugin_versions(url, None) == "unknown" and seen == []


def test_an_unreachable_server_leaves_plugin_versions_unknown():
    assert run.plugin_versions("http://127.0.0.1:9", "k") == "unknown"
