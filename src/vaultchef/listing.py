from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Optional
import yaml

from .config import EffectiveConfig
from .paths import resolve_vault_paths


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def list_recipes(cfg: EffectiveConfig, tag: Optional[str], category: Optional[str]) -> list[dict[str, Any]]:
    vault = resolve_vault_paths(cfg)
    recipes: list[dict[str, Any]] = []
    if not vault.recipes_dir.exists():
        return recipes

    for path in sorted(vault.recipes_dir.rglob("*.md")):
        data = _parse_frontmatter(path)
        if not data:
            continue
        if tag and tag not in _normalize_tags(data.get("tags")):
            continue
        if category and str(data.get("category", "")).lower() != category.lower():
            continue
        recipes.append(
            {
                "recipe_id": data.get("recipe_id"),
                "title": data.get("title"),
                "path": str(path),
                "category": data.get("category"),
                "tags": data.get("tags", []),
            }
        )
    return recipes


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = FRONTMATTER_RE.search(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _normalize_tags(tags: Any) -> list[str]:
    if isinstance(tags, list):
        return [str(t) for t in tags]
    if isinstance(tags, str):
        return [tags]
    return []
