import pytest

from harness import checks

pytestmark = pytest.mark.live

PANEL = "#loginPage > .margin-auto-y"
SPLASH = '.backdropImage[style*="Branding/Splashscreen"]'
HAS_SPLASH = (
    "() => [...document.querySelectorAll('.backdropImage')]"
    ".some((e) => getComputedStyle(e).backgroundImage.includes('Branding/Splashscreen'))"
)


def splash(page):
    if not page.evaluate(HAS_SPLASH):
        pytest.skip("this server shows no splash screen on sign-in")
    assert page.locator(SPLASH).count() == 1, "the splash is shown but the skin's selector misses it"


def test_the_sign_in_panel_is_glass_on_desktop(open_page, style, color):
    page = open_page("login", "desktop", "none")
    s = style(page, PANEL, "backdrop-filter", "background-color", "border-top-left-radius", "box-shadow")
    x, _, w, _ = s["rect"]
    assert "blur" in s["backdrop-filter"] and 0.4 <= color(s["background-color"])[3] <= 0.75, s
    assert s["border-top-left-radius"] == "14px" and "inset" in s["box-shadow"], s
    assert w <= 440 and abs(x + w / 2 - 720) < 1, s
    assert len(checks.glass_elements(page)) <= 3


@pytest.mark.parametrize("route", ["login", "picker"])
def test_the_sign_in_panel_is_solid_on_phones(open_page, style, color, route):
    page = open_page(route, "phone", "none")
    s = style(page, PANEL, "backdrop-filter", "background-color", "border-top-left-radius")
    assert s["backdrop-filter"] == "none" and color(s["background-color"])[3] >= 0.95, s
    assert s["border-top-left-radius"] == "14px", s
    assert checks.glass_elements(page) == []


@pytest.mark.parametrize("feature", [("prefers-reduced-transparency", "reduce"), ("prefers-contrast", "more")])
def test_the_sign_in_panel_turns_solid_when_asked(open_page, style, color, feature):
    s = style(open_page("login", "desktop", "none", media=(feature,)), PANEL, "backdrop-filter", "background-color")
    assert s["backdrop-filter"] == "none" and color(s["background-color"])[3] == 1, s


@pytest.mark.parametrize("route", ["login", "picker"])
def test_the_panel_fits_a_320px_phone(open_page, route):
    page = open_page(route, "phone", "none", viewport=(320, 700))
    assert page.evaluate("() => document.documentElement.scrollWidth") <= 320
    left, right = page.evaluate("(s) => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.right]; }", PANEL)
    assert left >= 15.5 and right <= 304.5, (left, right)


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_a_splash_screen_stays_sharp_and_dimmed(open_page, style, profile):
    page = open_page("login", profile, "none")
    splash(page)
    s = style(page, SPLASH, "filter", "transform")
    assert "brightness" in s["filter"] and "blur" not in s["filter"] and s["transform"] == "none", s
    if profile == "desktop":
        assert style(page, SPLASH, "display", pseudo="::after")["display"] == "none"


@pytest.mark.parametrize("profile", ["desktop", "phone"])
@pytest.mark.parametrize("route", ["login", "picker"])
def test_sign_in_text_reads_over_a_white_splash(open_page, tmp_path, route, profile):
    page = open_page(route, profile, "none", variant="white-splash")
    splash(page)
    page.add_style_tag(content=f"{SPLASH}, {SPLASH}::after {{ background: #fff !important; }}")
    page.wait_for_timeout(300)
    assert checks.contrast_failures(page, route, tmp_path / "sign-in.png") == []


TEXT_2 = (246, 243, 240, 0.62)


def test_the_heading_is_a_lit_sign(open_page, style):
    s = style(open_page("login", "desktop", "none"), "#loginPage .manualLoginForm h1", "font-family", "text-transform", "text-shadow")
    assert "NeonFin Sign" in s["font-family"] and s["text-transform"] == "uppercase" and s["text-shadow"] != "none", s


def test_forgot_password_and_the_disclaimer_step_back(open_page, style, color):
    page = open_page("login", "desktop", "none")
    forgot = style(page, "#loginPage .btnForgotPassword", "color", "background-color", "box-shadow")
    assert color(forgot["background-color"])[3] == 0 and forgot["box-shadow"] == "none", forgot
    assert color(forgot["color"]) == TEXT_2, forgot
    if page.locator("#loginPage .loginDisclaimer").inner_text().strip():
        assert color(style(page, "#loginPage .loginDisclaimer", "color")["color"]) == TEXT_2


def test_the_panel_ends_close_under_its_last_line(open_page):
    # The disclaimer's paragraph margin and Jellyfin's spacing left a tall empty band.
    gap = open_page("login", "desktop", "none").evaluate(
        """(s) => { const panel = document.querySelector(s).getBoundingClientRect();
      const last = [...document.querySelectorAll('#loginPage .readOnlyContent *')]
        .filter((e) => e.getClientRects().length && e.innerText && e.innerText.trim()).pop().getBoundingClientRect();
      return panel.bottom - last.bottom; }""",
        PANEL,
    )
    assert gap <= 32, gap


def test_disclaimer_links_are_crimson(open_page, color):
    page = open_page("login", "desktop", "none", variant="disclaimer-link")
    # Jellyfin renders the disclaimer from Markdown and marks its links as button links.
    c = page.evaluate("""() => { const a = document.createElement('a'); a.className = 'button-link'; a.href = '#';
      a.textContent = 'terms'; document.querySelector('#loginPage .loginDisclaimer').append(a); return getComputedStyle(a).color; }""")
    r, g, b, _ = color(c)
    assert r - max(g, b) > 80, c


def test_users_are_round_avatars_ringed_on_focus(open_page, style, color):
    page = open_page("picker", "desktop", "none", variant="focus")
    for sel in ("#divUsers .card .cardScalable", "#divUsers .card .cardContent", "#divUsers .card .cardImage"):
        assert style(page, sel, "border-top-left-radius")["border-top-left-radius"] == "50%", sel
    ground = style(page, "#divUsers .card .defaultCardBackground", "background-color")
    assert color(ground["background-color"])[:3] == (74, 10, 21), ground  # the oxblood
    page.locator("#divUsers .card").first.focus()
    page.wait_for_timeout(400)
    ring = style(page, "#divUsers .card .cardScalable", "opacity", "box-shadow", pseudo="::after")
    assert ring["opacity"] == "1" and "255, 36, 72" in ring["box-shadow"], ring
    assert style(page, "#divUsers .card", "outline-style")["outline-style"] == "none"
