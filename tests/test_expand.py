from __future__ import annotations

from pathlib import Path
import pytest

from vaultchef.expand import expand_cookbook, resolve_embed_path, expand_embed, _split_frontmatter, _image_marker
from vaultchef.errors import MissingFileError


def test_expand_cookbook_replaces_embeds(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    cookbooks = vault / "Cookbooks"
    recipes.mkdir(parents=True)
    cookbooks.mkdir(parents=True)

    recipe_path = recipes / "R1.md"
    recipe_path.write_text("---\nrecipe_id: 1\ntitle: R1\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n", encoding="utf-8")

    cookbook = cookbooks / "Book.md"
    cookbook.write_text("# Test\n![[Recipes/R1]]\n", encoding="utf-8")

    baked = expand_cookbook(str(cookbook), str(vault))
    assert "vaultchef:recipe:start" in baked
    assert "## R1" in baked


def test_resolve_embed_path_supports_md(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    recipes.mkdir(parents=True)
    recipe_path = recipes / "R1.md"
    recipe_path.write_text("ok", encoding="utf-8")
    resolved = resolve_embed_path("Recipes/R1.md", str(vault))
    assert resolved == recipe_path


def test_resolve_embed_path_rejects_heading_refs(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    with pytest.raises(MissingFileError):
        resolve_embed_path("Recipes/R1#Heading", str(vault))


def test_expand_embed_missing_file(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    cookbook = tmp_path / "Book.md"
    cookbook.write_text("![[Recipes/Nope]]", encoding="utf-8")
    with pytest.raises(MissingFileError):
        expand_cookbook(str(cookbook), str(vault))


def test_expand_cookbook_read_error(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    cookbook = tmp_path / "Cookbook"
    cookbook.mkdir()
    with pytest.raises(MissingFileError):
        expand_cookbook(str(cookbook), str(vault))


def test_expand_embed_read_error(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    recipes.mkdir(parents=True)
    recipe_dir = recipes / "R1.md"
    recipe_dir.mkdir()
    cookbook = tmp_path / "Cook.md"
    cookbook.write_text("![[Recipes/R1]]", encoding="utf-8")
    with pytest.raises(MissingFileError):
        expand_cookbook(str(cookbook), str(vault))


def test_expand_embed_no_title(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    recipes.mkdir(parents=True)
    recipe_path = recipes / "R1.md"
    recipe_path.write_text(
        "---\nrecipe_id: 1\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n",
        encoding="utf-8",
    )
    text = expand_embed("Recipes/R1", str(vault))
    assert text.lstrip().startswith("## Ingredients")


def test_expand_embed_with_image_marker(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    recipes.mkdir(parents=True)
    recipe_path = recipes / "R1.md"
    recipe_path.write_text(
        "---\nrecipe_id: 1\ntitle: R1\nimage: Images/r1.jpg\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n",
        encoding="utf-8",
    )
    text = expand_embed("Recipes/R1", str(vault))
    assert "vaultchef:image:" in text
    assert str((vault / "Images" / "r1.jpg").as_posix()) in text


def test_split_frontmatter_edge_cases() -> None:
    meta, body = _split_frontmatter("No frontmatter")
    assert meta == {}
    assert body == "No frontmatter"
    meta, _ = _split_frontmatter("---\n- a\n---\nbody")
    assert meta == {}
    meta, _ = _split_frontmatter("---\n: [\n---\nbody")
    assert meta == {}


def test_image_marker_variants() -> None:
    vault = "/vault"
    assert _image_marker({"image": ""}, vault) is None
    assert _image_marker({"image": []}, vault) is None
    assert _image_marker({"image": {"path": "x"}}, vault) is None
    assert _image_marker({"image": ["one.jpg", "two.jpg"]}, vault) == "<!-- vaultchef:image:/vault/one.jpg -->"
