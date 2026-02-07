from __future__ import annotations

import time
from pathlib import Path

from .build import build_cookbook
from .config import EffectiveConfig
from .errors import MissingFileError, WatchError
from .expand import EMBED_RE, resolve_embed_path
from .paths import resolve_vault_paths


def watch_cookbook(
    cookbook_name: str,
    cfg: EffectiveConfig,
    debounce_ms: int,
    verbose: bool,
    max_cycles: int | None = None,
) -> None:
    vault = resolve_vault_paths(cfg)
    cookbook_path = vault.cookbooks_dir / f"{cookbook_name}.md"
    if not cookbook_path.exists():
        raise MissingFileError(f"Cookbook not found: {cookbook_path}")

    watched = _collect_watch_paths(cookbook_path, vault.vault_root)
    mtimes = _snapshot_mtimes(watched)
    cycles = 0

    while True:
        time.sleep(debounce_ms / 1000.0)
        if _changed(mtimes):
            try:
                build_cookbook(cookbook_name, cfg, dry_run=False, verbose=verbose)
            except Exception as exc:  # pragma: no cover - defensive
                raise WatchError(str(exc)) from exc
            watched = _collect_watch_paths(cookbook_path, vault.vault_root)
            mtimes = _snapshot_mtimes(watched)

        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            break


def _collect_watch_paths(cookbook_path: Path, vault_root: Path) -> list[Path]:
    text = cookbook_path.read_text(encoding="utf-8")
    paths = {cookbook_path}
    for match in EMBED_RE.finditer(text):
        embed = match.group(1)
        paths.add(resolve_embed_path(embed, str(vault_root)))
    return sorted(paths)


def _snapshot_mtimes(paths: list[Path]) -> dict[Path, float]:
    mtimes: dict[Path, float] = {}
    for path in paths:
        mtimes[path] = path.stat().st_mtime
    return mtimes


def _changed(mtimes: dict[Path, float]) -> bool:
    for path, old in mtimes.items():
        if not path.exists():
            return True
        if path.stat().st_mtime != old:
            return True
    return False
