from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import EffectiveConfig
from .paths import resolve_vault_paths, resolve_project_paths
from .expand import expand_cookbook, EMBED_RE, resolve_embed_path
from .validate import validate_recipe
from .errors import MissingFileError
from .pandoc import run_pandoc


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

    baked = expand_cookbook(str(cookbook_path), str(vault.vault_root))

    project.build_dir.mkdir(parents=True, exist_ok=True)
    baked_path = project.build_dir / f"{cookbook_name}.baked.md"
    baked_path.write_text(baked, encoding="utf-8")

    pdf_path = project.build_dir / f"{cookbook_name}.pdf"
    if not dry_run:
        run_pandoc(str(baked_path), str(pdf_path), cfg, verbose)

    return BuildResult(baked_md=baked_path, pdf=pdf_path)
