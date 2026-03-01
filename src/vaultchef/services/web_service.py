from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from typing import Any

from ..config import EffectiveConfig
from ..domain import normalize_tags, split_frontmatter
from ..expand import EMBED_RE, resolve_embed_path
from ..paths import resolve_project_paths, resolve_vault_paths

_BOOL_TRUE = {"1", "true", "yes", "on"}
_BOOL_FALSE = {"0", "false", "no", "off"}
_FLAG_KEYS = ("vegetarian", "vegan", "gluten_free", "dairy_free")


def build_web_library(
    cookbook_name: str,
    cfg: EffectiveConfig,
    dry_run: bool,
    verbose: bool,
) -> tuple[Path, Path]:
    del cookbook_name
    del verbose

    vault = resolve_vault_paths(cfg)
    project = resolve_project_paths(cfg)

    library = _build_library_index(vault.vault_root, vault.recipes_dir, vault.cookbooks_dir)

    bundle_name = "vaultchef-web"
    build_bundle = project.build_dir / bundle_name
    content_index = build_bundle / "content" / "index.json"
    final_bundle = Path.cwd() / bundle_name

    if not dry_run:
        build_bundle.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(project.webapp_template_dir, build_bundle, dirs_exist_ok=True)
        content_index.parent.mkdir(parents=True, exist_ok=True)
        content_index.write_text(json.dumps(library, indent=2, ensure_ascii=False), encoding="utf-8")
        shutil.copytree(build_bundle, final_bundle, dirs_exist_ok=True)

    return content_index, final_bundle


def _build_library_index(vault_root: Path, recipes_dir: Path, cookbooks_dir: Path) -> dict[str, Any]:
    recipe_sources = _collect_recipe_sources(recipes_dir)
    recipes = _build_recipe_entries(recipe_sources)
    recipe_by_path = {entry["path"]: entry for entry in recipes}

    cookbooks = _build_cookbook_entries(cookbooks_dir, vault_root, recipe_by_path)
    cookbooks_by_slug = {item["slug"] for item in cookbooks}

    for recipe in recipes:
        recipe["cookbook_slugs"] = sorted(slug for slug in recipe["cookbook_slugs"] if slug in cookbooks_by_slug)

    recipes.sort(key=lambda item: item["title"].lower())
    cookbooks.sort(key=lambda item: item["title"].lower())

    facets = {
        "tags": sorted({tag for recipe in recipes for tag in recipe["tags"]}),
        "categories": sorted({recipe["category"] for recipe in recipes if recipe["category"]}),
        "courses": sorted({recipe["course"] for recipe in recipes if recipe["course"]}),
        "flags": [flag for flag in _FLAG_KEYS if any(recipe["flags"].get(flag) for recipe in recipes)],
    }

    # Remove internal fields before serialization.
    for recipe in recipes:
        recipe.pop("path", None)

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "recipes": recipes,
        "cookbooks": cookbooks,
        "facets": facets,
    }


