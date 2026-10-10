import base64

import pytest

import build
from cssscan import BuildError, brace_scan

FONT = b"wOF2-test-bytes"


def make_skin(root, files=None):
    tree = {
        "skin/00-tokens.css": ":root { --nf-x: 1; }\n",
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


def test_real_tree_builds_within_budget():
    css = build.assemble()
    assert brace_scan(css) == (0, [])
    assert len(css.encode()) - len(build.font_face().encode()) <= 60_000
