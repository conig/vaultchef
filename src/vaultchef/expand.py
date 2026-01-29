from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .errors import MissingFileError


EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
BOUNDARY = "\n\n<!-- vaultchef:recipe:start -->\n\n"
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def expand_cookbook(cookbook_path: str, vault_root: str) -> str:
    path = Path(cookbook_path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MissingFileError(f"Cookbook not found: {cookbook_path}") from exc

    def _replace(match: re.Match[str]) -> str:
        embed = match.group(1)
        content = expand_embed(embed, vault_root)
        return BOUNDARY + content

    return EMBED_RE.sub(_replace, text)


def expand_embed(embed: str, vault_root: str) -> str:
    path = resolve_embed_path(embed, vault_root)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MissingFileError(f"Embedded note not found: {path}") from exc
    meta, body = _split_frontmatter(content)
    title = meta.get("title")
    if title:
        return f"## {title}\n\n{body}"
    return body


def _split_frontmatter(md: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(md)
    if not match:
        return {}, md
    raw = match.group(1)
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return data, md[match.end():]


def resolve_embed_path(embed: str, vault_root: str) -> Path:
    target = embed.split("|", 1)[0].strip()
    if "#" in target:
        raise MissingFileError(f"Embed references are not supported yet: {embed}")
    if not target.endswith(".md"):
        target = f"{target}.md"
    path = Path(vault_root) / target
    if not path.exists():
        raise MissingFileError(f"Embedded note not found: {path}")
    return path
