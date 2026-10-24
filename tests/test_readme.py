"""The README states only what ships and what was tested."""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()


def section(title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", README, re.M | re.S)
    assert m, f"no ## {title} section"
    return m[1]


def test_every_image_the_readme_shows_ships_and_stays_small():
    images = re.findall(r"\((docs/screenshots/[\w-]+\.webp)\)", README)
    assert len(images) >= 8, images
    for rel in images:
        assert (ROOT / rel).exists() and (ROOT / rel).stat().st_size <= 400_000, rel
    assert sum(p.stat().st_size for p in (ROOT / "docs" / "screenshots").iterdir()) <= 2_500_000


def test_compatibility_names_the_tested_jellyfin_and_plugin_versions():
    text = section("Compatibility")
    tag = re.search(r"^\s*image:\s*(\S+)", (ROOT / "demo" / "compose.yml").read_text(), re.M)[1]
    assert f"`{tag}`" in text
    for p in json.loads((ROOT / "demo" / "plugins.json").read_text())["plugins"]:
        assert f"| {p['name']} | {p['version']} |" in text, p["name"]


def test_install_snippets_put_every_import_first():
    # Every CSS snippet in the README, the preset's two-line one included.
    blocks = re.findall(r"```css\n(.*?)```", README, re.S)
    assert len(blocks) >= 2
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        imports = [i for i, line in enumerate(lines) if line.startswith("@import")]
        assert imports == list(range(len(imports))), block
    assert "first" in section("Install").lower()


def test_readme_links_point_at_files_that_ship():
    for rel in re.findall(r"NeonFin@v[\d.]+/(palettes/[\w-]+\.css)", README):
        assert (ROOT / rel).exists(), rel
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    for asset in re.findall(r"releases/latest/download/([\w.-]+)", README):
        assert asset in workflow, asset


def test_the_readme_claims_only_what_is_measured():
    assert "never slower" not in README.lower()
    assert "dist/palette.html" not in README


def test_issue_forms_ask_what_a_styling_bug_needs():
    bug = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug.yml").read_text()
    for label in ("Jellyfin version", "NeonFin version", "Browser", "Desktop or phone", "Plugins", "Screenshot", "NeonFin removed"):
        assert label in bug, label
    assert "blank_issues_enabled: false" in (ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text()
