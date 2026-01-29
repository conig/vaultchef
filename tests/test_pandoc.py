from __future__ import annotations

from pathlib import Path
import stat
import pytest

from vaultchef.config import resolve_config
from vaultchef.pandoc import run_pandoc
from vaultchef.errors import PandocError


def _write_script(tmp_path: Path, content: str) -> Path:
    script = tmp_path / "pandoc"
    script.write_text(content, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_run_pandoc_success_verbose(tmp_path: Path, temp_home: Path, capsys) -> None:
    script = _write_script(
        tmp_path,
        """#!/usr/bin/env python3
import sys
out = None
for i, arg in enumerate(sys.argv):
    if arg == '-o' and i + 1 < len(sys.argv):
        out = sys.argv[i + 1]
if out:
    with open(out, 'wb') as fh:
        fh.write(b'%PDF-1.4\\n')
""",
    )
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(tmp_path), "project": str(tmp_path), "pandoc_path": str(script)})
    run_pandoc(str(input_md), str(tmp_path / "out.pdf"), cfg, verbose=True)
    out = capsys.readouterr().out
    assert str(script) in out


def test_run_pandoc_missing(tmp_path: Path, temp_home: Path) -> None:
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(tmp_path), "project": str(tmp_path), "pandoc_path": str(tmp_path / 'nope')})
    with pytest.raises(PandocError):
        run_pandoc(str(input_md), str(tmp_path / "out.pdf"), cfg, verbose=False)


def test_run_pandoc_failure(tmp_path: Path, temp_home: Path) -> None:
    script = _write_script(
        tmp_path,
        """#!/usr/bin/env python3
import sys
sys.exit(1)
""",
    )
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(tmp_path), "project": str(tmp_path), "pandoc_path": str(script)})
    with pytest.raises(PandocError):
        run_pandoc(str(input_md), str(tmp_path / "out.pdf"), cfg, verbose=False)
