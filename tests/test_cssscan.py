import pytest

from cssscan import BuildError, brace_scan, declarations, leaf_rules, selectors, split_imports


def test_brace_scan_ignores_comments_and_strings():
    assert brace_scan('a { content: "{"; } /* { */') == (0, [])
    assert brace_scan(".a { .b {") == (2, [])


def test_brace_scan_reports_stray_closers_without_going_negative():
    css = ".a{}\n}\n.b {"
    assert brace_scan(css) == (1, [css.index("}\n.b")])


def test_split_imports_returns_statements_and_rest():
    imports, rest = split_imports('.a{}\n@import "x.css";\n.b{}')
    assert imports == ['@import "x.css";']
    assert ".a{}" in rest and ".b{}" in rest and "@import" not in rest


def test_split_imports_rejects_import_inside_block():
    with pytest.raises(BuildError, match="inside a block"):
        split_imports('@media print { @import url("x.css"); }')


def test_leaf_rules_carry_their_at_rule_context():
    rules = leaf_rules("@media (x) { .a { color: red; } }\n.b{}")
    assert [(r.prelude, r.context) for r in rules] == [(".a", ("@media (x)",)), (".b", ())]


def test_leaf_rules_ignore_braces_in_comments_and_strings():
    assert [r.prelude for r in leaf_rules('/* { */ .a { content: "}"; }')] == [".a"]


def test_declarations_keep_order_and_parentheses():
    body = " a: 1; b: url(data:x;y) ; /* c: 3; */ D : rgba(0, 0,0 , .5) !important"
    assert declarations(body) == [("a", "1"), ("b", "url(data:x;y)"), ("d", "rgba(0, 0,0 , .5) !important")]


def test_selectors_split_on_top_level_commas_only():
    assert selectors(".a, :is(.b, .c) > .d,\n .e") == [".a", ":is(.b, .c) > .d", ".e"]
