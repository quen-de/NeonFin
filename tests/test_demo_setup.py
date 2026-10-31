"""demo/setup.py's own logic; Task 8 runs it against a real server."""

import importlib.util
import json
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


def test_a_plugin_that_did_not_load_is_named():
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


def test_main_names_the_likely_cause_when_compose_cannot_start(tmp_path, monkeypatch, capsys):
    # Docker stopped or the port taken: compose itself fails, before any health check.
    monkeypatch.setattr(setup, "ENV_FILE", tmp_path / ".env")
    monkeypatch.setattr(setup, "DATA", tmp_path / ".data")
    docker = tmp_path / "docker"
    docker.write_text("#!/bin/sh\nexit 1\n")
    docker.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert setup.main(["--port", "8123"]) == 1
    last = capsys.readouterr().err.strip().splitlines()[-1]
    assert last.startswith("setup: docker compose could not start the demo") and "port 8123" in last and "--port" in last, last


def test_the_series_gets_drawn_art_since_tmdb_has_none():
    art = setup.series_art(LIBRARY)
    assert {k: v.size for k, v in art.items()} == {
        "Shows/Caminandes (2013)/poster.jpg": (1000, 1500),
        "Shows/Caminandes (2013)/backdrop.jpg": (1920, 1080),
        "Shows/Caminandes (2013)/season01-poster.jpg": (1000, 1500),
    }


def test_every_clip_gets_english_and_french_subtitles_so_track_menus_have_choices():
    files = setup.subtitle_files(LIBRARY)
    stems = [c.path.removesuffix(".mp4") for c in setup.clips(LIBRARY)]
    assert sorted(files) == sorted(f"{s}.{lang}.srt" for s in stems for lang in ("en", "fr"))
    srt = files["Movies/Cosmos Laundromat (2015)/Cosmos Laundromat (2015).en.srt"]
    assert srt.startswith("1\n00:00:01,000 --> 00:00:06,000\n") and "Cosmos Laundromat" in srt


def test_the_series_names_its_director_so_its_page_has_a_crew():
    series = {**LIBRARY["series"], "director": "Pablo Vazquez"}
    show = setup.nfo_files({**LIBRARY, "series": series})["Shows/Caminandes (2013)/tvshow.nfo"]
    assert "<director>Pablo Vazquez</director>" in show
    assert "<director>" not in setup.nfo_files(LIBRARY)["Shows/Caminandes (2013)/tvshow.nfo"]


class Branding:
    def __init__(self, conf):
        self.conf, self.posted = conf, None

    def call(self, method, path, body=None):
        assert path == "/System/Configuration/branding"
        if method == "POST":
            self.posted = body
        return self.conf


def test_sign_in_shows_the_splash_screen():
    api = Branding({"LoginDisclaimer": "", "SplashscreenEnabled": False})
    setup.show_splash(api)
    assert api.posted == {"LoginDisclaimer": "", "SplashscreenEnabled": True}
    on = Branding({"SplashscreenEnabled": True})
    setup.show_splash(on)
    assert on.posted is None


def test_the_demo_searches_a_term_its_library_answers(tmp_path, monkeypatch):
    # "in" finds films (Sintel, Spring, Wing It!), the series and people; the example's "the"
    # finds only two people here.
    monkeypatch.setattr(setup, "CONFIG", tmp_path / "config.json")
    setup.write_config()
    conf = json.loads((tmp_path / "config.json").read_text())
    assert conf["search_term"] == "in" and conf["volatile"]


def test_the_calendar_tab_is_added_once_beside_any_other_tab():
    other = {"Title": "Requests", "ContentHtml": "<div></div>"}
    once = setup.with_calendar_tab({"Tabs": [other]})
    assert setup.with_calendar_tab(once) == once
    assert once["Tabs"] == [other, setup.CALENDAR_TAB]


def test_a_plugin_installs_as_its_newest_build_for_this_server():
    builds = [
        {"version": "3.9.0.0", "targetAbi": "12.2.0.0"},
        {"version": "3.11.1.0", "targetAbi": "12.2.0.0"},
        {"version": "3.12.0.0", "targetAbi": "12.3.0.0"},
        {"version": "3.10.0.0", "targetAbi": "10.11.0.0"},
    ]
    assert setup.newest_build({"versions": builds}, "12.2.1")["version"] == "3.11.1.0"
    assert setup.newest_build({"versions": [{"version": "1.0.0.0", "targetAbi": "10.10.0.0"}]}, "12.2.1") is None
    assert setup.newest_build({}, "12.2.1") is None


class Catalogue:
    """A server with plugins installed and a catalogue of builds, recording what setup installs."""

    def __init__(self, installed, builds):
        self.installed, self.builds, self.posted = installed, builds, []

    def call(self, method, path, body=None):
        if path == "/Repositories":
            return [] if method == "GET" else None
        if path == "/Plugins":
            return [{"Name": n, "Version": v} for n, v in self.installed.items()]
        if path == "/Packages":
            return [{"name": n, "guid": n, "versions": vs} for n, vs in self.builds.items()]
        self.posted.append(path)


def test_setup_brings_each_plugin_to_its_newest_build_and_never_back():
    fits = lambda *vs: [{"version": v, "targetAbi": "12.2.0.0", "repositoryUrl": "https://r"} for v in vs]  # noqa: E731
    admin = Catalogue(
        installed={"Ahead": "2.1.0.0", "Behind": "1.0.0.0"},
        builds={"Ahead": fits("2.0.0.0"), "Behind": fits("1.0.0.0", "1.2.0.0"), "Missing": fits("0.3.3.0"), "Old": []},
    )
    plan = {"repositories": [], "plugins": [{"name": n} for n in ("Ahead", "Behind", "Missing", "Old")]}
    done, skipped = setup.ensure_plugins(admin, plan, "12.2.1")
    assert done == ["Behind 1.2.0.0", "Missing 0.3.3.0"] and skipped == ["Old"]
    assert [p.split("?")[0] for p in admin.posted] == ["/Packages/Installed/Behind", "/Packages/Installed/Missing"]
