"""Browser plumbing: launch, login, CSS override, navigation, settling."""

from __future__ import annotations

import json
import time
import weakref
from dataclasses import dataclass

from harness import plugins
from harness.states import STATES


class LoginError(RuntimeError):
    pass


class RouteError(RuntimeError):
    pass


def launch(pw):
    # Branded Chrome, not Playwright's Chromium: Chromium has no proprietary
    # codecs, so the OSD capture could never start playback.
    return pw.chromium.launch(channel="chrome", headless=True)


def patch_branding(body: bytes, css: str) -> bytes:
    data = json.loads(body)
    data["CustomCss"] = css
    return json.dumps(data).encode()


@dataclass
class Override:
    css: str
    hits: int = 0


# Runs must not depend on when they happen: "Ends at" labels and cache-busting
# query strings read the clock. Only Date is frozen; timers, rAF and
# performance.now() keep real time so settling and frame metrics still work.
# Apps that throttle on Date deltas see none, so a capture step that needs one
# advances the clock itself with window.__harnessAdvanceClock(ms).
FIXED_NOW_MS = 1_780_315_200_000  # 2026-06-01T12:00:00Z
FREEZE_DATE_JS = f"""(() => {{
  const Real = Date;
  let T = {FIXED_NOW_MS};
  function D(...a) {{ if (!new.target) return new Real(T).toString(); return a.length ? new Real(...a) : new Real(T); }}
  D.prototype = Real.prototype; D.now = () => T; D.parse = Real.parse; D.UTC = Real.UTC;
  Object.setPrototypeOf(D, Real);
  globalThis.Date = D;
  globalThis.__harnessAdvanceClock = (ms) => {{ T += ms; }};
}})()"""
TIMEZONE = "UTC"
LOCALE = "en-US"
# Playing the OSD item would otherwise store a resume point on the server and
# change the detail pages the next run captures.
PLAYBACK_REPORTS = "**/Sessions/Playing**"
# Requests still in flight keep a page unsettled; streams never finish.
UNTRACKED = {"media", "websocket", "eventsource"}
_pending: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _swallow_report(route):
    if route.request.method == "POST":
        route.fulfill(status=204)
    else:
        route.fallback()


def _track_requests(page) -> None:
    pending: set = set()
    page.on("request", lambda r: r.resource_type in UNTRACKED or pending.add(r))
    page.on("requestfinished", lambda r: pending.discard(r))
    page.on("requestfailed", lambda r: pending.discard(r))
    _pending[page] = pending


def new_page(browser, profile, state, override: Override | None, plugins_off: frozenset[str] = frozenset(), freeze_clock: bool = True):
    ctx = browser.new_context(storage_state=state, service_workers="block", timezone_id=TIMEZONE, locale=LOCALE, **profile.context)
    if freeze_clock:
        ctx.add_init_script(FREEZE_DATE_JS)
    ctx.route(PLAYBACK_REPORTS, _swallow_report)
    if plugins_off:
        ctx.route(lambda url: plugins.blocks(url, plugins_off), lambda route: route.abort())
    if override is not None:
        # jellyfin-web 12 reads custom CSS from the CustomCss field of
        # /Branding/Configuration (components/CustomCss.tsx). /Branding/Css is
        # covered too in case a client still uses it.
        def branding(route):
            resp = route.fetch()
            override.hits += 1
            route.fulfill(status=resp.status, content_type="application/json", body=patch_branding(resp.body(), override.css))

        def css(route):
            override.hits += 1
            route.fulfill(status=200, content_type="text/css", body=override.css)

        ctx.route("**/Branding/Configuration*", branding)
        ctx.route("**/Branding/Css*", css)
    page = ctx.new_page()
    _track_requests(page)
    return ctx, page


def login_state(browser, cfg, profile) -> dict:
    ctx = browser.new_context(service_workers="block", **profile.context)
    page = ctx.new_page()
    try:
        page.goto(f"{cfg.url}/web/#/login")
        page.wait_for_selector("#txtManualName, .btnManual", state="visible", timeout=30_000)
        name = page.locator("#txtManualName")
        if not name.is_visible():
            page.locator(".btnManual").first.click()
        name.fill(cfg.user)
        page.locator("#txtManualPassword").fill(cfg.password)
        page.locator("#txtManualPassword").press("Enter")
        try:
            page.wait_for_function("() => location.hash.startsWith('#/home')", timeout=30_000)
        except Exception as e:
            raise LoginError(f"login as {cfg.user} never reached #/home") from e
        return ctx.storage_state()
    finally:
        ctx.close()


def navigate(page, url: str, anchor: str, timeout_ms: int = 30_000) -> float:
    """Full load of url (never a same-document hash change); ms until anchor is visible."""
    page.goto("about:blank")
    # Requests cut off by leaving a document do not always report failure.
    _pending.get(page, set()).clear()
    t0 = time.perf_counter()
    page.goto(url)
    try:
        page.wait_for_selector(anchor, state="visible", timeout=timeout_ms)
    except Exception as e:
        raise RouteError(f"{anchor!r} never became visible at {page.url}") from e
    return (time.perf_counter() - t0) * 1000


WATCH_JS = """(volatile) => {
  const ignored = (node) => {
    const el = node.nodeType === 1 ? node : node.parentElement;
    return !!el && volatile.some((s) => el.closest(s));
  };
  window.__harnessMutations = 0;
  window.__harnessObserver = new MutationObserver((recs) => {
    if (!recs.every((r) => ignored(r.target))) window.__harnessMutations++;
  });
  window.__harnessObserver.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
}"""


