from __future__ import annotations

from pathlib import Path
import argparse
import types
import sys
import stat

import pytest

from vaultchef import cli
from vaultchef.tex import TexCheckResult
from vaultchef.config import EffectiveConfig, PandocConfig, StyleConfig, TexConfig, TuiConfig
from vaultchef.errors import ConfigError, MissingFileError, ValidationError, PandocError, WatchError, VaultchefError
from tests.utils import write_global_config


# Purpose: verify cli no command.
def test_cli_no_command() -> None:
    called = {}

    def fake_tui(*args, **kwargs):
        called["ok"] = True
        return 0

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cli, "_cmd_tui", fake_tui)
    try:
        assert cli.main([]) == 0
        assert called.get("ok") is True
    finally:
        monkeypatch.undo()


# Purpose: verify cli tui flag.
def test_cli_tui_flag(monkeypatch) -> None:
    monkeypatch.setattr("vaultchef.cli._cmd_tui", lambda *a, **k: 0)
    assert cli.main(["--tui"]) == 0


# Purpose: verify cmd tui invokes run.
def test_cmd_tui_invokes_run(monkeypatch) -> None:
    calls = {}

    def fake_run_tui(args: dict[str, object]) -> int:
        calls["args"] = args
        return 0

    cfg = EffectiveConfig(
        vault_path="/v",
        recipes_dir="Recipes",
        cookbooks_dir="Cookbooks",
        default_project=None,
        build_dir="build",
        cache_dir="cache",
        pandoc=PandocConfig(),
        style=StyleConfig(),
        tex=TexConfig(check_on_startup=False),
        tui=TuiConfig(header_icon="🍳"),
        project_dir="/p",
    )
    monkeypatch.setattr(cli, "resolve_config", lambda *a, **k: cfg)
    monkeypatch.setitem(sys.modules, "vaultchef.tui", types.SimpleNamespace(run_tui=fake_run_tui))
    rc = cli._cmd_tui(argparse.Namespace())
    assert rc == 0
    assert calls["args"] == {}


# Purpose: verify cmd tex check skips install.
def test_cmd_tex_check_skips_install(monkeypatch, capsys) -> None:
    result = TexCheckResult(
        missing_required=["geometry"],
        missing_optional=[],
        missing_binaries=[],
        checked_packages=True,
    )
    monkeypatch.setattr(cli, "check_tex_dependencies", lambda pdf_engine=None: result)
    monkeypatch.setattr(cli, "format_tex_report", lambda res: ["Missing required packages: geometry"])
    monkeypatch.setattr("builtins.input", lambda _: "n")
    called = {}
    monkeypatch.setattr(cli, "install_tex_packages", lambda pkgs: called.setdefault("pkgs", pkgs))
    rc = cli._cmd_tex_check(argparse.Namespace(pdf_engine=None))
    assert rc == 0
    assert "pkgs" not in called
    assert "Missing required packages" in capsys.readouterr().out


# Purpose: verify cmd tex check installs.
def test_cmd_tex_check_installs(monkeypatch) -> None:
    result = TexCheckResult(
        missing_required=["geometry"],
        missing_optional=["fancyhdr"],
        missing_binaries=[],
        checked_packages=True,
    )
    monkeypatch.setattr(cli, "check_tex_dependencies", lambda pdf_engine=None: result)
    monkeypatch.setattr(cli, "format_tex_report", lambda res: ["Missing required packages: geometry"])
    monkeypatch.setattr("builtins.input", lambda _: "y")
    called = {}
    monkeypatch.setattr(cli, "install_tex_packages", lambda pkgs: called.setdefault("pkgs", pkgs))
    rc = cli._cmd_tex_check(argparse.Namespace(pdf_engine=None))
    assert rc == 0
    assert called["pkgs"] == ["geometry", "fancyhdr"]


# Purpose: verify cli tex check command.
def test_cli_tex_check_command(monkeypatch) -> None:
    result = TexCheckResult(
        missing_required=[],
        missing_optional=[],
        missing_binaries=[],
        checked_packages=True,
    )
    monkeypatch.setattr(cli, "check_tex_dependencies", lambda pdf_engine=None: result)
    monkeypatch.setattr(cli, "format_tex_report", lambda res: ["TeX dependencies OK."])
    rc = cli.main(["tex-check"])
    assert rc == 0


# Purpose: verify warn tex disabled.
def test_warn_tex_disabled(monkeypatch, capsys) -> None:
    cfg = EffectiveConfig(
        vault_path="/v",
        recipes_dir="Recipes",
        cookbooks_dir="Cookbooks",
        default_project=None,
        build_dir="build",
        cache_dir="cache",
        pandoc=PandocConfig(),
        style=StyleConfig(),
        tex=TexConfig(check_on_startup=False),
        tui=TuiConfig(header_icon="🍳"),
        project_dir="/p",
    )
    monkeypatch.setattr(cli, "check_tex_dependencies", lambda pdf_engine=None: None)
    cli._maybe_warn_tex(cfg)
    assert capsys.readouterr().err == ""


# Purpose: verify warn tex prints.
def test_warn_tex_prints(monkeypatch, capsys) -> None:
    cfg = EffectiveConfig(
        vault_path="/v",
        recipes_dir="Recipes",
        cookbooks_dir="Cookbooks",
        default_project=None,
        build_dir="build",
        cache_dir="cache",
        pandoc=PandocConfig(),
        style=StyleConfig(),
        tex=TexConfig(check_on_startup=True),
        tui=TuiConfig(header_icon="🍳"),
        project_dir="/p",
    )
    result = TexCheckResult(
        missing_required=["geometry"],
        missing_optional=[],
        missing_binaries=[],
        checked_packages=True,
    )
    monkeypatch.setattr(cli, "check_tex_dependencies", lambda pdf_engine=None: result)
    monkeypatch.setattr(cli, "format_tex_report", lambda res: ["Missing required packages: geometry"])
    cli._maybe_warn_tex(cfg)
    err = capsys.readouterr().err
    assert "Missing required packages" in err
    assert "vaultchef tex-check" in err
    assert "tex_check = false" in err


