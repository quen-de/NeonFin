import pathlib

import cssscan

SKIN = pathlib.Path(__file__).resolve().parents[1] / "skin"
NAV = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root"


def test_the_nav_capsule_hides_its_scrollbar_where_scrollbar_width_is_unknown():
    # Safari before 18.2 ignores scrollbar-width and would draw the global 10px scrollbar.
    rules = [r for r in cssscan.leaf_rules((SKIN / "30-header.css").read_text()) if r.prelude == f"{NAV}::-webkit-scrollbar"]
    assert rules and ("display", "none") in cssscan.declarations(rules[0].body)


def test_a_card_looks_for_keyboard_focus_only_once_focus_is_inside_it():
    # :has(:focus-visible) on every card costs a grid page about a third more style time;
    # behind :focus-within it runs only on the card that holds focus.
    found = [
        s
        for path in sorted(SKIN.rglob("*.css"))
        for rule in cssscan.leaf_rules(path.read_text())
        for s in cssscan.selectors(rule.prelude)
        if ":has(:focus-visible)" in s
    ]
    assert found and all(".card:focus-within:is(:focus-visible, :has(:focus-visible))" in s for s in found), found
