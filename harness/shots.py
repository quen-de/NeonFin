"""Screenshots for the README, taken on the demo server with the current build.

    uv run python -m harness.shots                            # docs/screenshots/ and docs/social-preview.png
    uv run python -m harness.shots --engine firefox --out DIR # the release check in another engine

Refuses any server but the demo (on this machine, named Demo by demo/setup.py), so no other
library ever reaches a public image.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import urllib.request
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFilter
from playwright.sync_api import sync_playwright

import build
from harness import config, session
from harness.profiles import PROFILES, ROUTES

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
PREVIEW = ROOT / "docs" / "social-preview.png"
LOGO = ROOT / "docs" / "brand" / "header-dark.webp"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DEMO_NAME = "Demo"  # the name demo/setup.py gives the server
ROUTE = {r.name: r for r in ROUTES}
CHECK_ROUTES = ("home", "movie", "movies", "login", "osd")
PRESETS = ("cyan", "amber", "violet", "acid")
MAX_BYTES = 400_000
GROUND = (5, 6, 10)
# Stop the hero on the slide it shows and finish what is moving.
HOLD = """() => { const p = document.querySelector('#slides-container .pause-button');
  if (p && p.offsetParent) p.click();
  document.getAnimations().forEach((a) => { try { a.finish(); } catch (e) {} }); }"""


class ShotError(RuntimeError):
    pass


DEMO_ONLY = "screenshots come from the demo server only (DEVELOPMENT.md, Demo server)"


def require_local(url: str) -> None:
    if urlsplit(url).hostname not in LOCAL_HOSTS:
        raise ShotError(DEMO_ONLY)


def require_demo_server(info: dict) -> None:
    """Another Jellyfin on this machine is local too; only the demo carries the demo's name."""
    if info.get("ServerName") != DEMO_NAME:
        raise ShotError(f"{DEMO_ONLY}; this server is not named {DEMO_NAME}")


def public_info(url: str) -> dict:
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/System/Info/Public", timeout=10) as r:
            return json.loads(r.read())
    except (OSError, ValueError) as e:
        raise ShotError(f"cannot read the server's public info: {e}") from None


def side_by_side(images: list[Image.Image], gap: int = 24) -> Image.Image:
    out = Image.new("RGB", (sum(i.width for i in images) + gap * (len(images) - 1), max(i.height for i in images)), GROUND)
    x = 0
    for i in images:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def grid(images: list[Image.Image], cols: int = 2, gap: int = 16) -> Image.Image:
    rows = [side_by_side(images[r : r + cols], gap) for r in range(0, len(images), cols)]
    out = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + gap * (len(rows) - 1)), GROUND)
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + gap
    return out


def fit(img: Image.Image, width: int) -> Image.Image:
    return img if img.width <= width else img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)


def webp(img: Image.Image, path: pathlib.Path, width: int) -> None:
    img = fit(img, width)
    for quality in (82, 72, 62, 52):
        img.save(path, "WEBP", quality=quality, method=6)
        if path.stat().st_size <= MAX_BYTES:
            return
    raise ShotError(f"{path.name} stays over {MAX_BYTES:,} bytes")


def social_preview(home: Image.Image) -> Image.Image:
    """GitHub's 1280x640 card: the logo over the home page, as a window rising from the bottom edge."""
    w, h, radius, fade = 1280, 640, 14, 100
    out = Image.new("RGB", (w, h), GROUND)
    win = fit(home, 920)
    x, top = (w - win.width) // 2, 206
    box = (x, top, x + win.width - 1, h + radius)
    shadow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(shadow).rounded_rectangle(box, radius, fill=200)
    out.paste((0, 0, 0), (0, 0, w, h), shadow.filter(ImageFilter.GaussianBlur(28)))
    mask = Image.new("L", win.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, win.width - 1, win.height + radius), radius, fill=255)
    out.paste(win, (x, top), mask)
    ImageDraw.Draw(out, "RGBA").rounded_rectangle(box, radius, outline=(255, 255, 255, 40))
    # Sink the window's lower edge into the ground so the logo leads.
    ramp = Image.new("L", (w, h), 0)
    for i in range(fade):
        ImageDraw.Draw(ramp).line((0, h - fade + i, w, h - fade + i), fill=round(255 * (i / fade) ** 2))
    out.paste(GROUND, (0, 0, w, h), ramp)
    logo = fit(Image.open(LOGO), 500)
    out.paste(logo, ((w - logo.width) // 2, 8), logo)
    return out


class Camera:
    def __init__(self, browser, cfg):
        self.browser, self.cfg, self.states = browser, cfg, {}

    def take(self, route: str, profile: str, css: str, path: pathlib.Path) -> Image.Image:
        prof, r = PROFILES[profile], ROUTE[route]
        state = None
        if r.logged_in:
            if profile not in self.states:
                self.states[profile] = session.login_state(self.browser, self.cfg, prof)
            state = self.states[profile]
        ctx, page = session.new_page(self.browser, prof, state, session.Override(css))
        try:
            session.open_route(page, self.cfg, r, self.cfg.volatile)
            page.evaluate(HOLD)
            page.wait_for_timeout(300)
            page.screenshot(path=str(path), animations="disabled")
        finally:
            ctx.close()
        return Image.open(path).convert("RGB")


def readme_shots(cam: Camera, css: str, tmp: pathlib.Path) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)

    def shot(route, profile="desktop", sheet=css):
        return cam.take(route, profile, sheet, tmp / f"{route}-{profile}-{len(sheet)}.png")

    home = shot("home")
    webp(home, SHOTS / "home.webp", 1440)
    webp(side_by_side([fit(shot("home", sheet=""), 720), fit(home, 720)]), SHOTS / "before-after.webp", 1464)
    webp(shot("movie"), SHOTS / "title.webp", 1440)
    webp(shot("movies"), SHOTS / "library.webp", 1440)
    webp(side_by_side([fit(shot("home", "phone"), 540), fit(shot("movie", "phone"), 540)]), SHOTS / "phone.webp", 1104)
    presets = [fit(shot("home", sheet=css + (ROOT / "palettes" / f"{p}.css").read_text()), 720) for p in PRESETS]
    webp(grid(presets), SHOTS / "palettes.webp", 1456)
    webp(shot("osd"), SHOTS / "player.webp", 1440)
    social_preview(home).save(PREVIEW, optimize=True)


def engine_check(cam: Camera, css: str, out: pathlib.Path, engine: str) -> int:
    out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for route in CHECK_ROUTES:
        try:
            cam.take(route, "desktop", css, out / f"{engine}-{route}.png")
        except session.RouteError as e:
            failed += 1
            print(f"{engine} {route}: {str(e).splitlines()[0]}")
    return failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", choices=("chrome", "firefox", "webkit"), default="chrome")
    ap.add_argument("--out", help="with --engine: where the check images go")
    args = ap.parse_args(argv)
    cfg = config.load()
    try:
        require_local(cfg.url)
        require_demo_server(public_info(cfg.url))
    except ShotError as e:
        print(f"shots: {e}", file=sys.stderr)
        return 2
    css = build.build()
    with sync_playwright() as pw, tempfile.TemporaryDirectory() as tmp:
        browser = session.launch(pw) if args.engine == "chrome" else getattr(pw, args.engine).launch(headless=True)
        try:
            cam = Camera(browser, cfg)
            if args.out:
                return 1 if engine_check(cam, css, pathlib.Path(args.out), args.engine) else 0
            readme_shots(cam, css, pathlib.Path(tmp))
        finally:
            browser.close()
    print(f"wrote {SHOTS} and {PREVIEW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