def _collect_recipe_sources(recipes_dir: Path) -> list[tuple[Path, dict[str, Any], str]]:
    if not recipes_dir.exists():
        return []

    sources: list[tuple[Path, dict[str, Any], str]] = []
    for path in sorted(recipes_dir.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        doc = split_frontmatter(text)
        sources.append((path.resolve(), doc.frontmatter, doc.body))
    return sources


def _build_recipe_entries(recipe_sources: list[tuple[Path, dict[str, Any], str]]) -> list[dict[str, Any]]:
    used_slugs: set[str] = set()
    recipes: list[dict[str, Any]] = []

    for path, meta, body in recipe_sources:
        title = _string_value(meta.get("title")) or path.stem
        recipe_id = _string_value(meta.get("recipe_id"))
        slug_base = title
        if recipe_id:
            slug_base = f"recipe-{recipe_id}-{title}"
        slug = _unique_slug(_slugify(slug_base), used_slugs)

        tags = normalize_tags(meta.get("tags"))
        sections = _split_sections(body)

        ingredients_md = sections.get("ingredients", "")
        method_md = sections.get("method", "")
        notes_md = sections.get("notes", "")
        intro_md = sections.get("__intro__", "")

        ingredients_items = _extract_list_items(ingredients_md, ordered=False)
        method_items = _extract_list_items(method_md, ordered=True)

        search_fields = [
            title,
            _string_value(meta.get("menu")) or "",
            _string_value(meta.get("category")) or "",
            _string_value(meta.get("course")) or "",
            _string_value(meta.get("cuisine")) or "",
            " ".join(tags),
            ingredients_md,
            method_md,
            notes_md,
            intro_md,
        ]

        recipes.append(
            {
                "id": recipe_id,
                "slug": slug,
                "title": title,
                "menu": _string_value(meta.get("menu")) or "",
                "category": _string_value(meta.get("category")) or "",
                "course": _string_value(meta.get("course")) or "",
                "cuisine": _string_value(meta.get("cuisine")) or "",
                "occasion": _string_value(meta.get("occasion")) or "",
                "serves": _string_value(meta.get("serves")) or "",
                "prep": _string_value(meta.get("prep")) or "",
                "cook": _string_value(meta.get("cook")) or "",
                "rest": _string_value(meta.get("rest")) or "",
                "difficulty": _int_value(meta.get("difficulty")),
                "image": _string_value(meta.get("image")) or "",
                "tags": sorted(tag for tag in tags if tag),
                "flags": {flag: _coerce_bool(meta.get(flag)) for flag in _FLAG_KEYS},
                "sections": {
                    "intro_html": _simple_markdown_to_html(intro_md),
                    "ingredients_html": _simple_markdown_to_html(ingredients_md),
                    "method_html": _simple_markdown_to_html(method_md),
                    "notes_html": _simple_markdown_to_html(notes_md),
                },
                "ingredients_items": ingredients_items,
                "method_items": method_items,
                "cookbook_slugs": [],
                "search_text": _collapse_whitespace(" ".join(search_fields)).lower(),
                "path": str(path),
            }
        )

    return recipes


def _build_cookbook_entries(
    cookbooks_dir: Path,
    vault_root: Path,
    recipe_by_path: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not cookbooks_dir.exists():
        return []

    used_slugs: set[str] = set()
    cookbooks: list[dict[str, Any]] = []

    for path in sorted(cookbooks_dir.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        doc = split_frontmatter(text)
        meta = doc.frontmatter
        title = _string_value(meta.get("title")) or path.stem
        slug = _unique_slug(_slugify(title), used_slugs)

        recipe_slugs: list[str] = []
        for match in EMBED_RE.finditer(text):
            embed = match.group(1)
            try:
                recipe_path = resolve_embed_path(embed, str(vault_root)).resolve()
            except Exception:
                continue
            recipe = recipe_by_path.get(str(recipe_path))
            if recipe is None:
                continue
            recipe_slugs.append(recipe["slug"])
            recipe["cookbook_slugs"].append(slug)

        cookbooks.append(
            {
                "slug": slug,
                "title": title,
                "subtitle": _string_value(meta.get("subtitle")) or "",
                "author": _string_value(meta.get("author")) or "",
                "date": _string_value(meta.get("date")) or "",
                "description": _string_value(meta.get("description")) or "",
                "album_title": _string_value(meta.get("album_title")) or "",
                "album_artist": _string_value(meta.get("album_artist")) or "",
                "album_style": _string_value(meta.get("album_style")) or "",
                "album_youtube_url": _string_value(meta.get("album_youtube_url")) or "",
                "recipe_slugs": _dedupe_ordered(recipe_slugs),
            }
        )

    return cookbooks


def _split_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"__intro__": []}
    current = "__intro__"

    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return {key: "\n".join(lines).strip() for key, lines in sections.items()}


def _extract_list_items(text: str, ordered: bool) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if ordered:
            match = re.match(r"^\d+\.\s+(.+)$", stripped)
            if match:
                items.append(match.group(1).strip())
        else:
            match = re.match(r"^[-*]\s+(.+)$", stripped)
            if match:
                items.append(match.group(1).strip())
    return items


def _simple_markdown_to_html(text: str) -> str:
    import html

    lines = text.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    in_ul = False
    in_ol = False

    def close_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append(f"<p>{html.escape(' '.join(paragraph).strip())}</p>")
            paragraph = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            close_paragraph()
            close_lists()
            continue

        if line.startswith("### "):
            close_paragraph()
            close_lists()
            out.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", line)
        if bullet:
            close_paragraph()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{html.escape(bullet.group(1).strip())}</li>")
            continue

        ordered = re.match(r"^\d+\.\s+(.+)$", line)
        if ordered:
            close_paragraph()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{html.escape(ordered.group(1).strip())}</li>")
            continue

        close_lists()
        paragraph.append(line)

    close_paragraph()
    close_lists()
    return "\n".join(out)


def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s_-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or "item"


def _unique_slug(base: str, used: set[str]) -> str:
    candidate = base
    idx = 2
    while candidate in used:
        candidate = f"{base}-{idx}"
        idx += 1
    used.add(candidate)
    return candidate


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None).strip() or None
    text = str(value).strip()
    return text or None


def _int_value(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if not isinstance(value, str):
        return False
    text = value.strip().lower()
    if text in _BOOL_TRUE:
        return True
    if text in _BOOL_FALSE:
        return False
    return False


def _dedupe_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
