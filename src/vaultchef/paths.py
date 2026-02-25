from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import EffectiveConfig


@dataclass(frozen=True)
class VaultPaths:
    vault_root: Path
    recipes_dir: Path
    cookbooks_dir: Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    build_dir: Path
    cache_dir: Path
    templates_dir: Path
    filters_dir: Path
    template_path: Path
    lua_filter_path: Path
    web_template_path: Path
    web_lua_filter_path: Path
    style_dir: Path


def resolve_vault_paths(cfg: EffectiveConfig) -> VaultPaths:
    root = Path(cfg.vault_path)
    return VaultPaths(
        vault_root=root,
        recipes_dir=root / cfg.recipes_dir,
        cookbooks_dir=root / cfg.cookbooks_dir,
    )


def resolve_project_paths(cfg: EffectiveConfig) -> ProjectPaths:
    root = Path(cfg.project_dir)
    repo_root = Path(__file__).resolve().parents[2]
    templates_fallback = repo_root / "templates"
    filters_fallback = repo_root / "filters"

    template_path = _resolve_file(root, Path(cfg.pandoc.template), templates_fallback / "cookbook.tex")
    lua_filter_path = _resolve_file(root, Path(cfg.pandoc.lua_filter), filters_fallback / "recipe.lua")
    web_template_path = _resolve_file(root, Path("templates/cookbook.html"), templates_fallback / "cookbook.html")
    web_lua_filter_path = _resolve_file(root, Path("filters/web.lua"), filters_fallback / "web.lua")
    style_dir = _resolve_dir(root, Path(cfg.pandoc.style_dir), templates_fallback)

    return ProjectPaths(
        root=root,
        build_dir=root / cfg.build_dir,
        cache_dir=root / cfg.cache_dir,
        templates_dir=templates_fallback,
        filters_dir=filters_fallback,
        template_path=template_path,
        lua_filter_path=lua_filter_path,
        web_template_path=web_template_path,
        web_lua_filter_path=web_lua_filter_path,
        style_dir=style_dir,
    )


def _resolve_file(root: Path, rel: Path, fallback: Path) -> Path:
    candidate = rel if rel.is_absolute() else root / rel
    if candidate.exists():
        return candidate
    return fallback


def _resolve_dir(root: Path, rel: Path, fallback: Path) -> Path:
    candidate = rel if rel.is_absolute() else root / rel
    if candidate.exists():
        return candidate
    return fallback
