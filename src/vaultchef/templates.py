from __future__ import annotations

from pathlib import Path
from typing import Any


def render_recipe_template(recipe_id: str, title: str, **kwargs: Any) -> str:
    lines = ["---", f"recipe_id: {recipe_id}", f"title: {title}"]
    for key in ("course", "category", "cuisine", "serves", "prep", "cook", "rest", "menu", "source"):
        if kwargs.get(key):
            lines.append(f"{key}: {kwargs[key]}")
    lines.append("---")
    lines.append("")
    lines.append("## Ingredients")
    lines.append("- ")
    lines.append("")
    lines.append("## Method")
    lines.append("1. ")
    lines.append("")
    lines.append("## Notes")
    lines.append("- ")
    return "\n".join(lines) + "\n"


def render_cookbook_template(title: str, **kwargs: Any) -> str:
    lines = ["---", f"title: {title}"]
    if kwargs.get("subtitle"):
        lines.append(f"subtitle: {kwargs['subtitle']}")
    if kwargs.get("author"):
        lines.append(f"author: {kwargs['author']}")
    if kwargs.get("style"):
        lines.append(f"style: {kwargs['style']}")
    lines.append("---")
    lines.append("")
    lines.append("# Chapter")
    lines.append("![[Recipes/Example Recipe]]")
    return "\n".join(lines) + "\n"


def render_cookbook_note(
    title: str,
    embeds: list[str],
    subtitle: str | None = None,
    author: str | None = None,
    style: str | None = None,
) -> str:
    lines = ["---", f"title: {title}"]
    if subtitle:
        lines.append(f"subtitle: {subtitle}")
    if author:
        lines.append(f"author: {author}")
    if style:
        lines.append(f"style: {style}")
    lines.append("---")
    lines.append("")
    lines.append("# Recipes")
    for embed in embeds:
        lines.append(f"![[{embed}]]")
    lines.append("")
    return "\n".join(lines) + "\n"


def write_template_file(content: str, filename: str, cwd: str) -> str:
    path = Path(cwd) / filename
    if path.exists():
        raise FileExistsError(f"File already exists: {path}")
    path.write_text(content, encoding="utf-8")
    return str(path)
