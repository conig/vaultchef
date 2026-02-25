from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import os
from pathlib import Path
import re
import shutil
from typing import Any

import yaml

from ..config import EffectiveConfig
from ..domain import FRONTMATTER_RE
from ..errors import ConfigError, MissingFileError
from ..expand import EMBED_RE, expand_cookbook, resolve_embed_path
from ..pandoc import run_pandoc
from ..paths import resolve_project_paths, resolve_vault_paths
from ..shopping import build_shopping_list
from ..validate import validate_recipe


@dataclass(frozen=True)
class BuildResult:
    baked_md: Path
    output: Path
    output_format: str

    @property
    def pdf(self) -> Path:
        return self.output


def build_cookbook(
    cookbook_name: str,
    cfg: EffectiveConfig,
    dry_run: bool,
    verbose: bool,
    output_format: str = "pdf",
) -> BuildResult:
    if output_format not in {"pdf", "web"}:
        raise ConfigError(f"Unsupported output format: {output_format}")

    vault = resolve_vault_paths(cfg)
    project = resolve_project_paths(cfg)

    cookbook_path = vault.cookbooks_dir / f"{cookbook_name}.md"
    try:
        cookbook_text = cookbook_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MissingFileError(f"Cookbook not found: {cookbook_path}") from exc

    recipe_documents: list[tuple[str, str]] = []
    for match in EMBED_RE.finditer(cookbook_text):
        embed = match.group(1)
        recipe_path = resolve_embed_path(embed, str(vault.vault_root))
        recipe_text = recipe_path.read_text(encoding="utf-8")
        validate_recipe(recipe_text, str(recipe_path))
        recipe_documents.append((str(recipe_path), recipe_text))

    cookbook_meta = _parse_cookbook_meta(cookbook_text)
    if cookbook_meta.get("include_intro_page"):
        cookbook_meta["shopping_items"] = build_shopping_list(recipe_documents)
        cookbook_meta.setdefault("shopping_compact", True)
    baked = expand_cookbook(str(cookbook_path), str(vault.vault_root))

    project.build_dir.mkdir(parents=True, exist_ok=True)
    baked_path = project.build_dir / f"{cookbook_name}.baked.md"
    baked_path.write_text(baked, encoding="utf-8")

    extension = "pdf" if output_format == "pdf" else "html"
    output_path = project.build_dir / f"{cookbook_name}.{extension}"
    final_output_path = Path(os.getcwd()) / f"{cookbook_name}.{extension}"
    if not dry_run:
        extra_metadata = dict(cookbook_meta)
        if not extra_metadata.get("title"):
            extra_metadata["title"] = cookbook_name
        run_pandoc(
            str(baked_path),
            str(output_path),
            cfg,
            verbose,
            output_format=output_format,
            extra_metadata=extra_metadata or None,
            extra_resource_paths=[str(vault.vault_root)],
        )
        if output_path.resolve() != final_output_path.resolve():
            shutil.copy2(output_path, final_output_path)

    return BuildResult(baked_md=baked_path, output=final_output_path, output_format=output_format)


def _parse_cookbook_meta(text: str) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}

    meta: dict[str, Any] = {}
    for key in (
        "title",
        "subtitle",
        "date",
        "author",
        "album_title",
        "album_artist",
        "album_style",
        "album_youtube_url",
    ):
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            value = value.strftime("%A, %B %d, %Y").replace(" 0", " ")
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if item is not None)
        value_text = str(value).strip()
        if value_text:
            meta[key] = value_text

    subtitle = meta.get("subtitle")
    if isinstance(subtitle, str) and "·" in subtitle:
        left, right = (part.strip() for part in subtitle.split("·", 1))
        if (
            left
            and right
            and any(char.isdigit() for char in left)
            and any(char.isalpha() for char in left)
        ):
            meta["subtitle"] = right
            if not meta.get("date") or re.match(r"^\d{4}-\d{2}-\d{2}$", str(meta["date"])):
                meta["date"] = left

    if isinstance(meta.get("subtitle"), str) and meta["subtitle"]:
        meta["web_description"] = meta["subtitle"]
    if isinstance(meta.get("date"), str) and meta["date"]:
        meta["web_date"] = meta["date"]

    include_intro = _coerce_bool(data.get("include_intro_page"))
    if include_intro is None:
        include_intro = _coerce_bool(data.get("include_title_page"))
    if include_intro is not None:
        meta["include_intro_page"] = include_intro

    compact = _coerce_bool(data.get("shopping_compact"))
    if compact is not None:
        meta["shopping_compact"] = compact

    if any(
        meta.get(key)
        for key in (
            "album_title",
            "album_artist",
            "album_style",
            "album_youtube_url",
        )
    ):
        meta["has_music_pairing"] = True

    return meta


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if not isinstance(value, str):
        return None

    text = value.strip().lower()
    if text in {"true", "yes", "on", "1"}:
        return True
    if text in {"false", "no", "off", "0"}:
        return False
    return None
