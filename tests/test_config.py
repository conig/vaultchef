from __future__ import annotations

from pathlib import Path
import pytest

from vaultchef.config import (
    load_global_config,
    load_profile,
    load_project_config,
    merge_config,
    resolve_config,
    config_to_toml,
)
from vaultchef.errors import ConfigError
from tests.utils import write_global_config, write_profile


def test_load_global_config_missing(temp_home: Path) -> None:
    assert load_global_config() == {}


def test_load_global_config_invalid(temp_home: Path) -> None:
    write_global_config(temp_home, "bad = ")
    with pytest.raises(ConfigError):
        load_global_config()


def test_load_global_config_permission_error(temp_home: Path) -> None:
    path = write_global_config(temp_home, "vault_path = '/vault'\n")
    path.chmod(0o000)
    try:
        with pytest.raises(ConfigError):
            load_global_config()
    finally:
        path.chmod(0o644)


def test_load_profile_missing_returns_none(temp_home: Path) -> None:
    assert load_profile("missing") is None


def test_profile_missing_project_key(temp_home: Path) -> None:
    profile_path = temp_home / ".config" / "vaultchef" / "projects.d" / "bad.toml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text("foo = 'bar'\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_profile("bad")


def test_project_config_missing(tmp_path: Path) -> None:
    assert load_project_config(str(tmp_path)) == {}


def test_merge_config() -> None:
    base = {"a": 1, "b": {"c": 1}}
    proj = {"b": {"c": 2}}
    cli = {"b": {"d": 3}}
    merged = merge_config(cli, proj, base)
    assert merged["b"]["c"] == 2
    assert merged["b"]["d"] == 3


def test_resolve_config_precedence(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(
        temp_home,
        """
vault_path = "/vault"
recipes_dir = "Recipes"
cookbooks_dir = "Cookbooks"
default_project = "/global_project"

[pandoc]
pdf_engine = "xelatex"
""",
    )

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "vaultchef.toml").write_text(
        """
build_dir = "out"
[pandoc]
style_dir = "templates"
""",
        encoding="utf-8",
    )

    cfg = resolve_config(
        {
            "vault_path": "/cli_vault",
            "project": str(project_dir),
            "pdf_engine": "lualatex",
            "theme": "minimal",
        }
    )
    assert cfg.vault_path == "/cli_vault"
    assert cfg.build_dir == "out"
    assert cfg.pandoc.pdf_engine == "lualatex"
    assert cfg.style.theme == "minimal"
    assert cfg.tex.check_on_startup is True


def test_resolve_config_profile(temp_home: Path, tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    write_global_config(temp_home, "vault_path = '/vault'\n")
    write_profile(temp_home, "gift", str(project_dir))
    cfg = resolve_config({"profile": "gift"})
    assert cfg.project_dir == str(project_dir)


def test_resolve_config_requires_vault(temp_home: Path) -> None:
    with pytest.raises(ConfigError):
        resolve_config({})


def test_config_to_toml(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(temp_home, "vault_path = '/vault'\ndefault_project = '/p'\n")
    cfg = resolve_config({"project": str(tmp_path)})
    text = config_to_toml(cfg)
    assert "vault_path" in text
    assert "[pandoc]" in text
    assert "default_project" in text
    assert "tex_check" in text


def test_resolve_config_tex_check_override(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(temp_home, "vault_path = '/vault'\ntex_check = false\n")
    cfg = resolve_config({"project": str(tmp_path)})
    assert cfg.tex.check_on_startup is False
