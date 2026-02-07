from __future__ import annotations

from pathlib import Path
import time
import pytest

from vaultchef.watch import watch_cookbook, _collect_watch_paths, _snapshot_mtimes, _changed
from vaultchef.config import resolve_config
from vaultchef.errors import MissingFileError, WatchError


def _write_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    cookbooks = vault / "Cookbooks"
    recipes.mkdir(parents=True)
    cookbooks.mkdir(parents=True)
    (recipes / "R1.md").write_text(
        "---\nrecipe_id: 1\ntitle: R1\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n",
        encoding="utf-8",
    )
    (cookbooks / "Book.md").write_text("# T\n![[Recipes/R1]]\n", encoding="utf-8")
    return vault


# Purpose: verify collect watch paths.
def test_collect_watch_paths(tmp_path: Path) -> None:
    vault = _write_vault(tmp_path)
    cookbook = vault / "Cookbooks" / "Book.md"
    paths = _collect_watch_paths(cookbook, vault)
    assert cookbook in paths


# Purpose: verify changed detection.
def test_changed_detection(tmp_path: Path) -> None:
    vault = _write_vault(tmp_path)
    cookbook = vault / "Cookbooks" / "Book.md"
    paths = _collect_watch_paths(cookbook, vault)
    mtimes = _snapshot_mtimes(paths)
    assert _changed(mtimes) is False
    time.sleep(0.01)
    cookbook.write_text("# T\n![[Recipes/R1]]\n\n", encoding="utf-8")
    assert _changed(mtimes) is True


# Purpose: verify changed detection missing path.
def test_changed_detection_missing_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.md"
    assert _changed({missing: 0.0}) is True


# Purpose: verify watch cookbook single cycle.
def test_watch_cookbook_single_cycle(tmp_path: Path, temp_home: Path) -> None:
    vault = _write_vault(tmp_path)
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path), "pandoc_path": "true"})
    watch_cookbook("Book", cfg, debounce_ms=1, verbose=False, max_cycles=1)


# Purpose: verify watch cookbook missing.
def test_watch_cookbook_missing(tmp_path: Path, temp_home: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path), "pandoc_path": "true"})
    with pytest.raises(MissingFileError):
        watch_cookbook("Missing", cfg, debounce_ms=1, verbose=False, max_cycles=1)


# Purpose: verify watch cookbook change triggers build.
def test_watch_cookbook_change_triggers_build(tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    vault = _write_vault(tmp_path)
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path), "pandoc_path": "true"})

    calls = []

    def fake_build(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr("vaultchef.watch.build_cookbook", fake_build)
    monkeypatch.setattr("vaultchef.watch._changed", lambda mtimes: True)
    watch_cookbook("Book", cfg, debounce_ms=1, verbose=False, max_cycles=1)
    assert calls


# Purpose: verify watch cookbook build error.
def test_watch_cookbook_build_error(tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    vault = _write_vault(tmp_path)
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path), "pandoc_path": "true"})

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("vaultchef.watch.build_cookbook", boom)
    monkeypatch.setattr("vaultchef.watch._changed", lambda mtimes: True)
    with pytest.raises(WatchError):
        watch_cookbook("Book", cfg, debounce_ms=1, verbose=False, max_cycles=1)
