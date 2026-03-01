from __future__ import annotations

import io
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


# Purpose: verify cli tui mode animation flag.
def test_cli_tui_mode_animation_flag(monkeypatch) -> None:
    monkeypatch.setattr("vaultchef.cli._cmd_tui", lambda *a, **k: 0)
    assert cli.main(["--tui", "--tui-mode-animation", "off"]) == 0


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
        output = "out.pdf"

    monkeypatch.setattr("vaultchef.cli.build_cookbook", lambda *a, **k: Dummy())
    opened = {}

    def fake_open(path: str) -> None:
        opened["path"] = path

    monkeypatch.setattr("vaultchef.cli._open_file", fake_open)
    rc = cli.main(["build", "X", "--vault", "/v", "--project", "/p", "--open"])
    assert rc == 0
    assert opened["path"] == "out.pdf"


# Purpose: verify cli build open web targets index html.
def test_cli_build_open_web(monkeypatch) -> None:
    class Dummy:
        output = Path("/tmp/vaultchef-web")

    monkeypatch.setattr("vaultchef.cli.build_cookbook", lambda *a, **k: Dummy())
    opened = {}

    def fake_open(path: str) -> None:
        opened["path"] = path

    monkeypatch.setattr("vaultchef.cli._open_file", fake_open)
    rc = cli.main(["build", "X", "--vault", "/v", "--project", "/p", "--open", "--format", "web"])
    assert rc == 0
    assert opened["path"] == "/tmp/vaultchef-web/index.html"


# Purpose: verify cli build web format creates library app bundle.
def test_cli_build_web_creates_bundle(example_vault: Path, tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    rc = cli.main(
        [
            "build",
            "Family Cookbook",
            "--vault",
            str(example_vault),
            "--project",
            str(tmp_path),
            "--format",
            "web",
        ]
    )
    assert rc == 0
    assert (tmp_path / "build" / "vaultchef-web" / "index.html").exists()
    assert (cwd / "vaultchef-web" / "index.html").exists()
    assert (cwd / "vaultchef-web" / "content" / "index.json").exists()


# Purpose: verify cli build app format creates library app bundle without cookbook name.
def test_cli_build_app_creates_bundle(example_vault: Path, tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    rc = cli.main(
        [
            "build",
            "--vault",
            str(example_vault),
            "--project",
            str(tmp_path),
            "--format",
            "app",
        ]
    )
    assert rc == 0
    assert (tmp_path / "build" / "vaultchef-web" / "index.html").exists()
    assert (cwd / "vaultchef-web" / "index.html").exists()
    assert (cwd / "vaultchef-web" / "content" / "index.json").exists()


# Purpose: verify cli build supports --format --app shorthand.
def test_cli_build_format_flag_then_app(example_vault: Path, tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    rc = cli.main(
        [
            "build",
            "--vault",
            str(example_vault),
            "--project",
            str(tmp_path),
            "--format",
            "--app",
        ]
    )
    assert rc == 0
    assert (cwd / "vaultchef-web" / "index.html").exists()


# Purpose: verify cli build requires cookbook name for pdf format.
def test_cli_build_pdf_requires_cookbook_name(example_vault: Path, tmp_path: Path, temp_home: Path) -> None:
    rc = cli.main(["build", "--vault", str(example_vault), "--project", str(tmp_path)])
    assert rc == 2


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


# Purpose: verify cli serve command routing.
def test_cli_serve(monkeypatch) -> None:
    monkeypatch.setattr("vaultchef.cli._cmd_serve", lambda *a, **k: 0)
    rc = cli.main(["serve", "--vault", "/v", "--project", "/p"])
    assert rc == 0


# Purpose: verify cmd serve builds app and writes request log path.
def test_cmd_serve_builds_and_logs(tmp_path: Path, monkeypatch, capsys) -> None:
    app_dir = tmp_path / "vaultchef-web"
    app_dir.mkdir()
    (app_dir / "index.html").write_text("<!doctype html>", encoding="utf-8")
    log_file = tmp_path / "serve.log"

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
    monkeypatch.setattr(cli, "_resolve_cfg", lambda _args: cfg)

    class Dummy:
        output = app_dir

    monkeypatch.setattr(cli, "build_cookbook", lambda *a, **k: Dummy())
    captured = {}

    class FakeBaseHandler:
        def __init__(self, *args, directory=None, **kwargs):
            captured["directory"] = directory

        def address_string(self):
            return "127.0.0.1"

        def log_date_time_string(self):
            return "DATE"

    monkeypatch.setattr(cli, "SimpleHTTPRequestHandler", FakeBaseHandler)

    called = {}

    class FakeServer:
        def __init__(self, addr, handler):
            called["addr"] = addr
            called["handler"] = handler

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def serve_forever(self):
            handler = called["handler"]()
            handler.log_message("%s", "GET / HTTP/1.1")
            raise KeyboardInterrupt

    monkeypatch.setattr(cli, "ThreadingHTTPServer", FakeServer)

    args = argparse.Namespace(
        no_build=False,
        serve_dir=None,
        log_file=str(log_file),
        verbose=False,
        host="127.0.0.1",
        port=8000,
    )
    rc = cli._cmd_serve(args)
    assert rc == 0
    assert called["addr"] == ("127.0.0.1", 8000)
    assert captured["directory"] == str(app_dir.resolve())
    assert log_file.exists()
    assert "GET / HTTP/1.1" in log_file.read_text(encoding="utf-8")
    output = capsys.readouterr().out
    assert "Serving" in output
    assert "Request log:" in output


# Purpose: verify cmd serve no-build missing directory error.
def test_cmd_serve_no_build_missing_dir(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setattr(cli, "_resolve_cfg", lambda _args: cfg)

    args = argparse.Namespace(
        no_build=True,
        serve_dir=str(tmp_path / "nope"),
        log_file=str(tmp_path / "serve.log"),
        verbose=False,
        host="127.0.0.1",
        port=8000,
    )
    with pytest.raises(MissingFileError):
        cli._cmd_serve(args)


# Purpose: verify cmd serve errors when index.html is missing.
def test_cmd_serve_missing_entrypoint(tmp_path: Path, monkeypatch) -> None:
    app_dir = tmp_path / "vaultchef-web"
    app_dir.mkdir()
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
    monkeypatch.setattr(cli, "_resolve_cfg", lambda _args: cfg)
    args = argparse.Namespace(
        no_build=True,
        serve_dir=str(app_dir),
        log_file=str(tmp_path / "serve.log"),
        verbose=False,
        host="127.0.0.1",
        port=8000,
    )
    with pytest.raises(MissingFileError):
        cli._cmd_serve(args)


# Purpose: verify write serve log helper supports verbose stream output.
def test_write_serve_log_verbose(capsys) -> None:
    fh = io.StringIO()
    cli._write_serve_log(fh, "line\\n", verbose=True)
    assert fh.getvalue() == "line\\n"
    assert "line" in capsys.readouterr().out


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
