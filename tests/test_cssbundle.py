from harness import cssbundle


def test_strip_imports_drops_every_import_and_keeps_rules():
    out = cssbundle.strip_imports('@import url("https://fonts.example/f.css");\n.a{x:1}\n')
    assert "@import" not in out and ".a{x:1}" in out


def test_strip_imports_without_imports_is_identity():
    assert cssbundle.strip_imports(".a{}") == ".a{}"
