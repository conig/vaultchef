from __future__ import annotations

from pathlib import Path

from vaultchef.services.web_service import (
    _build_cookbook_entries,
    _build_recipe_entries,
    _coerce_bool,
    _collect_recipe_sources,
    _copy_recipe_images,
    _dedupe_ordered,
    _extract_cookbook_reader_blocks,
    _image_meta_value,
    _int_value,
    _simple_markdown_to_html,
    _string_value,
    _strip_internal_recipe_fields,
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

    recipe_map = {str(recipe.resolve()): {"slug": "r1", "cookbook_slugs": []}}
    entries = _build_cookbook_entries(cookbooks_dir, vault_root, recipe_map)
    assert len(entries) == 1
    assert entries[0]["title"] == "Book"
    assert entries[0]["recipe_slugs"] == ["r1"]


# Purpose: verify recipe image copy pipeline populates app asset references.
def test_recipe_image_copy_pipeline(tmp_path: Path) -> None:
    vault_root = tmp_path / "Vault"
    recipes_dir = vault_root / "Recipes"
    images_dir = vault_root / "Images"
    recipes_dir.mkdir(parents=True)
    images_dir.mkdir(parents=True)

    source_md = recipes_dir / "R1.md"
    source_md.write_text("---\ntitle: R1\n---\n\nBody", encoding="utf-8")

    image = images_dir / "hero.jpg"
    image.write_bytes(b"fake")

    recipe_sources = [
        (
            source_md.resolve(),
            {"title": "R1", "recipe_id": 1, "image": "Images/hero.jpg"},
            "## Ingredients\n- a\n\n## Method\n1. b\n",
        )
    ]

    recipes = _build_recipe_entries(recipe_sources, vault_root)
    assert recipes[0]["_image_source"].endswith("Images/hero.jpg")

    target_dir = tmp_path / "bundle" / "assets" / "images"
    warnings = _copy_recipe_images(recipes, target_dir)
    assert warnings == []
    assert recipes[0]["image"].startswith("assets/images/")

    copied = tmp_path / "bundle" / recipes[0]["image"]
    assert copied.exists()

    _strip_internal_recipe_fields(recipes)
    assert "_image_source" not in recipes[0]
    assert "path" not in recipes[0]


# Purpose: verify missing image warning does not fail copy step.
def test_recipe_image_missing_warns(tmp_path: Path) -> None:
    recipe = {
        "title": "Missing Hero",
        "image": "Images/missing.jpg",
        "_image_source": str(tmp_path / "Vault" / "Images" / "missing.jpg"),
    }
    warnings = _copy_recipe_images([recipe], tmp_path / "bundle" / "assets" / "images")
    assert len(warnings) == 1
    assert "Missing Hero" in warnings[0]
    assert recipe["image"] == ""


# Purpose: verify cookbook reader blocks preserve intro, chapters, and recipe order.
def test_extract_cookbook_reader_blocks(tmp_path: Path) -> None:
    vault_root = tmp_path / "Vault"
    recipes_dir = vault_root / "Recipes"
    recipes_dir.mkdir(parents=True)

    r1 = recipes_dir / "R1.md"
    r2 = recipes_dir / "R2.md"
    r1.write_text("---\ntitle: One\n---\n", encoding="utf-8")
    r2.write_text("---\ntitle: Two\n---\n", encoding="utf-8")

    recipe_map = {
        str(r1.resolve()): {"slug": "one", "cookbook_slugs": []},
        str(r2.resolve()): {"slug": "two", "cookbook_slugs": []},
    }

    body = (
        "A short intro.\n\n"
        "# First Chapter\n"
        "![[Recipes/R1]]\n"
        "Bridge text\n"
        "# Second Chapter\n"
        "![[Recipes/R2]]\n"
    )

    intro_html, blocks, recipe_slugs = _extract_cookbook_reader_blocks(body, vault_root, recipe_map)
    assert "A short intro." in intro_html
    assert recipe_slugs == ["one", "two"]
    assert blocks[0]["type"] == "chapter"
    assert blocks[1] == {"type": "recipe", "slug": "one"}
    assert any(block.get("type") == "text" for block in blocks)


# Purpose: verify cookbook reader handles unresolved and empty-slug embeds.
def test_extract_cookbook_reader_blocks_skips_unusable_embeds(tmp_path: Path) -> None:
    vault_root = tmp_path / "Vault"
    recipes_dir = vault_root / "Recipes"
    recipes_dir.mkdir(parents=True)

    r1 = recipes_dir / "R1.md"
    r2 = recipes_dir / "R2.md"
    r1.write_text("---\ntitle: One\n---\n", encoding="utf-8")
    r2.write_text("---\ntitle: Two\n---\n", encoding="utf-8")

    recipe_map = {
        str(r1.resolve()): {"slug": "", "cookbook_slugs": []},
    }

    body = "# Chapter\n![[Recipes/R1]] trailing text\n![[Recipes/R2]]\n"
    _intro_html, blocks, recipe_slugs = _extract_cookbook_reader_blocks(body, vault_root, recipe_map)
    assert recipe_slugs == []
    assert any(block.get("type") == "text" and "trailing text" in block.get("html", "") for block in blocks)


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
    assert _image_meta_value([]) is None
    assert _image_meta_value([" first.jpg "]) == "first.jpg"
