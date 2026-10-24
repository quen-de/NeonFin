#!/usr/bin/env python3
"""Bring up the demo server: Jellyfin 12 with the supported plugins and a library of Blender
open movies, reachable from this machine only. Rerun it at any time; finished steps are
skipped and the passwords kept.

    uv run python demo/setup.py
    ( set -a; . demo/.env; set +a; uv run pytest -m live )

Reset: docker compose -f demo/compose.yml down, then delete demo/.data/ yourself.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

DEMO = pathlib.Path(__file__).resolve().parent
ROOT = DEMO.parent
DATA = DEMO / ".data"
ENV_FILE = DEMO / ".env"
CONFIG = DEMO / "config.json"
COMPOSE = DEMO / "compose.yml"
CLIENT = 'MediaBrowser Client="neonfin-demo", Device="setup", DeviceId="neonfin-demo-setup", Version="1.0"'
ADMIN, VIEWER, KEY_APP = "admin", "demo", "neonfin-demo"
FFMPEG = "/usr/lib/jellyfin-ffmpeg/ffmpeg"
OLDEST_ABI = (10, 11)
SEARCH_TERM = "in"
LIBRARIES = (("Movies", "movies", "/media/Movies"), ("Shows", "tvshows", "/media/Shows"))
HDR10 = (
    "hdr10=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc"
    ":master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400:keyint=600"
)


class SetupError(RuntimeError):
    pass


@dataclass(frozen=True)
class Clip:
    path: str  # under the media folder
    title: str
    seconds: int
    hdr: bool = False


def safe(name: str) -> str:
    """A file name every file system takes and Jellyfin still matches."""
    return re.sub(r"\s+", " ", re.sub(r'[<>:"/\\|?*]', "", name)).strip()


def show_dir(series: dict) -> str:
    return f"Shows/{safe(series['title'])} ({series['year']})"


def episode_stem(series: dict, e: dict) -> str:
    return (
        f"{show_dir(series)}/Season {e['season']:02d}/{safe(series['title'])} - S{e['season']:02d}E{e['episode']:02d} - {safe(e['title'])}"
    )


def clips(library: dict) -> list[Clip]:
    out = []
    for m in library["movies"]:
        name = safe(f"{m['title']} ({m['year']})")
        out.append(Clip(f"Movies/{name}/{name}.mp4", m["title"], m["runtime_s"], bool(m.get("hdr"))))
    s = library["series"]
    out += [Clip(episode_stem(s, e) + ".mp4", e["title"], e["runtime_s"]) for e in s["episodes"]]
    return out


def nfo_files(library: dict) -> dict[str, str]:
    """NFO files for the series, so its names and order hold whether or not TMDB knows it."""
    s = library["series"]
    crew = f"<director>{s['director']}</director>" if s.get("director") else ""
    out = {f"{show_dir(s)}/tvshow.nfo": f"<tvshow><title>{s['title']}</title><year>{s['year']}</year>{crew}</tvshow>\n"}
    for e in s["episodes"]:
        out[episode_stem(s, e) + ".nfo"] = (
            f"<episodedetails><title>{e['title']}</title><season>{e['season']}</season>"
            f"<episode>{e['episode']}</episode><year>{e['year']}</year></episodedetails>\n"
        )
    return out


def subtitle_files(library: dict) -> dict[str, str]:
    """English and French subtitles beside every clip, so the title page's track selects and the
    player's subtitle menu have choices to show."""
    out = {}
    for clip in clips(library):
        for lang in ("en", "fr"):
            out[f"{clip.path.removesuffix('.mp4')}.{lang}.srt"] = f"1\n00:00:01,000 --> 00:00:06,000\n{clip.title}\n"
    return out


def title_card(title: str, size: tuple[int, int] = (1920, 1080)) -> Image.Image:
    """The stand-in's only picture: the title, light on the skin's dark ink."""
    im = Image.new("RGB", size, (9, 11, 18))
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=96)
    left, top, right, bottom = draw.textbbox((0, 0), title, font=font)
    draw.text(((size[0] - (right - left)) / 2, (size[1] - (bottom - top)) / 2), title, font=font, fill=(246, 243, 240))
    return im


