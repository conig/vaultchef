from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import yaml


FRONTMATTER_RE = re.compile(r"^\ufeff?\s*---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


@dataclass(frozen=True)
class MarkdownDocument:
    frontmatter: dict[str, Any]
    body: str


def split_frontmatter(md: str) -> MarkdownDocument:
    match = FRONTMATTER_RE.match(md)
    if not match:
        return MarkdownDocument(frontmatter={}, body=md)

    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        data = {}

    if not isinstance(data, dict):
        data = {}

    return MarkdownDocument(frontmatter=data, body=md[match.end() :])


def extract_sections(md: str, heading_level: int = 2) -> dict[str, str]:
    prefix = "#" * heading_level + " "
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in md.splitlines():
        if line.startswith(prefix):
            current = line[len(prefix) :].strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)

    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def normalize_tags(tags: Any) -> list[str]:
    if isinstance(tags, list):
        return [str(tag) for tag in tags]
    if isinstance(tags, str):
        return [tags]
    return []
