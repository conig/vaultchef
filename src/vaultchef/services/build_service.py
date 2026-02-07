from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

import yaml

from ..config import EffectiveConfig
from ..domain import FRONTMATTER_RE
from ..errors import MissingFileError
from ..expand import EMBED_RE, expand_cookbook, resolve_embed_path
from ..pandoc import run_pandoc
from ..paths import resolve_project_paths, resolve_vault_paths
from ..validate import validate_recipe


@dataclass(frozen=True)
class BuildResult:
    baked_md: Path
    pdf: Path


def build_cookbook(cookbook_name: str, cfg: EffectiveConfig, dry_run: bool, verbose: bool) -> BuildResult:
    vault = resolve_vault_paths(cfg)
    project = resolve_project_paths(cfg)

    cookbook_path = vault.cookbooks_dir / f"{cookbook_name}.md"
    try:
        cookbook_text = cookbook_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MissingFileError(f"Cookbook not found: {cookbook_path}") from exc

    for match in EMBED_RE.finditer(cookbook_text):
        embed = match.group(1)
        recipe_path = resolve_embed_path(embed, str(vault.vault_root))
        recipe_text = recipe_path.read_text(encoding="utf-8")
        validate_recipe(recipe_text, str(recipe_path))

    cookbook_meta = _parse_cookbook_meta(cookbook_text)
    baked = expand_cookbook(str(cookbook_path), str(vault.vault_root))

    project.build_dir.mkdir(parents=True, exist_ok=True)
    baked_path = project.build_dir / f"{cookbook_name}.baked.md"
    baked_path.write_text(baked, encoding="utf-8")

    pdf_path = project.build_dir / f"{cookbook_name}.pdf"
    final_pdf_path = Path(os.getcwd()) / f"{cookbook_name}.pdf"
    if not dry_run:
        extra_metadata = dict(cookbook_meta)
        if not extra_metadata.get("title"):
            extra_metadata["title"] = cookbook_name
        run_pandoc(
            str(baked_path),
            str(pdf_path),
            cfg,
            verbose,
            extra_metadata=extra_metadata or None,
            extra_resource_paths=[str(vault.vault_root)],
        )
        if pdf_path.resolve() != final_pdf_path.resolve():
            shutil.copy2(pdf_path, final_pdf_path)

    return BuildResult(baked_md=baked_path, pdf=final_pdf_path)


def _parse_cookbook_meta(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}

    meta: dict[str, str] = {}
    for key in ("title", "subtitle", "author"):
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value if item is not None)
        value_text = str(value).strip()
        if value_text:
            meta[key] = value_text
    return meta