def series_art(library: dict) -> dict[str, Image.Image]:
    """Poster, backdrop and season poster for the series, drawn like the title cards: TMDB lists
    no Caminandes series, and a library of blank tiles shows nothing of the skin."""
    s = library["series"]
    poster, backdrop = title_card(s["title"], (1000, 1500)), title_card(s["title"])
    seasons = sorted({e["season"] for e in s["episodes"]})
    out = {f"{show_dir(s)}/poster.jpg": poster, f"{show_dir(s)}/backdrop.jpg": backdrop}
    return out | {f"{show_dir(s)}/season{n:02d}-poster.jpg": title_card(f"Season {n}", (1000, 1500)) for n in seasons}


def ffmpeg_args(clip: Clip, card: str, out: str) -> list[str]:
    """The title card held for the film's runtime with silent stereo AAC: H.264 SDR, or HEVC
    HDR10 for the HDR title."""
    head = ["-y", "-v", "error", "-loop", "1", "-framerate", "24", "-i", card]
    head += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-t", str(clip.seconds)]
    if clip.hdr:
        video = ["-c:v", "libx265", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p10le", "-x265-params", HDR10]
        video += ["-color_primaries", "bt2020", "-color_trc", "smpte2084", "-colorspace", "bt2020nc", "-tag:v", "hvc1"]
    else:
        video = ["-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "30", "-pix_fmt", "yuv420p", "-g", "600"]
    return head + video + ["-c:a", "aac", "-b:a", "16k", "-shortest", "-movflags", "+faststart", out]


def image(compose_text: str) -> str:
    m = re.search(r"^\s*image:\s*(\S+)", compose_text, re.M)
    if not m:
        raise SetupError("demo/compose.yml names no image")
    return m[1]


def read_env(path: pathlib.Path = ENV_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line and not line.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def write_env(values: dict[str, str], path: pathlib.Path = ENV_FILE) -> None:
    body = "# The demo server's local test credentials, written by demo/setup.py. Never commit.\n"
    body += "".join(f"{k}={v}\n" for k, v in values.items())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(body)
    os.chmod(path, 0o600)


def credentials(old: dict[str, str], port: int) -> dict[str, str]:
    """Passwords and the key kept from an earlier run, new random passwords otherwise."""
    return {
        "JELLYFIN_URL": f"http://127.0.0.1:{port}",
        "JELLYFIN_THEME_USER": VIEWER,
        "JELLYFIN_THEME_PASSWORD": old.get("JELLYFIN_THEME_PASSWORD") or secrets.token_urlsafe(18),
        "DEMO_ADMIN_USER": ADMIN,
        "DEMO_ADMIN_PASSWORD": old.get("DEMO_ADMIN_PASSWORD") or secrets.token_urlsafe(18),
        "JELLYFIN_API_KEY": old.get("JELLYFIN_API_KEY", ""),
        "NEONFIN_CONFIG": "demo/config.json",
    }


def version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def abi_ok(target_abi: str, server: str) -> bool:
    """A plugin build fits when it targets no later version than this server and no earlier ABI
    than 10.11, the one Jellyfin 12 continues: Media Bar Enhanced ships only 10.11 builds, and
    Jellyfin 12 loads them."""
    t = version_tuple(target_abi)
    return bool(t) and OLDEST_ABI <= t <= version_tuple(server)


class Api:
    def __init__(self, base: str, token: str | None = None):
        self.base, self.token = base.rstrip("/"), token

    def call(self, method: str, path: str, body=None):
        auth = CLIENT + (f', Token="{self.token}"' if self.token else "")
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            self.base + path, data=data, method=method, headers={"Authorization": auth, "Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read()
        except urllib.error.HTTPError as e:
            raise SetupError(f"{method} {path.split('?')[0]}: HTTP {e.code}") from None
        return json.loads(text) if text.strip() else None


def wait_healthy(base: str, timeout_s: float = 180, step_s: float = 2) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base + "/health", timeout=5) as r:
                if r.read().strip() == b"Healthy":
                    return
        except OSError:
            pass
        time.sleep(step_s)
    raise SetupError(f"{base} never reported healthy; is Docker running and the port free? See: docker compose -f demo/compose.yml logs")


def in_container(path: pathlib.Path) -> str:
    """Where a file under demo/.data/ sits inside the ffmpeg container."""
    return "/work/" + path.relative_to(DATA).as_posix()


def make_media(library: dict, tag: str) -> int:
    media, cards = DATA / "media", DATA / "cards"
    cards.mkdir(parents=True, exist_ok=True)
    for rel, text in (nfo_files(library) | subtitle_files(library)).items():
        (media / rel).parent.mkdir(parents=True, exist_ok=True)
        (media / rel).write_text(text)
    for rel, picture in series_art(library).items():
        if not (media / rel).exists():
            picture.save(media / rel, quality=90)
    made = 0
    for clip in clips(library):
        out = media / clip.path
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        card = cards / f"{safe(clip.title)}.png"
        title_card(clip.title).save(card)
        part = out.with_name(out.stem + ".part.mp4")
        cmd = ["docker", "run", "--rm", "-v", f"{DATA}:/work", "--entrypoint", FFMPEG, tag]
        subprocess.run([*cmd, *ffmpeg_args(clip, in_container(card), in_container(part))], check=True)
        part.rename(out)  # a clip cut short never looks finished
        made += 1
    return made


def wizard(api: Api, creds: dict[str, str]) -> None:
    if api.call("GET", "/System/Info/Public").get("StartupWizardCompleted"):
        return
    api.call("POST", "/Startup/Configuration", {"UICulture": "en-US", "MetadataCountryCode": "US", "PreferredMetadataLanguage": "en"})
    api.call("GET", "/Startup/User")
    api.call("POST", "/Startup/User", {"Name": ADMIN, "Password": creds["DEMO_ADMIN_PASSWORD"]})
    api.call("POST", "/Startup/RemoteAccess", {"EnableRemoteAccess": True, "EnableAutomaticPortMapping": False})
    api.call("POST", "/Startup/Complete")


def sign_in(base: str, user: str, password: str) -> tuple[Api, str]:
    r = Api(base).call("POST", "/Users/AuthenticateByName", {"Username": user, "Pw": password})
    return Api(base, r["AccessToken"]), r["User"]["Id"]


def name_server(admin: Api) -> None:
    conf = admin.call("GET", "/System/Configuration")
    if conf.get("ServerName") != "Demo":
        admin.call("POST", "/System/Configuration", {**conf, "ServerName": "Demo"})


def show_splash(admin: Api) -> None:
    """Sign-in over the splash screen Jellyfin draws from the library's artwork."""
    branding = admin.call("GET", "/System/Configuration/branding")
    if not branding.get("SplashscreenEnabled"):
        admin.call("POST", "/System/Configuration/branding", {**branding, "SplashscreenEnabled": True})


def ensure_viewer(admin: Api, password: str) -> None:
    if not any(u["Name"] == VIEWER for u in admin.call("GET", "/Users")):
        admin.call("POST", "/Users/New", {"Name": VIEWER, "Password": password})


def ensure_key(admin: Api) -> str:
    def find():
        return next((k["AccessToken"] for k in admin.call("GET", "/Auth/Keys")["Items"] if k.get("AppName") == KEY_APP), None)

    if not find():
        admin.call("POST", f"/Auth/Keys?app={KEY_APP}")
    key = find()
    if not key:
        raise SetupError("the server made no API key")
    return key


def ensure_plugins(admin: Api, plan: dict, server: str) -> tuple[list[str], list[str]]:
    """Install each pinned plugin: (installed now, skipped with the reason)."""
    repos = admin.call("GET", "/Repositories")
    have = {r["Url"] for r in repos}
    new = [{"Name": r["name"], "Url": r["url"], "Enabled": True} for r in plan["repositories"] if r["url"] not in have]
    if new:
        admin.call("POST", "/Repositories", repos + new)
    installed = {p["Name"]: p["Version"] for p in admin.call("GET", "/Plugins")}
    packages = {p["name"]: p for p in admin.call("GET", "/Packages")}
    done, skipped = [], []
    for p in plan["plugins"]:
        if installed.get(p["name"]) == p["version"]:
            continue
        pkg = packages.get(p["name"]) or {}
        fit = next((v for v in pkg.get("versions", []) if v["version"] == p["version"] and abi_ok(v["targetAbi"], server)), None)
        if fit is None:
            skipped.append(f"{p['name']} {p['version']}: no build for Jellyfin {server}")
            continue
        q = urllib.parse.urlencode({"assemblyGuid": pkg["guid"], "version": p["version"], "repositoryUrl": fit["repositoryUrl"]})
        admin.call("POST", f"/Packages/Installed/{urllib.parse.quote(p['name'])}?{q}")
        done.append(f"{p['name']} {p['version']}")
    return done, skipped


def wrong_abis(server: str) -> list[str]:
    bad = []
    for meta in sorted(DATA.glob("config/**/plugins/*/meta.json")):
        m = json.loads(meta.read_text())
        if not abi_ok(m.get("targetAbi", ""), server):
            bad.append(f"{m.get('name')} {m.get('version')}: targetAbi {m.get('targetAbi')}")
    return bad


def not_active(admin: Api, plan: dict, skipped: set[str]) -> list[str]:
    """Each pinned plugin, other than the skipped ones, that the server has not loaded."""
    status = {p["Name"]: p.get("Status") for p in admin.call("GET", "/Plugins")}
    names = [p["name"] for p in plan["plugins"] if p["name"] not in skipped]
    return [f"{n}: {status.get(n) or 'not installed'}" for n in names if status.get(n) != "Active"]


def ensure_libraries(admin: Api) -> None:
    have = {f["Name"] for f in admin.call("GET", "/Library/VirtualFolders")}
    for name, kind, path in LIBRARIES:
        if name not in have:
            q = urllib.parse.urlencode({"name": name, "collectionType": kind, "paths": path, "refreshLibrary": "true"})
            admin.call("POST", f"/Library/VirtualFolders?{q}", {"LibraryOptions": {}})


def items(viewer: Api, uid: str, kind: str) -> list[dict]:
    q = urllib.parse.urlencode(
        {"IncludeItemTypes": kind, "Recursive": "true", "userId": uid, "SortBy": "SortName", "Fields": "ProviderIds"}
    )
    return viewer.call("GET", f"/Items?{q}")["Items"]


def wait_for_library(viewer: Api, uid: str, library: dict, timeout_s: float = 900) -> list[str]:
    """Wait until every title is in with its poster; what is still missing at the timeout."""
    deadline = time.monotonic() + timeout_s
    while True:
        movies, episodes = items(viewer, uid, "Movie"), items(viewer, uid, "Episode")
        bare = sorted(m["Name"] for m in movies if "Primary" not in (m.get("ImageTags") or {}))
        complete = len(movies) >= len(library["movies"]) and len(episodes) >= len(library["series"]["episodes"])
        if complete and not bare:
            return []
        if time.monotonic() > deadline:
            return bare or [f"{len(movies)} of {len(library['movies'])} films, {len(episodes)} episodes"]
        time.sleep(10)


def seed_playstate(viewer: Api, uid: str) -> None:
    """Two films half watched and the first episode watched, so Continue Watching and Next Up
    have something to show. The first film by name stays untouched: the harness's title page."""
    for film in items(viewer, uid, "Movie")[1:3]:
        ticks = (film.get("RunTimeTicks") or 0) // 2
        viewer.call("POST", f"/UserItems/{film['Id']}/UserData?userId={uid}", {"PlaybackPositionTicks": ticks})
    first = items(viewer, uid, "Episode")[0]
    viewer.call("POST", f"/UserPlayedItems/{first['Id']}?userId={uid}")


def write_config() -> None:
    """The harness's settings for the demo: the example's volatile parts, and a search term this
    library answers with films, the series and people."""
    if not CONFIG.exists():
        example = json.loads((ROOT / "harness" / "config.example.json").read_text())
        CONFIG.write_text(json.dumps({"search_term": SEARCH_TERM, "volatile": example["volatile"]}, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=int(os.environ.get("DEMO_PORT", "8096")))
    args = ap.parse_args(argv)
    library = json.loads((DEMO / "library.json").read_text())
    plan = json.loads((DEMO / "plugins.json").read_text())
    creds = credentials(read_env(ENV_FILE), args.port)
    write_env(creds, ENV_FILE)
    base = creds["JELLYFIN_URL"]
    try:
        for d in ("config", "cache", "media"):
            (DATA / d).mkdir(parents=True, exist_ok=True)
        compose = ["docker", "compose", "-f", str(COMPOSE)]
        try:
            subprocess.run([*compose, "up", "-d"], check=True, env={**os.environ, "DEMO_PORT": str(args.port)})
        except subprocess.CalledProcessError:
            raise SetupError(
                f"docker compose could not start the demo; is Docker running and port {args.port} free? "
                "Docker's own message is above; --port picks another port"
            ) from None
        print(f"made {make_media(library, image(COMPOSE.read_text()))} stand-in clips", flush=True)
        wait_healthy(base)
        wizard(Api(base), creds)
        admin, _ = sign_in(base, ADMIN, creds["DEMO_ADMIN_PASSWORD"])
        name_server(admin)
        show_splash(admin)
        ensure_viewer(admin, creds["JELLYFIN_THEME_PASSWORD"])
        creds["JELLYFIN_API_KEY"] = ensure_key(admin)
        write_env(creds, ENV_FILE)
        server = admin.call("GET", "/System/Info")["Version"]
        done, skipped = ensure_plugins(admin, plan, server)
        if done:
            print("installed " + ", ".join(done) + "; restarting", flush=True)
            admin.call("POST", "/System/Restart")
            time.sleep(5)
            wait_healthy(base)
            admin, _ = sign_in(base, ADMIN, creds["DEMO_ADMIN_PASSWORD"])
        bad = wrong_abis(server)
        if bad:
            raise SetupError("plugin builds for another Jellyfin: " + "; ".join(bad))
        idle = not_active(admin, plan, {p["name"] for p in plan["plugins"] if any(s.startswith(p["name"] + " ") for s in skipped)})
        if idle:
            raise SetupError("plugins the server did not load: " + "; ".join(idle))
        ensure_libraries(admin)
        viewer, uid = sign_in(base, VIEWER, creds["JELLYFIN_THEME_PASSWORD"])
        missing = wait_for_library(viewer, uid, library)
        seed_playstate(viewer, uid)
        write_config()
        subprocess.run([sys.executable, "-m", "harness.discover"], cwd=ROOT, env={**os.environ, **creds}, check=True)
    except FileNotFoundError as e:
        print(
            f"setup: {pathlib.Path(e.filename or 'docker').name} not found; install Docker (OrbStack on a Mac) and start it",
            file=sys.stderr,
        )
        return 1
    except (SetupError, subprocess.CalledProcessError, OSError) as e:
        print(f"setup: {e}", file=sys.stderr)
        return 1
    for s in skipped:
        print(f"skipped {s}")
    for m in missing:
        print(f"no artwork yet: {m}")
    print("demo ready on " + base + ". Use it: ( set -a; . demo/.env; set +a; <command> )")
    return 0


if __name__ == "__main__":
    sys.exit(main())
