import pytest

from harness import checks

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
