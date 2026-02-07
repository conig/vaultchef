from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import EffectiveConfig
from ..domain import normalize_tags, split_frontmatter
from ..paths import resolve_vault_paths


def list_recipes(cfg: EffectiveConfig, tag: str | None, category: str | None) -> list[dict[str, Any]]:
    vault = resolve_vault_paths(cfg)
    recipes: list[dict[str, Any]] = []
    if not vault.recipes_dir.exists():
        return recipes

    for path in sorted(vault.recipes_dir.rglob("*.md")):
        data = _parse_frontmatter(path)
        if not data:
            continue
        tags = normalize_tags(data.get("tags"))
        if tag and tag not in tags:
            continue
        if category and str(data.get("category", "")).lower() != category.lower():
            continue
        recipes.append(
            {
                "recipe_id": data.get("recipe_id"),
                "title": data.get("title"),
                "path": str(path),
                "category": data.get("category"),
                "tags": tags,
            }
        )
    return recipes


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    return split_frontmatter(text).frontmatter
