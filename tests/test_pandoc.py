from __future__ import annotations

from pathlib import Path
import os
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


# Purpose: verify run pandoc success verbose.
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
    output_pdf = tmp_path / "out.pdf"
    run_pandoc(str(input_md), str(output_pdf), cfg, verbose=True)
    out = capsys.readouterr().out
    assert str(script) in out
    assert output_pdf.exists()
    assert output_pdf.read_bytes().startswith(b"%PDF-1.4")


# Purpose: verify run pandoc texinputs prepends.
def test_run_pandoc_texinputs_prepends(tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    script = _write_script(
        tmp_path,
        """#!/usr/bin/env python3
import os
import sys
out = None
for i, arg in enumerate(sys.argv):
    if arg == '-o' and i + 1 < len(sys.argv):
        out = sys.argv[i + 1]
env_out = os.environ.get("PANDOC_ENV_OUT")
if env_out:
    with open(env_out, "w", encoding="utf-8") as fh:
        fh.write(os.environ.get("TEXINPUTS", ""))
if out:
    with open(out, 'wb') as fh:
        fh.write(b'%PDF-1.4\\n')
""",
    )
    templates = tmp_path / "templates"
    templates.mkdir()
    env_out = tmp_path / "env.txt"
    monkeypatch.setenv("TEXINPUTS", "existing")
    monkeypatch.setenv("PANDOC_ENV_OUT", str(env_out))
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config(
        {
            "vault_path": str(tmp_path),
            "project": str(tmp_path),
            "pandoc_path": str(script),
        }
    )
    run_pandoc(str(input_md), str(tmp_path / "out.pdf"), cfg, verbose=False)
    texinputs = env_out.read_text(encoding="utf-8")
    assert texinputs.startswith(str(templates) + os.pathsep)


# Purpose: verify run pandoc resource paths.
def test_run_pandoc_resource_paths(tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    script = _write_script(
        tmp_path,
        """#!/usr/bin/env python3
import os
import sys
out = None
for i, arg in enumerate(sys.argv):
    if arg == '-o' and i + 1 < len(sys.argv):
        out = sys.argv[i + 1]
paths = ""
for i, arg in enumerate(sys.argv):
    if arg == '--resource-path' and i + 1 < len(sys.argv):
        paths = sys.argv[i + 1]
env_out = os.environ.get("PANDOC_PATHS_OUT")
if env_out:
    with open(env_out, "w", encoding="utf-8") as fh:
        fh.write(paths)
if out:
    with open(out, 'wb') as fh:
        fh.write(b'%PDF-1.4\\n')
""",
    )
    env_out = tmp_path / "paths.txt"
    monkeypatch.setenv("PANDOC_PATHS_OUT", str(env_out))
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(tmp_path), "project": str(tmp_path), "pandoc_path": str(script)})
    extra = tmp_path / "extra"
    extra.mkdir()
    run_pandoc(
        str(input_md),
        str(tmp_path / "out.pdf"),
        cfg,
        verbose=False,
        extra_resource_paths=[str(extra)],
    )
    paths = env_out.read_text(encoding="utf-8")
    assert str(extra) in paths


# Purpose: verify run pandoc missing.
def test_run_pandoc_missing(tmp_path: Path, temp_home: Path) -> None:
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(tmp_path), "project": str(tmp_path), "pandoc_path": str(tmp_path / 'nope')})
    with pytest.raises(PandocError):
        run_pandoc(str(input_md), str(tmp_path / "out.pdf"), cfg, verbose=False)


# Purpose: verify run pandoc failure.
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
