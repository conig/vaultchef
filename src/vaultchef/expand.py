from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .domain import split_frontmatter
from .errors import MissingFileError


EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
BOUNDARY = "\n\n<!-- vaultchef:recipe:start -->\n\n"
IMAGE_MARKER_PREFIX = "<!-- vaultchef:image:"


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
    image_marker = _image_marker(meta, vault_root)
    if title:
        if image_marker:
            return f"## {title}\n\n{image_marker}\n\n{body}"
        return f"## {title}\n\n{body}"
    return body


def _split_frontmatter(md: str) -> tuple[dict[str, Any], str]:
    doc = split_frontmatter(md)
    return doc.frontmatter, doc.body


def _image_marker(meta: dict[str, Any], vault_root: str) -> str | None:
    image = meta.get("image")
    if isinstance(image, list):
        image = image[0] if image else None
    if image is None or isinstance(image, dict):
        return None

    text = str(image).strip()
    if not text:
        return None

    path = Path(text)
    if not path.is_absolute():
        path = Path(vault_root) / path
    return f"{IMAGE_MARKER_PREFIX}{path.as_posix()} -->"


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
