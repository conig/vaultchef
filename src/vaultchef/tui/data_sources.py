from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path

from ..config import EffectiveConfig
from ..domain import split_frontmatter
from ..listing import list_recipes
from ..paths import resolve_vault_paths
from .state import CookbookInfo, RecipeInfo


def load_recipes(cfg: EffectiveConfig) -> list[RecipeInfo]:
    recipes: list[RecipeInfo] = []
    for rec in list_recipes(cfg, None, None):
        path = Path(rec.get("path", ""))
        tags = normalize_tags(rec.get("tags"))
        recipes.append(
            RecipeInfo(
                recipe_id=None if rec.get("recipe_id") is None else str(rec.get("recipe_id")),
                title=str(rec.get("title") or path.stem),
                path=path,
                tags=tags,
            )
        )
    return recipes


def load_cookbooks(cfg: EffectiveConfig) -> list[CookbookInfo]:
    vault = resolve_vault_paths(cfg)
    cookbooks: list[CookbookInfo] = []
    if not vault.cookbooks_dir.exists():
        return cookbooks

    for path in sorted(vault.cookbooks_dir.rglob("*.md")):
        title = parse_frontmatter_title(path) or path.stem
        cookbooks.append(CookbookInfo(title=title, stem=path.stem, path=path))
    return cookbooks


def parse_frontmatter_title(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    title = split_frontmatter(text).frontmatter.get("title")
    if not title:
        return None
    return str(title)


def normalize_tags(tags: object) -> list[str]:
    if isinstance(tags, list):
        return [str(t) for t in tags]
    if isinstance(tags, str):
        return [tags]
    return []


def unique_tags(recipes: list[RecipeInfo]) -> list[str]:
    found: set[str] = set()
    for rec in recipes:
        found.update(rec.tags)
    return sorted(tag for tag in found if tag)


def fuzzy_filter(items: list[object], query: str, key) -> list[object]:
    q = query.strip().lower()
    if not q:
        return items

    scored: list[tuple[float, object]] = []
    for item in items:
        text = str(key(item)).lower()
        score = 1.0 if q in text else SequenceMatcher(None, q, text).ratio()
        if score >= 0.2:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


def embed_path_for_recipe(recipe_path: Path, vault_root: Path) -> str:
    rel = recipe_path.relative_to(vault_root)
    return rel.with_suffix("").as_posix()
