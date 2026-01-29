from __future__ import annotations

from pathlib import Path


def write_global_config(home: Path, content: str) -> Path:
    cfg_dir = home / ".config" / "vaultchef"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    path = cfg_dir / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path


def write_profile(home: Path, name: str, project: str) -> Path:
    dir_path = home / ".config" / "vaultchef" / "projects.d"
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{name}.toml"
    path.write_text(f"project = {project!r}\n", encoding="utf-8")
    return path
