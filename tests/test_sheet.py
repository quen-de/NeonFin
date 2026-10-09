from PIL import Image

from harness import sheet


def test_sheet_tiles_captures_and_skips_diffs(tmp_path):
    d = tmp_path / "run" / "desktop"
    d.mkdir(parents=True)
    for name in ("home", "movies", "series", "search"):
        Image.new("RGB", (720, 2000), (200, 0, 0)).save(d / f"{name}.png")
    Image.new("RGB", (720, 400)).save(d / "home.diff.png")
    Image.new("RGB", (720, 400)).save(d / "home.contrast.png")
    out = sheet.make_sheet(tmp_path / "run", "desktop")
    im = Image.open(out)
    assert out.name == "sheet-desktop.png"
    assert im.width == sheet.GUTTER + 3 * (sheet.THUMB_W + sheet.GUTTER)
    assert im.height == sheet.GUTTER + 2 * (sheet.LABEL_H + 576 + sheet.GUTTER)