def settle(page, volatile, quiet_ms: int = 800, cap_ms: int = 15_000) -> bool:
    """True once neither the DOM (outside volatile subtrees) nor the network
    has been busy for quiet_ms; False if that never happens within cap_ms.
    networkidle alone misses lazy images requested after it fires."""
    page.wait_for_load_state("networkidle")
    page.evaluate("() => document.fonts.ready.then(() => true)")
    pending = _pending.get(page, set())
    page.evaluate(WATCH_JS, list(volatile))
    start = last_busy = time.monotonic()
    seen = 0
    try:
        while True:
            page.wait_for_timeout(100)
            now = time.monotonic()
            count = page.evaluate("() => window.__harnessMutations")
            if count != seen or pending:
                seen, last_busy = count, now
            if now - last_busy >= quiet_ms / 1000:
                return True
            if now - start >= cap_ms / 1000:
                return False
    finally:
        # Disconnect so the observer does not tax the perf trial that follows.
        page.evaluate("() => window.__harnessObserver?.disconnect()")


# Lazy cards load when an IntersectionObserver sees them, and which ones it
# sees while sections are still arriving and shifting the layout varies per
# load. Scrolling the whole page once makes the end state "everything loaded".
# Native loading=lazy images (plugin flags in horizontal rows) load within a
# distance Chrome derives from measured network quality, so they go eager.
PRIME_JS = """async (maxSteps) => {
  const step = Math.max(200, Math.floor(innerHeight * 0.8));
  for (let i = 0, y = 0; i < maxSteps && y < document.documentElement.scrollHeight; i++, y += step) {
    scrollTo({ top: y, behavior: 'instant' });
    await new Promise((r) => setTimeout(r, 100));
  }
  scrollTo({ top: 0, behavior: 'instant' });
  for (const img of document.querySelectorAll('img[loading="lazy"]')) img.loading = 'eager';
}"""


def prime(page, max_steps: int = 60) -> None:
    page.evaluate(PRIME_JS, max_steps)


# Blurhash placeholders are decoded off-thread and drawn with no DOM change, so
# whether one is drawn at capture time is timing. Left out of pixels only; their
# computed styles are still compared.
PAINT_ONLY_HIDDEN = ("canvas.blurhash-canvas",)


# Chrome decodes large images off-thread at paint time, so a loaded image can
# still paint blank in a capture taken right after settling.
DECODE_JS = """async () => {
  const urls = new Set();
  for (const el of document.querySelectorAll('*')) {
    for (const m of getComputedStyle(el).backgroundImage.matchAll(/url\\("([^"]+)"\\)/g)) urls.add(m[1]);
  }
  for (const img of document.images) if (img.complete && img.naturalWidth) urls.add(img.currentSrc || img.src);
  await Promise.all([...urls].map((u) => { const i = new Image(); i.src = u; return i.decode().catch(() => {}); }));
  return urls.size;
}"""


def decode_images(page) -> int:
    return page.evaluate(DECODE_JS)


REVEAL_JS = """async (maxSteps) => {
  const frame = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  for (let i = 0, y = 0; i < maxSteps && y < document.documentElement.scrollHeight; i++, y += innerHeight) {
    scrollTo({ top: y, behavior: 'instant' });
    await frame();
  }
  scrollTo({ top: 0, behavior: 'instant' });
  await frame();
}"""


def reveal_lazy(page, max_steps: int = 40) -> None:
    """Scroll through the page once so lazy loaders fill what a full-page capture shows; a page
    that keeps growing stops after max_steps viewports."""
    page.evaluate(REVEAL_JS, max_steps)


def screenshot(page, route, volatile, path) -> None:
    # Hide volatile subtrees instead of masking them: a mask is painted on top
    # and would cover the menus and tooltips the state routes exist to show.
    hide = "".join(f"{s}{{visibility:hidden!important}}" for s in (*volatile, *PAINT_ONLY_HIDDEN))
    decode_images(page)
    if route.state:
        # Overlays are positioned against the viewport; a full-page capture
        # resizes it and moves them.
        page.screenshot(path=path, style=hide, animations="disabled")
        return
    reveal_lazy(page)
    decode_images(page)
    # Horizontal scrollers inflate the content width past what body
    # overflow-x:hidden ever lets a user see, so clip to the viewport width.
    height = page.evaluate("() => document.documentElement.scrollHeight")
    width = page.viewport_size["width"]
    page.screenshot(path=path, full_page=True, style=hide, animations="disabled", clip={"x": 0, "y": 0, "width": width, "height": height})


def route_url(cfg, route) -> str:
    return f"{cfg.url}/web/{route.path.format(search_term=cfg.search_term, **cfg.items)}"


def open_route(page, cfg, route, volatile) -> bool:
    navigate(page, route_url(cfg, route), route.ready or route.anchor)
    settle(page, volatile)
    prime(page)
    settled = settle(page, volatile)
    if route.state:
        try:
            STATES[route.state](page)
        except Exception as e:
            raise RouteError(f"state {route.state} failed: {str(e).splitlines()[0]}") from e
        try:
            page.wait_for_selector(route.anchor, state="visible", timeout=30_000)
        except Exception as e:
            raise RouteError(f"state {route.state} never showed {route.anchor!r}") from e
        settled = settle(page, volatile, cap_ms=5_000)
    return settled
