from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib
from typing import Any, Optional

from .errors import ConfigError


@dataclass(frozen=True)
class PandocConfig:
    pdf_engine: str = "lualatex"
    template: str = "templates/cookbook.tex"
    lua_filter: str = "filters/recipe.lua"
    style_dir: str = "templates"
    pandoc_path: str = "pandoc"


@dataclass(frozen=True)
class StyleConfig:
    theme: str = "menu-card"


@dataclass(frozen=True)
class TexConfig:
    check_on_startup: bool = True


@dataclass(frozen=True)
class TuiConfig:
    header_icon: str = "🔪"
    layout: str = "auto"
    density: str = "cozy"
    mode_animation: str = "auto"


@dataclass(frozen=True)
class EffectiveConfig:
    vault_path: str
    recipes_dir: str
    cookbooks_dir: str
    default_project: Optional[str]
    build_dir: str
    cache_dir: str
    pandoc: PandocConfig
    style: StyleConfig
    tex: TexConfig
    tui: TuiConfig
    project_dir: str


def _config_root() -> Path:
    return Path(os.path.expanduser("~/.config/vaultchef"))


def load_global_config() -> dict[str, Any]:
    path = _config_root() / "config.toml"
    if not path.exists():
        return {}
    return _load_toml(path)


def load_profile(profile: str) -> Optional[str]:
    path = _config_root() / "projects.d" / f"{profile}.toml"
    if not path.exists():
        return None
    data = _load_toml(path)
    project = data.get("project")
    if not project:
        raise ConfigError(f"Profile {profile!r} missing 'project' key")
    return str(project)


def load_project_config(project_dir: str) -> dict[str, Any]:
    path = Path(project_dir) / "vaultchef.toml"
    if not path.exists():
        return {}
    return _load_toml(path)


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except OSError as exc:
        raise ConfigError(f"Failed to read config: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in config: {path}") from exc


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def merge_config(cli: dict[str, Any], project: dict[str, Any], global_cfg: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(global_cfg, project)
    return _deep_merge(merged, cli)


def resolve_config(cli_args: dict[str, Any]) -> EffectiveConfig:
    global_cfg = load_global_config()
    profile = cli_args.get("profile")
    project_dir = cli_args.get("project")
    if not project_dir and profile:
        project_dir = load_profile(profile)
    if not project_dir:
        project_dir = global_cfg.get("default_project") or os.getcwd()

    project_cfg = load_project_config(project_dir)

    cli_cfg = _cli_to_dict(cli_args)
    merged = merge_config(cli_cfg, project_cfg, global_cfg)

    vault_path = merged.get("vault_path")
    if not vault_path:
        raise ConfigError("vault_path is required (set in config or via --vault)")

    pandoc_cfg = merged.get("pandoc", {})
    style_cfg = merged.get("style", {})
    tex_check = merged.get("tex_check", True)
    tui_icon = merged.get("tui_header_icon", "🔪")
    tui_layout = _normalize_tui_layout(merged.get("tui_layout", "auto"))
    tui_density = _normalize_tui_density(merged.get("tui_density", "cozy"))
    tui_mode_animation = _normalize_tui_mode_animation(merged.get("tui_mode_animation", "auto"))

    return EffectiveConfig(
        vault_path=str(vault_path),
        recipes_dir=str(merged.get("recipes_dir", "Recipes")),
        cookbooks_dir=str(merged.get("cookbooks_dir", "Cookbooks")),
        default_project=merged.get("default_project"),
        build_dir=str(merged.get("build_dir", "build")),
        cache_dir=str(merged.get("cache_dir", "cache")),
        pandoc=PandocConfig(
            pdf_engine=str(pandoc_cfg.get("pdf_engine", "lualatex")),
            template=str(pandoc_cfg.get("template", "templates/cookbook.tex")),
            lua_filter=str(pandoc_cfg.get("lua_filter", "filters/recipe.lua")),
            style_dir=str(pandoc_cfg.get("style_dir", "templates")),
            pandoc_path=str(pandoc_cfg.get("pandoc_path", "pandoc")),
        ),
        style=StyleConfig(theme=str(style_cfg.get("theme", "menu-card"))),
        tex=TexConfig(check_on_startup=bool(tex_check)),
        tui=TuiConfig(
            header_icon=str(tui_icon),
            layout=tui_layout,
            density=tui_density,
            mode_animation=tui_mode_animation,
        ),
        project_dir=str(project_dir),
    )


def _cli_to_dict(cli_args: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in (
        "vault_path",
        "recipes_dir",
        "cookbooks_dir",
        "default_project",
        "build_dir",
        "cache_dir",
    ):
        if cli_args.get(key) is not None:
            out[key] = cli_args[key]

    pandoc: dict[str, Any] = {}
    for key in ("pdf_engine", "template", "lua_filter", "style_dir", "pandoc_path"):
        if cli_args.get(key) is not None:
            pandoc[key] = cli_args[key]
    if pandoc:
        out["pandoc"] = pandoc

    style: dict[str, Any] = {}
    if cli_args.get("theme") is not None:
        style["theme"] = cli_args["theme"]
    if style:
        out["style"] = style

    for key in ("tui_header_icon", "tui_layout", "tui_density", "tui_mode_animation"):
        if cli_args.get(key) is not None:
            out[key] = cli_args[key]

    return out


def config_to_toml(cfg: EffectiveConfig) -> str:
    lines = [
        f"vault_path = {cfg.vault_path!r}",
        f"recipes_dir = {cfg.recipes_dir!r}",
        f"cookbooks_dir = {cfg.cookbooks_dir!r}",
    ]
    if cfg.default_project:
        lines.append(f"default_project = {cfg.default_project!r}")
    lines.append(f"build_dir = {cfg.build_dir!r}")
    lines.append(f"cache_dir = {cfg.cache_dir!r}")
    lines.append(f"tex_check = {cfg.tex.check_on_startup!r}")
    lines.append(f"tui_header_icon = {cfg.tui.header_icon!r}")
    lines.append(f"tui_layout = {cfg.tui.layout!r}")
    lines.append(f"tui_density = {cfg.tui.density!r}")
    lines.append(f"tui_mode_animation = {cfg.tui.mode_animation!r}")
    lines.append("")
    lines.append("[pandoc]")
    lines.append(f"pdf_engine = {cfg.pandoc.pdf_engine!r}")
    lines.append(f"template = {cfg.pandoc.template!r}")
    lines.append(f"lua_filter = {cfg.pandoc.lua_filter!r}")
    lines.append(f"style_dir = {cfg.pandoc.style_dir!r}")
    lines.append(f"pandoc_path = {cfg.pandoc.pandoc_path!r}")
    lines.append("")
    lines.append("[style]")
    lines.append(f"theme = {cfg.style.theme!r}")
    return "\n".join(lines) + "\n"


def _normalize_tui_layout(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"auto", "compact", "normal", "wide"}:
        return text
    return "auto"


def _normalize_tui_density(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"cozy", "compact"}:
        return text
    return "cozy"


def _normalize_tui_mode_animation(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"auto", "on", "off"}:
        return text
    return "auto"
