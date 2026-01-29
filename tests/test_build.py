from __future__ import annotations

from pathlib import Path
import os
import stat
import pytest

from vaultchef.build import build_cookbook
from vaultchef.config import resolve_config
from vaultchef.errors import MissingFileError


def _write_mock_pandoc(tmp_path: Path) -> Path:
    script = tmp_path / "pandoc"
    script.write_text(
        """#!/usr/bin/env python3
import sys

args = sys.argv
out = None
for i, arg in enumerate(args):
    if arg == '-o' and i + 1 < len(args):
        out = args[i + 1]

if out:
    with open(out, 'wb') as fh:
        fh.write(b'%PDF-1.4\\n%mock')
""",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_build_dry_run(tmp_path: Path, example_vault: Path, temp_home: Path) -> None:
    cfg = resolve_config({"vault_path": str(example_vault), "project": str(tmp_path)})
    result = build_cookbook("Family Cookbook", cfg, dry_run=True, verbose=False)
    assert result.baked_md.exists()
    assert not result.pdf.exists()


def test_build_runs_pandoc(tmp_path: Path, example_vault: Path, temp_home: Path) -> None:
    pandoc = _write_mock_pandoc(tmp_path)
    cfg = resolve_config(
        {
            "vault_path": str(example_vault),
            "project": str(tmp_path),
            "pandoc_path": str(pandoc),
        }
    )
    result = build_cookbook("Family Cookbook", cfg, dry_run=False, verbose=False)
    assert result.pdf.exists()


def test_build_missing_cookbook(tmp_path: Path, example_vault: Path, temp_home: Path) -> None:
    cfg = resolve_config({"vault_path": str(example_vault), "project": str(tmp_path)})
    with pytest.raises(MissingFileError):
        build_cookbook("Does Not Exist", cfg, dry_run=True, verbose=False)
