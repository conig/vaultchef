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


# Purpose: verify load global config missing.
def test_load_global_config_missing(temp_home: Path) -> None:
    assert load_global_config() == {}


# Purpose: verify load global config invalid.
def test_load_global_config_invalid(temp_home: Path) -> None:
    write_global_config(temp_home, "bad = ")
    with pytest.raises(ConfigError):
        load_global_config()


# Purpose: verify load global config permission error.
def test_load_global_config_permission_error(temp_home: Path) -> None:
    path = write_global_config(temp_home, "vault_path = '/vault'\n")
    path.chmod(0o000)
    try:
        with pytest.raises(ConfigError):
            load_global_config()
    finally:
        path.chmod(0o644)


# Purpose: verify load profile missing returns none.
def test_load_profile_missing_returns_none(temp_home: Path) -> None:
    assert load_profile("missing") is None


# Purpose: verify profile missing project key.
def test_profile_missing_project_key(temp_home: Path) -> None:
    profile_path = temp_home / ".config" / "vaultchef" / "projects.d" / "bad.toml"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text("foo = 'bar'\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_profile("bad")


# Purpose: verify project config missing.
def test_project_config_missing(tmp_path: Path) -> None:
    assert load_project_config(str(tmp_path)) == {}


# Purpose: verify merge config.
def test_merge_config() -> None:
    base = {"a": 1, "b": {"c": 1}}
    proj = {"b": {"c": 2}}
    cli = {"b": {"d": 3}}
    merged = merge_config(cli, proj, base)
    assert merged["b"]["c"] == 2
    assert merged["b"]["d"] == 3


# Purpose: verify resolve config precedence.
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
    assert cfg.tui.header_icon == "🔪"
    assert cfg.tui.layout == "auto"
    assert cfg.tui.density == "cozy"


# Purpose: verify resolve config profile.
def test_resolve_config_profile(temp_home: Path, tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    write_global_config(temp_home, "vault_path = '/vault'\n")
    write_profile(temp_home, "gift", str(project_dir))
    cfg = resolve_config({"profile": "gift"})
    assert cfg.project_dir == str(project_dir)


# Purpose: verify resolve config requires vault.
def test_resolve_config_requires_vault(temp_home: Path) -> None:
    with pytest.raises(ConfigError):
        resolve_config({})


# Purpose: verify config to toml.
def test_config_to_toml(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(temp_home, "vault_path = '/vault'\ndefault_project = '/p'\n")
    cfg = resolve_config({"project": str(tmp_path)})
    text = config_to_toml(cfg)
    assert "vault_path" in text
    assert "[pandoc]" in text
    assert "default_project" in text
    assert "tex_check" in text
    assert "tui_header_icon" in text
    assert "tui_layout" in text
    assert "tui_density" in text


# Purpose: verify resolve config tex check override.
def test_resolve_config_tex_check_override(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(temp_home, "vault_path = '/vault'\ntex_check = false\n")
    cfg = resolve_config({"project": str(tmp_path)})
    assert cfg.tex.check_on_startup is False


# Purpose: verify resolve config tui icon override.
def test_resolve_config_tui_icon_override(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(temp_home, "vault_path = '/vault'\ntui_header_icon = '🧁'\n")
    cfg = resolve_config({"project": str(tmp_path)})
    assert cfg.tui.header_icon == "🧁"


# Purpose: verify resolve config tui layout and density.
def test_resolve_config_tui_layout_density(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(
        temp_home,
        "vault_path = '/vault'\ntui_layout = 'WIDE'\ntui_density = 'compact'\n",
    )
    cfg = resolve_config({"project": str(tmp_path)})
    assert cfg.tui.layout == "wide"
    assert cfg.tui.density == "compact"


# Purpose: verify resolve config tui layout and density fallback.
def test_resolve_config_tui_layout_density_fallback(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(
        temp_home,
        "vault_path = '/vault'\ntui_layout = 'unknown'\ntui_density = 'dense'\n",
    )
    cfg = resolve_config({"project": str(tmp_path)})
    assert cfg.tui.layout == "auto"
    assert cfg.tui.density == "cozy"


# Purpose: verify resolve config tui cli precedence.
def test_resolve_config_tui_cli_precedence(temp_home: Path, tmp_path: Path) -> None:
    write_global_config(temp_home, "vault_path = '/vault'\ntui_layout = 'normal'\ntui_density = 'cozy'\n")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "vaultchef.toml").write_text(
        "tui_layout = 'wide'\ntui_density = 'compact'\n",
        encoding="utf-8",
    )
    cfg = resolve_config(
        {
            "project": str(project_dir),
            "tui_layout": "compact",
            "tui_density": "cozy",
        }
    )
    assert cfg.tui.layout == "compact"
    assert cfg.tui.density == "cozy"
