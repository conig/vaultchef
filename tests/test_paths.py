from __future__ import annotations

from pathlib import Path

from vaultchef.config import resolve_config
from vaultchef.paths import resolve_vault_paths, resolve_project_paths


def test_resolve_vault_paths(tmp_path: Path, temp_home: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path)})
    paths = resolve_vault_paths(cfg)
    assert paths.vault_root == vault


def test_resolve_project_paths_prefers_project_files(tmp_path: Path, temp_home: Path) -> None:
    project = tmp_path / "Project"
    project.mkdir()
    templates = project / "templates"
    filters = project / "filters"
    templates.mkdir()
    filters.mkdir()
    (templates / "cookbook.tex").write_text("% ok", encoding="utf-8")
    (filters / "recipe.lua").write_text("return {}", encoding="utf-8")

    cfg = resolve_config(
        {
            "vault_path": str(tmp_path / "Vault"),
            "project": str(project),
            "template": "templates/cookbook.tex",
            "lua_filter": "filters/recipe.lua",
            "style_dir": "templates",
        }
    )
    paths = resolve_project_paths(cfg)
    assert paths.template_path == templates / "cookbook.tex"
    assert paths.lua_filter_path == filters / "recipe.lua"
    assert paths.style_dir == templates
