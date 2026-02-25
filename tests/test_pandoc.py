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


# Purpose: verify run pandoc web format arguments.
def test_run_pandoc_web_format_args(tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    script = _write_script(
        tmp_path,
        """#!/usr/bin/env python3
import os
import sys
out = None
for i, arg in enumerate(sys.argv):
    if arg == '-o' and i + 1 < len(sys.argv):
        out = sys.argv[i + 1]
args_out = os.environ.get("PANDOC_ARGS_OUT")
if args_out:
    with open(args_out, "w", encoding="utf-8") as fh:
        fh.write("\\n".join(sys.argv))
if out:
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('<!doctype html>')
""",
    )
    args_out = tmp_path / "args.txt"
    monkeypatch.setenv("PANDOC_ARGS_OUT", str(args_out))
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(tmp_path), "project": str(tmp_path), "pandoc_path": str(script)})
    output_html = tmp_path / "out.html"
    run_pandoc(str(input_md), str(output_html), cfg, verbose=False, output_format="web")
    args = args_out.read_text(encoding="utf-8").splitlines()
    assert "--standalone" in args
    assert "--embed-resources" in args
    assert "--toc" in args
    assert "--pdf-engine" not in args
    assert any(arg.endswith("cookbook.html") for arg in args)
    assert any(arg.endswith("web.lua") for arg in args)
    assert output_html.exists()


# Purpose: verify run pandoc writes structured metadata file.
def test_run_pandoc_metadata_file(tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    script = _write_script(
        tmp_path,
        """#!/usr/bin/env python3
import os
import sys

out = None
for i, arg in enumerate(sys.argv):
    if arg == '-o' and i + 1 < len(sys.argv):
        out = sys.argv[i + 1]

args_out = os.environ.get("PANDOC_ARGS_OUT")
if args_out:
    with open(args_out, "w", encoding="utf-8") as fh:
        fh.write("\\n".join(sys.argv))

meta_out = os.environ.get("PANDOC_META_OUT")
if meta_out:
    for i, arg in enumerate(sys.argv):
        if arg == '--metadata-file' and i + 1 < len(sys.argv):
            with open(sys.argv[i + 1], "r", encoding="utf-8") as src:
                data = src.read()
            with open(meta_out, "w", encoding="utf-8") as dst:
                dst.write(data)

if out:
    with open(out, 'wb') as fh:
        fh.write(b'%PDF-1.4\\n')
""",
    )
    args_out = tmp_path / "args.txt"
    meta_out = tmp_path / "meta.txt"
    monkeypatch.setenv("PANDOC_ARGS_OUT", str(args_out))
    monkeypatch.setenv("PANDOC_META_OUT", str(meta_out))
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(tmp_path), "project": str(tmp_path), "pandoc_path": str(script)})
    run_pandoc(
        str(input_md),
        str(tmp_path / "out.pdf"),
        cfg,
        verbose=False,
        extra_metadata={
            "include_intro_page": True,
            "shopping_items": ["2 tbsp olive oil"],
            "album_youtube_url": "https://music.youtube.com/watch?v=abc123",
        },
    )

    args = args_out.read_text(encoding="utf-8").splitlines()
    assert "--metadata-file" in args
    meta_text = meta_out.read_text(encoding="utf-8")
    assert "include_intro_page: true" in meta_text
    assert "album_youtube_url: https://music.youtube.com/watch?v=abc123" in meta_text
    assert "- 2 tbsp olive oil" in meta_text


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


# Purpose: verify run pandoc rejects unsupported format.
def test_run_pandoc_rejects_unsupported_format(tmp_path: Path, temp_home: Path) -> None:
    input_md = tmp_path / "in.md"
    input_md.write_text("# Hi\n", encoding="utf-8")
    cfg = resolve_config({"vault_path": str(tmp_path), "project": str(tmp_path), "pandoc_path": "pandoc"})
    with pytest.raises(PandocError):
        run_pandoc(str(input_md), str(tmp_path / "out.bin"), cfg, verbose=False, output_format="epub")
