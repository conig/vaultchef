from __future__ import annotations

import re
from typing import Any

import yaml

from .domain import extract_sections
from .errors import ValidationError


def validate_recipe(md: str, source_path: str) -> None:
    front = _parse_frontmatter(md, source_path)
    if "recipe_id" not in front or "title" not in front:
        raise ValidationError(f"{source_path}: missing required frontmatter keys")

    sections = extract_sections(md)
    if "Ingredients" not in sections or "Method" not in sections:
        raise ValidationError(f"{source_path}: missing required sections")

    if not _has_bullet(sections["Ingredients"]):
        raise ValidationError(f"{source_path}: ingredients must include at least one bullet")
    if not _has_numbered_step(sections["Method"]):
        raise ValidationError(f"{source_path}: method must include at least one numbered step")


def _parse_frontmatter(md: str, source_path: str) -> dict[str, Any]:
    from .domain import FRONTMATTER_RE

    match = FRONTMATTER_RE.search(md)
    if not match:
        raise ValidationError(f"{source_path}: missing YAML frontmatter")

    raw = match.group(1)
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise ValidationError(f"{source_path}: invalid YAML frontmatter") from exc

    if not isinstance(data, dict):
        raise ValidationError(f"{source_path}: frontmatter must be a mapping")
    return data


def _has_bullet(text: str) -> bool:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ", "+ ")):
            return True
    return False


def _has_numbered_step(text: str) -> bool:
    for line in text.splitlines():
        if re.match(r"^\s*\d+\.\s+", line):
            return True
    return False


__all__ = ["validate_recipe", "extract_sections"]
