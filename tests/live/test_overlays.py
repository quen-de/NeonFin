import pytest

from harness import checks, states

pytestmark = pytest.mark.live

INK = (5, 6, 10)
INK2 = (9, 11, 18)


def test_desktop_dialogs_are_solid_ink_with_a_rim(open_page, style, color):
    page = open_page("dialog", "desktop", "none")
    d = style(page, ".formDialog", "background-color", "backdrop-filter", "border-top-left-radius")
    rim = style(page, ".formDialog", "box-shadow", pseudo="::after")
    head = style(page, ".formDialog .formDialogHeader", "background-color")
    foot = style(page, ".formDialog .formDialogFooter", "background-color")
    assert color(d["background-color"]) == (*INK2, 1) and d["backdrop-filter"] == "none", d
    assert d["border-top-left-radius"] == "14px" and "inset" in rim["box-shadow"], (d, rim)
    assert color(head["background-color"])[3] == 0, head  # the dialog's ink shows through
    assert color(foot["background-color"])[:3] == INK2, foot  # content scrolls under it


def test_the_page_behind_a_dialog_dims_in_ink(open_page, style, color):
    b = style(open_page("dialog", "desktop", "none"), ".dialogBackdropOpened", "background-color", "opacity")
    assert color(b["background-color"])[:3] == INK and float(b["opacity"]) >= 0.5, b


@pytest.mark.parametrize("profile, viewport", [("phone", None), ("desktop", (1100, 800))])
def test_full_screen_dialogs_are_square(open_page, style, color, profile, viewport):
    page = open_page("dialog", profile, "none", viewport=viewport)
    d = style(page, ".formDialog", "background-color", "border-top-left-radius")
    rim = style(page, ".formDialog", "display", pseudo="::after")
    assert d["rect"][:2] == [0, 0] and d["border-top-left-radius"] == "0px", d
    assert color(d["background-color"])[:3] == INK2 and rim["display"] == "none", (d, rim)
    if profile == "phone":
        assert checks.glass_elements(page) == []


def dark_pill(s, color):
    r, g, b, a = color(s["background-color"])
    height = s["rect"][3]
    return a >= 0.95 and max(r, g, b) < 40 and float(s["border-top-left-radius"].removesuffix("px")) >= height / 2 - 0.5


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_tooltips_are_small_dark_pills(open_page, style, color, profile):
    s = style(open_page("tooltip", profile, "none"), ".MuiTooltip-tooltip", "background-color", "border-top-left-radius")
    assert dark_pill(s, color), s


@pytest.mark.parametrize("profile", ["desktop", "phone"])
def test_toasts_are_small_dark_pills(open_page, style, color, profile):
    page = open_page("login", profile, "none", variant="toast")
    answered = []

    def refuse(route):
        answered.append(route.request.method)
        route.fulfill(status=401, body="")

    # A refused sign-in, answered here: nothing reaches the server.
    page.route(states.api_path("/users/authenticatebyname"), refuse)
    page.fill("#txtManualName", "nobody")
    page.fill("#txtManualPassword", "wrong")
    page.press("#txtManualPassword", "Enter")
    page.wait_for_selector(".toast.toastVisible", timeout=10_000)
    assert answered == ["POST"], answered
    page.wait_for_timeout(400)  # the slide-in
    s = style(page, ".toast", "background-color", "border-top-left-radius")
    assert dark_pill(s, color), s
    assert checks.blue_hits(page) == {}
