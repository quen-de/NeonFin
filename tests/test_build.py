import base64
import re

import pytest

import build
from cssscan import BuildError, brace_scan

FONT = b"wOF2-test-bytes"


def make_skin(root, files=None):
    tree = {
        "skin/00-tokens.css": (
            ":root { --nf-neon: #f00; --nf-teal: #0f0; --nf-ink: #000; --nf-ink-2: #111; --nf-chrome: #222;"
            " --nf-paper: #eee; --nf-light: #fff; --nf-shade: #000; --nf-on-neon: var(--nf-light); }\n"
        ),
        "palettes/picker.html": "<style>/*@FONT@*/ /*@TOKENS@*/</style><script>const PRESETS = /*@PRESETS@*/null;</script>\n",
        "palettes/test.css": "/* NeonFin palette: Test. Paste after the skin in Custom CSS. */\n:root { --nf-neon: #abc; }\n",
        "skin/30-header.css": ".h { color: inherit; }\n",
        "skin/plugins/b-plugin.css": "/* plugin: B; roots: .b- */\n.b-x { color: inherit; }\n",
        "skin/plugins/a-plugin.css": "/* plugin: A; roots: .a- */\n.a-x { color: inherit; }\n",
        "skin/99-access.css": ".z { color: inherit; }\n",
    }
    tree.update(files or {})
    for rel, text in tree.items():
        if text is None:
            continue
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    font = root / build.FONT_FILE
    font.parent.mkdir(parents=True, exist_ok=True)
    font.write_bytes(FONT)
    return root


def test_cascade_order_is_core_then_plugins_then_late(tmp_path):
    assert build.skin_files(make_skin(tmp_path)) == [
        "skin/00-tokens.css",
        "skin/30-header.css",
        "skin/plugins/a-plugin.css",
        "skin/plugins/b-plugin.css",
        "skin/99-access.css",
    ]


def test_unnumbered_files_are_not_built(tmp_path):
    assert ".n{}" not in build.assemble(make_skin(tmp_path, {"skin/notes.css": ".n{}"}))


def test_font_is_embedded_once_at_the_top(tmp_path):
    css = build.assemble(make_skin(tmp_path))
    assert css.startswith('@font-face { font-family: "NeonFin Sign";')
    assert css.count("@font-face") == 1
    assert base64.b64encode(FONT).decode() in css


def test_missing_tokens_fail(tmp_path):
    root = make_skin(tmp_path, {"skin/00-tokens.css": None})
    with pytest.raises(BuildError, match="missing skin/00-tokens.css"):
        build.assemble(root)


def test_missing_font_fails(tmp_path):
    root = make_skin(tmp_path)
    (root / build.FONT_FILE).unlink()
    with pytest.raises(BuildError, match="missing skin/fonts/neonfin-sign-800.woff2"):
        build.assemble(root)


def test_skin_rule_violations_fail_the_build(tmp_path):
    with pytest.raises(BuildError, match="skin/30-header.css:1: @import is not allowed"):
        build.assemble(make_skin(tmp_path, {"skin/30-header.css": '@import "x.css";\n'}))


def test_unbalanced_file_fails_with_its_name(tmp_path):
    with pytest.raises(BuildError, match="skin/30-header.css is brace-unbalanced"):
        build.assemble(make_skin(tmp_path, {"skin/30-header.css": ".h { color: inherit;\n"}))


def test_header_round_trip():
    h = build.header("a" * 40, True)
    assert h.startswith("/* neonfin ")
    assert build.parse_header(h + ".x{}") == ("a" * 40, True)
    assert build.parse_header(".x{}") is None


def test_main_writes_the_stylesheet(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "ROOT", make_skin(tmp_path / "repo"))
    out = tmp_path / "out.css"
    assert build.main(["-o", str(out)]) == 0
    assert out.read_text().startswith("/* neonfin unknown-dirty */\n@font-face")
    assert (tmp_path / "palette.html").read_text().startswith("<style>@font-face")


def test_real_tree_builds_within_budget():
    css = build.assemble()
    assert "/*" not in css
    assert brace_scan(css) == (0, [])
    assert len(css.encode()) - len(build.font_face().encode()) <= 60_000


def test_the_built_sheet_keeps_only_the_stamp_comment(tmp_path):
    root = make_skin(tmp_path, {"skin/30-header.css": "/* area */\n.h { color: inherit; } /* why */\n"})
    css = build.build(root)
    assert css.startswith("/* neonfin ") and css.count("/*") == 1


def test_a_comment_that_joins_two_tokens_fails_with_its_file(tmp_path):
    root = make_skin(tmp_path, {"skin/30-header.css": ".h { border: 1px/* x */solid; }\n"})
    with pytest.raises(BuildError, match="skin/30-header.css: line 1: a comment is all that separates"):
        build.assemble(root)


def test_the_palette_has_nine_inputs_each_a_token():
    tokens = build.preset_tokens((build.ROOT / build.TOKENS).read_text())
    assert build.PALETTE == ("neon", "teal", "ink", "ink-2", "chrome", "paper", "light", "shade", "on-neon")
    assert set(build.PALETTE) <= set(tokens) and tokens["on-neon"] == "var(--nf-light)"


def test_presets_set_only_palette_inputs_in_hex():
    files = sorted((build.ROOT / "palettes").glob("*.css"))
    assert [f.stem for f in files] == ["acid", "amber", "cyan", "violet"]
    for f in files:
        css = f.read_text()
        assert build.PRESET_HEADER.match(css), f.name
        tokens = build.preset_tokens(css)
        assert tokens and set(tokens) <= set(build.PALETTE), f.name
        assert all(re.fullmatch(r"#[0-9a-f]{3}|#[0-9a-f]{6}", v) for v in tokens.values()), f.name


def test_hex6_spells_every_colour_out():
    assert build.hex6("#ABC") == "#aabbcc" and build.hex6("#00e5ff") == "#00e5ff"


def test_the_palette_page_carries_the_tokens_the_presets_and_the_font(tmp_path):
    page = build.palette_page(make_skin(tmp_path))
    assert ".nf-preview {" in page and ":root" not in page and page.count("@font-face") == 1
    assert '"Crimson": {"neon": "#ff0000", "teal": "#00ff00"' in page and '"on-neon": "#ffffff"}' in page
    assert '"Test": {"neon": "#aabbcc"}' in page


def test_a_palette_page_without_its_marks_fails(tmp_path):
    root = make_skin(tmp_path, {"palettes/picker.html": "<p>no marks</p>"})
    with pytest.raises(BuildError, match="palettes/picker.html has no /\\*@FONT@\\*/ mark"):
        build.palette_page(root)


def test_a_preset_without_its_header_fails(tmp_path):
    root = make_skin(tmp_path, {"palettes/bad.css": ":root { --nf-neon: #abc; }\n"})
    with pytest.raises(BuildError, match="palettes/bad.css starts with"):
        build.palette_page(root)


def test_the_real_palette_page_builds():
    page = build.palette_page()
    assert all(name in page for name in ('"Cyan neon"', '"Amber"', '"Violet"', '"Acid green"'))
