import pathlib

from fontTools.ttLib import TTFont

FONT = pathlib.Path(__file__).resolve().parents[1] / "skin" / "fonts" / "neonfin-sign-800.woff2"


def test_font_is_a_small_woff2():
    data = FONT.read_bytes()
    assert data[:4] == b"wOF2"
    assert len(data) <= 25_000


def test_font_covers_sign_text():
    cmap = TTFont(FONT).getBestCmap()
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ÀÂÄÆÇÉÈÊËÎÏÔŒÙÛÜŸÑÅØŠŽŁ&'’:!?,.-–#()/":
        assert ord(ch) in cmap, ch


def test_font_is_renamed_so_it_never_shadows_an_installed_one():
    assert TTFont(FONT)["name"].getDebugName(1) == "NeonFin Sign"
