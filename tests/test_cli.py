from __future__ import annotations

from pathlib import Path

import pytest

from vaultchef import cli
from vaultchef.errors import ConfigError, MissingFileError, ValidationError, PandocError, WatchError, VaultchefError
from tests.utils import write_global_config


def test_cli_no_command() -> None:
    assert cli.main([]) == 1


def test_cli_new_recipe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["new-recipe", "--id", "1", "--title", "Test"])
    assert rc == 0
    assert (tmp_path / "Test.md").exists()


def test_cli_new_recipe_file_exists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Test.md").write_text("x", encoding="utf-8")
    rc = cli.main(["new-recipe", "--id", "1", "--title", "Test"])
    assert rc == 1


def test_cli_new_cookbook(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["new-cookbook", "--title", "Book"])
    assert rc == 0
    assert (tmp_path / "Book.md").exists()


def test_cli_config_prints(temp_home: Path, tmp_path: Path, capsys) -> None:
    write_global_config(temp_home, "vault_path = '/vault'\n")
    rc = cli.main(["config", "--project", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "vault_path" in out


def test_cli_config_error(temp_home: Path) -> None:
    rc = cli.main(["config"])
    assert rc == 2


def test_cli_build_dry_run(example_vault: Path, tmp_path: Path, temp_home: Path) -> None:
    rc = cli.main(["build", "Family Cookbook", "--vault", str(example_vault), "--project", str(tmp_path), "--dry-run"])
    assert rc == 0


def test_cli_build_missing(example_vault: Path, tmp_path: Path, temp_home: Path) -> None:
    rc = cli.main(["build", "Missing", "--vault", str(example_vault), "--project", str(tmp_path), "--dry-run"])
    assert rc == 3


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


def test_cli_list_json(example_vault: Path, tmp_path: Path, temp_home: Path, capsys) -> None:
    rc = cli.main(["list", "--vault", str(example_vault), "--project", str(tmp_path), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip().startswith("[")


def test_cli_list_text(example_vault: Path, tmp_path: Path, temp_home: Path, capsys) -> None:
    rc = cli.main(["list", "--vault", str(example_vault), "--project", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Lemon Tart" in out


def test_cli_watch(monkeypatch) -> None:
    monkeypatch.setattr("vaultchef.cli.watch_cookbook", lambda *a, **k: None)
    rc = cli.main(["watch", "X", "--vault", "/v", "--project", "/p"])
    assert rc == 0


def test_cli_init(tmp_path: Path) -> None:
    rc = cli.main(["init", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "vaultchef.toml").exists()


def test_cli_init_existing(tmp_path: Path) -> None:
    (tmp_path / "vaultchef.toml").write_text("x", encoding="utf-8")
    rc = cli.main(["init", str(tmp_path)])
    assert rc == 2


def test_open_file_error(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr("vaultchef.cli.subprocess.run", boom)
    with pytest.raises(ConfigError):
        cli._open_file("x")


def test_exit_code_mapping() -> None:
    assert cli._exit_code(ConfigError("x")) == 2
    assert cli._exit_code(MissingFileError("x")) == 3
    assert cli._exit_code(ValidationError("x")) == 4
    assert cli._exit_code(PandocError("x")) == 5
    assert cli._exit_code(WatchError("x")) == 6
    assert cli._exit_code(VaultchefError("x")) == 1


def test_main_generic_exception(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise ValueError("oops")

    monkeypatch.setattr("vaultchef.cli._cmd_build", boom)
    rc = cli.main(["build", "X", "--vault", "/v", "--project", "/p"])
    assert rc == 1
