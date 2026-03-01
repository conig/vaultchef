from __future__ import annotations

from pathlib import Path

from vaultchef.services.web_service import (
    _build_cookbook_entries,
    _coerce_bool,
    _collect_recipe_sources,
    _dedupe_ordered,
    _int_value,
    _simple_markdown_to_html,
    _string_value,
    _unique_slug,
)


# Purpose: verify collect recipe sources handles missing dir and unreadable file.
def test_collect_recipe_sources_handles_missing_and_unreadable(tmp_path: Path, monkeypatch) -> None:
    missing = tmp_path / "missing"
    assert _collect_recipe_sources(missing) == []

    recipes = tmp_path / "Recipes"
    recipes.mkdir()
    good = recipes / "Good.md"
    bad = recipes / "Bad.md"
    good.write_text("---\ntitle: Good\n---\n\nBody", encoding="utf-8")
    bad.write_text("---\ntitle: Bad\n---\n", encoding="utf-8")

    original = Path.read_text

    def fake_read_text(self: Path, *args, **kwargs):
        if self.name == "Bad.md":
            raise OSError("boom")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    sources = _collect_recipe_sources(recipes)
    assert len(sources) == 1
    assert sources[0][0].name == "Good.md"


# Purpose: verify cookbook entry builder handles missing dir and unresolved embeds.
def test_build_cookbook_entries_handles_errors(tmp_path: Path, monkeypatch) -> None:
    vault_root = tmp_path / "Vault"
    recipes_dir = vault_root / "Recipes"
    cookbooks_dir = vault_root / "Cookbooks"
    recipes_dir.mkdir(parents=True)
    cookbooks_dir.mkdir(parents=True)

    recipe = recipes_dir / "R1.md"
    recipe.write_text("---\ntitle: R1\n---\n", encoding="utf-8")

    valid = cookbooks_dir / "Valid.md"
    valid.write_text(
        "---\ntitle: Book\n---\n\n![[Recipes/R1]]\n![[Recipes/Missing]]\n",
        encoding="utf-8",
    )
    bad = cookbooks_dir / "Bad.md"
    bad.write_text("---\ntitle: Bad\n---\n", encoding="utf-8")

    original = Path.read_text

    def fake_read_text(self: Path, *args, **kwargs):
        if self.name == "Bad.md":
            raise OSError("boom")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)

    missing_dir_entries = _build_cookbook_entries(tmp_path / "NoCookbooks", vault_root, {})
    assert missing_dir_entries == []

    entries = _build_cookbook_entries(cookbooks_dir, vault_root, {})
    assert len(entries) == 1
    assert entries[0]["title"] == "Book"
    assert entries[0]["recipe_slugs"] == []


# Purpose: verify simple markdown renderer closes list transitions and paragraphs.
def test_simple_markdown_to_html_transitions() -> None:
    html = _simple_markdown_to_html(
        "Alpha line\n"
        "Beta line\n\n"
        "1. Step one\n"
        "- Item after ordered\n"
        "1. Step two\n"
        "Plain tail\n"
    )
    assert "<p>Alpha line Beta line</p>" in html
    assert "<ol>" in html
    assert "</ol>" in html
    assert "<ul>" in html
    assert "</ul>" in html
    assert "<p>Plain tail</p>" in html


# Purpose: verify web service normalization helpers.
def test_web_service_helpers() -> None:
    used = {"slug"}
    assert _unique_slug("slug", used) == "slug-2"

    assert _string_value(["a", None, "b"]) == "a, b"

    assert _int_value(3) == 3
    assert _int_value("7") == 7
    assert _int_value("nope") is None

    assert _coerce_bool(1) is True
    assert _coerce_bool("yes") is True
    assert _coerce_bool("off") is False
    assert _coerce_bool("maybe") is False

    assert _dedupe_ordered(["a", "b", "a", "c"]) == ["a", "b", "c"]