# Purpose: verify cli new recipe.
def test_cli_new_recipe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["new-recipe", "--id", "1", "--title", "Test"])
    assert rc == 0
    assert (tmp_path / "Test.md").exists()


# Purpose: verify cli new recipe file exists.
def test_cli_new_recipe_file_exists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Test.md").write_text("x", encoding="utf-8")
    rc = cli.main(["new-recipe", "--id", "1", "--title", "Test"])
    assert rc == 1


# Purpose: verify cli new cookbook.
def test_cli_new_cookbook(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["new-cookbook", "--title", "Book"])
    assert rc == 0
    assert (tmp_path / "Book.md").exists()


# Purpose: verify cli config prints.
def test_cli_config_prints(temp_home: Path, tmp_path: Path, capsys) -> None:
    write_global_config(temp_home, "vault_path = '/vault'\n")
    rc = cli.main(["config", "--project", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "vault_path" in out


# Purpose: verify cli config error.
def test_cli_config_error(temp_home: Path) -> None:
    rc = cli.main(["config"])
    assert rc == 2


# Purpose: verify cli build dry run.
def test_cli_build_dry_run(example_vault: Path, tmp_path: Path, temp_home: Path) -> None:
    rc = cli.main(["build", "Family Cookbook", "--vault", str(example_vault), "--project", str(tmp_path), "--dry-run"])
    assert rc == 0


# Purpose: verify cli build creates pdf.
def test_cli_build_creates_pdf(example_vault: Path, tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    pandoc = tmp_path / "pandoc"
    pandoc.write_text(
        """#!/usr/bin/env python3
import sys
out = None
for i, arg in enumerate(sys.argv):
    if arg == '-o' and i + 1 < len(sys.argv):
        out = sys.argv[i + 1]
if out:
    with open(out, 'wb') as fh:
        fh.write(b'%PDF-1.4\\n%mock')
""",
        encoding="utf-8",
    )
    pandoc.chmod(pandoc.stat().st_mode | stat.S_IEXEC)
    rc = cli.main(
        [
            "build",
            "Family Cookbook",
            "--vault",
            str(example_vault),
            "--project",
            str(tmp_path),
            "--pandoc",
            str(pandoc),
        ]
    )
    assert rc == 0
    assert (tmp_path / "build" / "Family Cookbook.pdf").exists()
    assert (cwd / "Family Cookbook.pdf").exists()


# Purpose: verify cli build missing.
def test_cli_build_missing(example_vault: Path, tmp_path: Path, temp_home: Path) -> None:
    rc = cli.main(["build", "Missing", "--vault", str(example_vault), "--project", str(tmp_path), "--dry-run"])
    assert rc == 3


# Purpose: verify cli build open.
def test_cli_build_open(monkeypatch) -> None:
    class Dummy:
        pdf = "out.pdf"

    monkeypatch.setattr("vaultchef.cli.build_cookbook", lambda *a, **k: Dummy())
    opened = {}

    def fake_open(path: str) -> None:
        opened["path"] = path

    monkeypatch.setattr("vaultchef.cli._open_file", fake_open)
    rc = cli.main(["build", "X", "--vault", "/v", "--project", "/p", "--open"])
    assert rc == 0
    assert opened["path"] == "out.pdf"


# Purpose: verify cli list json.
def test_cli_list_json(example_vault: Path, tmp_path: Path, temp_home: Path, capsys) -> None:
    rc = cli.main(["list", "--vault", str(example_vault), "--project", str(tmp_path), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip().startswith("[")


# Purpose: verify cli list text.
def test_cli_list_text(example_vault: Path, tmp_path: Path, temp_home: Path, capsys) -> None:
    rc = cli.main(["list", "--vault", str(example_vault), "--project", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Lemon Tart" in out


# Purpose: verify cli watch.
def test_cli_watch(monkeypatch) -> None:
    monkeypatch.setattr("vaultchef.cli.watch_cookbook", lambda *a, **k: None)
    rc = cli.main(["watch", "X", "--vault", "/v", "--project", "/p"])
    assert rc == 0


# Purpose: verify cli init.
def test_cli_init(tmp_path: Path) -> None:
    rc = cli.main(["init", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "vaultchef.toml").exists()


# Purpose: verify cli init existing.
def test_cli_init_existing(tmp_path: Path) -> None:
    (tmp_path / "vaultchef.toml").write_text("x", encoding="utf-8")
    rc = cli.main(["init", str(tmp_path)])
    assert rc == 2


# Purpose: verify open file error.
def test_open_file_error(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr("vaultchef.cli.subprocess.run", boom)
    with pytest.raises(ConfigError):
        cli._open_file("x")


# Purpose: verify exit code mapping.
def test_exit_code_mapping() -> None:
    assert cli._exit_code(ConfigError("x")) == 2
    assert cli._exit_code(MissingFileError("x")) == 3
    assert cli._exit_code(ValidationError("x")) == 4
    assert cli._exit_code(PandocError("x")) == 5
    assert cli._exit_code(WatchError("x")) == 6
    assert cli._exit_code(VaultchefError("x")) == 1


# Purpose: verify main generic exception.
def test_main_generic_exception(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise ValueError("oops")

    monkeypatch.setattr("vaultchef.cli._cmd_build", boom)
    rc = cli.main(["build", "X", "--vault", "/v", "--project", "/p"])
    assert rc == 1
