from __future__ import annotations

from pathlib import Path

from vaultchef.config import resolve_config
from vaultchef.listing import list_recipes


def test_list_recipes_filters(example_vault: Path, tmp_path: Path, temp_home: Path) -> None:
    cfg = resolve_config({"vault_path": str(example_vault), "project": str(tmp_path)})
    all_recipes = list_recipes(cfg, None, None)
    assert len(all_recipes) == 3
    baking = list_recipes(cfg, "baking", None)
    assert len(baking) == 2
    mains = list_recipes(cfg, None, "main")
    assert len(mains) == 1


def test_list_recipes_missing_dir(tmp_path: Path, temp_home: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path)})
    assert list_recipes(cfg, None, None) == []


def test_list_recipes_skips_bad_files(tmp_path: Path, temp_home: Path) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    recipes.mkdir(parents=True)
    (recipes / "no-frontmatter.md").write_text("# Hi\n", encoding="utf-8")
    (recipes / "bad-yaml.md").write_text("---\n[bad\n---\n", encoding="utf-8")
    (recipes / "list-frontmatter.md").write_text("---\n- a\n---\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path)})
    assert list_recipes(cfg, None, None) == []


def test_list_recipes_tags_string(tmp_path: Path, temp_home: Path) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    recipes.mkdir(parents=True)
    (recipes / "tag.md").write_text(
        """---
recipe_id: 1
title: Taggy
tags: baking
---
""",
        encoding="utf-8",
    )
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path)})
    assert len(list_recipes(cfg, "baking", None)) == 1


def test_list_recipes_unreadable_file(tmp_path: Path, temp_home: Path) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    recipes.mkdir(parents=True)
    unreadable = recipes / "nope.md"
    unreadable.write_text("---\nrecipe_id: 1\ntitle: Nope\n---\n", encoding="utf-8")
    unreadable.chmod(0o000)
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path)})
    try:
        assert list_recipes(cfg, None, None) == []
    finally:
        unreadable.chmod(0o644)
