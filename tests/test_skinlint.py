from skinlint import GLASS_ALLOWLIST, lint

CAPSULE = sorted(GLASS_ALLOWLIST)[0]


def core(css):
    return lint({"skin/30-header.css": css})


def test_clean_glass_passes():
    assert core(f"{CAPSULE} {{ -webkit-backdrop-filter: blur(20px); backdrop-filter: blur(20px); }}") == []


def test_glass_needs_its_webkit_twin_first():
    p = core(f"{CAPSULE} {{ backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); }}")
    assert any("identical -webkit-backdrop-filter" in x for x in p)


def test_glass_twins_must_match():
    p = core(f"{CAPSULE} {{ -webkit-backdrop-filter: blur(10px); backdrop-filter: blur(20px); }}")
    assert any("identical -webkit-backdrop-filter" in x for x in p)


def test_glass_rejects_var_and_url():
    p = core(f"{CAPSULE} {{ -webkit-backdrop-filter: blur(var(--b)); backdrop-filter: blur(var(--b)); }}")
    assert sum("literal values" in x for x in p) == 2


def test_glass_outside_the_allowlist_fails():
    p = core(".card { -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); }")
    assert p == ["skin/30-header.css:1: glass on '.card', which is not on the glass allowlist"]


def test_switching_glass_off_is_allowed_anywhere():
    assert core(".layout-mobile .x { -webkit-backdrop-filter: none !important; backdrop-filter: none !important; }") == []


def test_lone_webkit_filter_fails():
    p = core(f"{CAPSULE} {{ -webkit-backdrop-filter: blur(2px); }}")
    assert any("without backdrop-filter" in x for x in p)


def test_glass_inside_a_media_query_is_checked():
    p = core("@media (min-width: 1px) {\n.card { -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); }\n}")
    assert p == ["skin/30-header.css:2: glass on '.card', which is not on the glass allowlist"]


def test_import_font_face_and_will_change_fail_with_file_and_line():
    p = core('.a { color: inherit; }\n@import "x.css";\n@font-face { font-family: x; }\n.b { will-change: transform; }')
    assert p == [
        "skin/30-header.css:2: @import is not allowed",
        "skin/30-header.css:3: @font-face belongs to build.py, which embeds the font",
        "skin/30-header.css:4: will-change is not allowed",
    ]


def test_comments_and_strings_are_not_code():
    assert core('/* @import "x"; will-change */ .a { font-family: "@font-face"; }') == []


def test_plugin_file_needs_its_header():
    assert lint({"skin/plugins/x.css": ".a { color: inherit; }"})[0].startswith("skin/plugins/x.css:1: a plugin file starts with")


def test_plugin_file_stays_inside_its_roots():
    files = {
        "skin/plugins/mb.css": "/* plugin: Media Bar; roots: #slides-container */\n"
        "#slides-container .dot { color: inherit; }\n.card { color: inherit; }\n"
    }
    assert lint(files) == ["skin/plugins/mb.css:3: '.card' selects outside this plugin's roots"]


def test_core_never_selects_plugin_markup():
    files = {
        "skin/plugins/mb.css": "/* plugin: Media Bar; roots: #slides-container */\n",
        "skin/40-rows-cards.css": "#slides-container .x { color: inherit; }",
    }
    assert lint(files) == ["skin/40-rows-cards.css:1: core file selects plugin markup (#slides-container)"]


def test_content_never_adds_visible_text():
    p = core('.a::before { content: "New"; }\n.b::after { content: ""; }\n/* content: "x" */')
    assert p == ["skin/30-header.css:1: content adds visible text; only empty strings are allowed"]


def test_selectors_avoid_emotion_hashes_and_localized_labels():
    p = core(".css-1x2y3z { color: inherit; }\n[aria-label] .x { color: inherit; }")
    assert len(p) == 2
    assert p[0].startswith("skin/30-header.css:1:") and "emotion hash" in p[0]
    assert p[1].startswith("skin/30-header.css:2:") and "aria-label" in p[1]


def test_colours_come_from_the_palette():
    # One palette in the tokens file restyles the whole skin, so rules never write a colour out.
    css = (
        ".a { color: #fff; }\n.b { background: linear-gradient(rgba(5, 6, 10, 0.5), transparent); }\n"
        ".c { border-color: white; }\n.d { box-shadow: 0 0 2px hsl(0 0% 0%); }"
    )
    p = core(css)
    assert [x.split(":")[1] for x in p] == ["1", "2", "3", "4"] and all("palette" in x for x in p), p
    assert lint({"skin/00-tokens.css": ":root { --nf-light: #fff; --nf-ink: rgba(5, 6, 10, 1); }"}) == []


def test_every_named_and_system_colour_is_a_literal():
    css = ".a { color: crimson; }\n.b { border-color: DarkSlateGray; }\n.c { background: Canvas; }\n.d { outline-color: whitesmoke; }"
    assert [x.split(":")[1] for x in core(css)] == ["1", "2", "3", "4"]


def test_colours_in_strings_and_nesting_rules_are_linted():
    css = (
        ".a { background-image: url(\"data:image/svg+xml,<svg fill='red'/>\"); }\n"
        ".b { background-image: url('data:image/svg+xml,<svg fill=\"%23ff2448\"/>'); }\n"
        ".c { color: #f00; will-change: transform; & .d { color: inherit; } }"
    )
    p = core(css)
    assert [x.split(":")[1] for x in p if "palette" in x] == ["1", "2", "3"], p
    assert any("will-change" in x for x in p), p


def test_words_that_only_contain_a_colour_name_pass():
    assert core(".a { animation: tan-spin 1s; width: calc(tan(45deg) * 1px); transition: color 1s; color: var(--nf-teal); }") == []


def test_tokens_masks_and_keywords_are_not_colour_literals():
    css = (
        ".a { color: var(--nf-teal); background: color-mix(in srgb, var(--nf-ink) 50%, transparent); }\n"
        ".b { -webkit-mask-image: linear-gradient(#000, transparent); mask-image: linear-gradient(#000, transparent); }\n"
        ".c { border-color: currentColor; white-space: nowrap; }\n/* a white backdrop */"
    )
    assert core(css) == []


def test_a_plugin_may_hand_its_own_variables_the_palette_on_root():
    head = "/* plugin: P; roots: .p- */\n"
    assert lint({"skin/plugins/p.css": head + ":root { --p-accent: var(--nf-neon); }"}) == []
    assert lint({"skin/plugins/p.css": head + ":root { --p-accent: var(--nf-neon); color: inherit; }"}) == [
        "skin/plugins/p.css:2: ':root' selects outside this plugin's roots"
    ]
