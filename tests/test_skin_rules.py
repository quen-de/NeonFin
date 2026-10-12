import pathlib

import cssscan

SKIN = pathlib.Path(__file__).resolve().parents[1] / "skin"
NAV = ".MuiAppBar-root > .MuiToolbar-root:first-child > .MuiStack-root"


def test_the_nav_capsule_hides_its_scrollbar_where_scrollbar_width_is_unknown():
    # Safari before 18.2 ignores scrollbar-width and would draw the global 10px scrollbar.
    rules = [r for r in cssscan.leaf_rules((SKIN / "30-header.css").read_text()) if r.prelude == f"{NAV}::-webkit-scrollbar"]
    assert rules and ("display", "none") in cssscan.declarations(rules[0].body)


def test_media_bar_enhanced_rules_leave_media_bar_alone():
    # Both plugins build #slides-container and share class names (.misc-info, .genre,
    # .gradient-overlay), so a rule meant for Media Bar Enhanced would also restyle Media Bar.
    # Only Media Bar Enhanced puts .jellyfin-v12 on the body.
    css = (SKIN / "plugins/media-bar-enhanced.css").read_text()
    selected = [s for r in cssscan.leaf_rules(css) for s in cssscan.selectors(r.prelude)]
    assert selected and [s for s in selected if ".jellyfin-v12 #slides-container" not in s] == []
