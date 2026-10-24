"""demo/setup.py's own logic; Task 8 runs it against a real server."""

import importlib.util
import pathlib
import stat
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("demo_setup", ROOT / "demo" / "setup.py")
setup = importlib.util.module_from_spec(spec)
sys.modules["demo_setup"] = setup  # dataclasses look their module up while the class is made
spec.loader.exec_module(setup)

LIBRARY = {
    "movies": [
        {"title": "Agent 327: Operation Barbershop", "year": 2017, "runtime_s": 231},
        {"title": "Cosmos Laundromat", "year": 2015, "runtime_s": 730, "hdr": True},
    ],
    "series": {
        "title": "Caminandes",
        "year": 2013,
        "episodes": [{"season": 1, "episode": 1, "title": "Llama Drama", "year": 2013, "runtime_s": 90}],
    },
}


def test_clips_are_named_the_way_jellyfin_matches_them():
    assert [c.path for c in setup.clips(LIBRARY)] == [
        "Movies/Agent 327 Operation Barbershop (2017)/Agent 327 Operation Barbershop (2017).mp4",
        "Movies/Cosmos Laundromat (2015)/Cosmos Laundromat (2015).mp4",
        "Shows/Caminandes (2013)/Season 01/Caminandes - S01E01 - Llama Drama.mp4",
    ]
    assert [c.hdr for c in setup.clips(LIBRARY)] == [False, True, False]


def test_the_hdr_clip_is_hevc_hdr10_and_the_rest_h264():
    plain, hdr, _ = setup.clips(LIBRARY)
    a, b = setup.ffmpeg_args(plain, "/work/c.png", "/work/o.mp4"), setup.ffmpeg_args(hdr, "/work/c.png", "/work/o.mp4")
    assert "libx264" in a and "yuv420p" in a and "libx265" not in a
    assert "libx265" in b and "smpte2084" in b and "bt2020nc" in b and "yuv420p10le" in b
    assert a[a.index("-t") + 1] == "231" and a[-1] == "/work/o.mp4" and "aac" in a


def test_the_image_comes_from_compose():
    assert setup.image("services:\n  jellyfin:\n    image: jellyfin/jellyfin:12.2.1\n") == "jellyfin/jellyfin:12.2.1"
    with pytest.raises(setup.SetupError, match="names no image"):
        setup.image("services: {}\n")


def test_credentials_survive_a_rerun(tmp_path):
    first = setup.credentials({}, 8096)
    path = tmp_path / ".env"
    setup.write_env(first, path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    again = setup.credentials(setup.read_env(path), 8096)
    assert again == first
    assert first["JELLYFIN_THEME_PASSWORD"] != first["DEMO_ADMIN_PASSWORD"] and len(first["DEMO_ADMIN_PASSWORD"]) >= 20
    assert first["NEONFIN_CONFIG"] == "demo/config.json" and first["JELLYFIN_URL"] == "http://127.0.0.1:8096"


# Jellyfin 12 still loads plugins built for 10.11: Media Bar Enhanced ships no other build.
@pytest.mark.parametrize(
    ("abi", "server", "ok"),
    [
        ("12.2.0.0", "12.2.1", True),
        ("12.0.0.0", "12.2.1", True),
        ("10.11.0.0", "12.2.1", True),
        ("10.10.7.0", "12.2.1", False),
        ("12.3.0.0", "12.2.1", False),
        ("", "12.2.1", False),
    ],
)
def test_a_plugin_build_fits_from_the_abi_jellyfin_12_continues_up_to_this_server(abi, server, ok):
    assert setup.abi_ok(abi, server) is ok


class Plugins:
    def __init__(self, rows):
        self.rows = rows

    def call(self, method, path, body=None):
        assert (method, path) == ("GET", "/Plugins")
        return self.rows


def test_a_pinned_plugin_that_did_not_load_is_named():
    admin = Plugins([{"Name": "A", "Status": "Active"}, {"Name": "B", "Status": "NotSupported"}])
    plan = {"plugins": [{"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"}]}
    assert setup.not_active(admin, plan, skipped={"D"}) == ["B: NotSupported", "C: not installed"]


def test_the_series_gets_nfo_files_so_names_and_order_hold_without_tmdb():
    files = setup.nfo_files(LIBRARY)
    assert "<title>Caminandes</title>" in files["Shows/Caminandes (2013)/tvshow.nfo"]
    ep = files["Shows/Caminandes (2013)/Season 01/Caminandes - S01E01 - Llama Drama.nfo"]
    assert "<title>Llama Drama</title>" in ep and "<season>1</season>" in ep and "<episode>1</episode>" in ep


def test_a_title_card_is_full_hd_and_not_blank():
    im = setup.title_card("Sintel")
    assert im.size == (1920, 1080) and any(lo != hi for lo, hi in im.getextrema())


def test_an_unreachable_server_fails_with_a_hint():
    with pytest.raises(setup.SetupError, match="never reported healthy; is Docker running and the port free"):
        setup.wait_healthy("http://127.0.0.1:9", timeout_s=0.5, step_s=0.1)


def test_main_reports_a_missing_docker(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(setup, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(setup, "DATA", tmp_path / ".data")
    monkeypatch.setenv("PATH", str(tmp_path))  # no docker on it
    assert setup.main([]) == 1
    assert capsys.readouterr().err.startswith("setup: docker not found")
