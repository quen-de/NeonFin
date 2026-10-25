"""The README states only what ships and what was tested."""

import json
import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()


def section(title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", README, re.M | re.S)
    assert m, f"no ## {title} section"
    return m[1]


def test_every_image_the_readme_shows_ships_and_stays_small():
    images = re.findall(r"\((docs/screenshots/[\w-]+\.webp)\)", README)
    assert len(images) >= 7, images
    for rel in images:
        assert (ROOT / rel).exists() and (ROOT / rel).stat().st_size <= 400_000, rel
    assert sum(p.stat().st_size for p in (ROOT / "docs" / "screenshots").iterdir()) <= 2_500_000


def test_every_screenshot_that_ships_is_shown():
    shown = set(re.findall(r"\(docs/screenshots/([\w-]+\.webp)\)", README))
    assert {p.name for p in (ROOT / "docs" / "screenshots").glob("*.webp")} == shown


def test_the_gallery_has_no_empty_cell():
    rows = [line for line in README.splitlines() if line.startswith("| ![")]
    assert rows
    for row in rows:
        assert row.count("![") == 2, row


def test_the_opening_says_why_it_exists_and_how_it_was_built():
    opening = README.split("\n## ", 1)[0]
    assert "Claude Code" in opening and "I built NeonFin to" in opening


def test_features_link_every_plugin_they_name():
    # File Transformation only carries the others, so it stays in Compatibility.
    text = section("Features")
    for p in json.loads((ROOT / "demo" / "plugins.json").read_text())["plugins"]:
        if p["name"] != "File Transformation":
            assert re.search(rf"\[{re.escape(p['name'])}\]\(https://github\.com/[\w-]+/[\w-]+\)", text), p["name"]


def test_contributing_says_why_the_tooling_is_python():
    text = section("Contributing")
    assert "Python" in text and "Playwright" in text and "DEVELOPMENT.md" in text


def test_compatibility_names_the_tested_jellyfin_and_plugin_versions():
    text = section("Compatibility")
    tag = re.search(r"^\s*image:\s*(\S+)", (ROOT / "demo" / "compose.yml").read_text(), re.M)[1]
    assert f"`{tag}`" in text
    for p in json.loads((ROOT / "demo" / "plugins.json").read_text())["plugins"]:
        assert f"| {p['name']} | {p['version']} |" in text, p["name"]


def test_phones_are_claimed_only_as_far_as_they_are_tested():
    # The harness emulates a phone in desktop Chrome; no phone or app is tested on a device.
    text = " ".join(section("Compatibility").split())  # as read, whatever the line wrapping
    assert "phone sizes" in text and "neither is tested on a device" in text
    # The Android app runs the web client, so it does load custom CSS.
    assert "native apps" not in section("Known limitations")


def test_known_limitations_name_every_plugin_built_for_an_older_jellyfin():
    text = section("Known limitations")
    plugins = json.loads((ROOT / "demo" / "plugins.json").read_text())["plugins"]
    assert all(re.fullmatch(r"\d+\.\d+\.\d+\.\d+", p["target_abi"]) for p in plugins)
    for p in plugins:
        if not p["target_abi"].startswith("12."):
            assert f"{p['name']} has no Jellyfin 12 build" in text, p["name"]


def test_install_snippets_put_every_import_first():
    # Every CSS snippet in the README, the preset's two-line one included.
    blocks = re.findall(r"```css\n(.*?)```", README, re.S)
    assert len(blocks) >= 2
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        imports = [i for i, line in enumerate(lines) if line.startswith("@import")]
        assert imports == list(range(len(imports))), block
    # An indented snippet would hide its @import from the check above.
    assert not re.search(r"^[ \t]+@import", "\n".join(blocks), re.M)
    assert "first" in section("Install").lower()


def test_update_offers_the_major_version_that_follows_every_compatible_release():
    # jsDelivr resolves @1 to the newest v1.x tag; semver keeps the palette tokens within a major.
    major = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"].split(".")[0]
    assert f"cdn.jsdelivr.net/gh/quen-de/NeonFin@{major}/dist/neonfin.css" in section("Update")


def test_readme_links_point_at_files_that_ship():
    for rel in re.findall(r"NeonFin@v[\d.]+/(palettes/[\w-]+\.css)", README):
        assert (ROOT / rel).exists(), rel
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    for asset in re.findall(r"releases/latest/download/([\w.-]+)", README):
        assert asset in workflow, asset


def test_the_readme_claims_only_what_is_measured():
    # The gates allow a measured margin over plain Jellyfin (DEVELOPMENT.md, Gates), so no public
    # document may promise more.
    for name in ("README.md", "DESIGN.md", "PRODUCT.md", "DEVELOPMENT.md", "CONTRIBUTING.md"):
        assert "never slower" not in (ROOT / name).read_text().lower(), name
    assert "dist/palette.html" not in README


def test_issue_forms_ask_what_a_styling_bug_needs():
    bug = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug.yml").read_text()
    for label in ("Jellyfin version", "NeonFin version", "Browser", "Desktop or phone", "Plugins", "Screenshot", "NeonFin removed"):
        assert label in bug, label
    assert "blank_issues_enabled: false" in (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text()
