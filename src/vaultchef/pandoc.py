from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any

import yaml

from .config import EffectiveConfig
from .errors import PandocError
from .infra import run_process
from .paths import resolve_project_paths


def run_pandoc(
    input_md: str,
    output_path: str,
    cfg: EffectiveConfig,
    verbose: bool,
    output_format: str = "pdf",
    extra_metadata: dict[str, Any] | None = None,
    extra_resource_paths: list[str] | None = None,
) -> None:
    paths = resolve_project_paths(cfg)
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    resource_paths = [str(paths.style_dir)]
    if extra_resource_paths:
        for path in extra_resource_paths:
            if path and path not in resource_paths:
                resource_paths.append(path)

    cmd = _build_pandoc_command(
        input_md=input_md,
        output_path=output_path,
        cfg=cfg,
        output_format=output_format,
        resource_paths=resource_paths,
    )
    env = _pandoc_env(output_dir, str(paths.style_dir), output_format=output_format)
    metadata_file = _write_metadata_file(output_dir, extra_metadata)
    if metadata_file is not None:
        cmd.extend(["--metadata-file", str(metadata_file)])

    if verbose:
        print(" ".join(cmd))

    try:
        run_process(cmd, env=env, capture_output=not verbose)
    except FileNotFoundError as exc:
        raise PandocError("pandoc not found") from exc
    except Exception as exc:
        stderr = getattr(exc, "stderr", None)
        stdout = getattr(exc, "stdout", None)
        raise PandocError(f"pandoc failed: {stderr or stdout}") from exc
    finally:
        if metadata_file is not None:
            metadata_file.unlink(missing_ok=True)


def _build_pandoc_command(
    input_md: str,
    output_path: str,
    cfg: EffectiveConfig,
    output_format: str,
    resource_paths: list[str],
) -> list[str]:
    paths = resolve_project_paths(cfg)
    cmd: list[str] = [cfg.pandoc.pandoc_path, str(input_md), "-o", str(output_path)]

    if output_format == "pdf":
        cmd.extend(
            [
                "--pdf-engine",
                cfg.pandoc.pdf_engine,
                "--template",
                str(paths.template_path),
                "--lua-filter",
                str(paths.lua_filter_path),
                "--metadata",
                f"theme={cfg.style.theme}",
                "--resource-path",
                os.pathsep.join(resource_paths),
            ]
        )
        return cmd

    if output_format == "web":
        cmd.extend(
            [
                "--standalone",
                "--embed-resources",
                "--toc",
                "--toc-depth",
                "2",
                "--template",
                str(paths.web_template_path),
                "--lua-filter",
                str(paths.web_lua_filter_path),
                "--metadata",
                f"theme={cfg.style.theme}",
                "--resource-path",
                os.pathsep.join(resource_paths),
            ]
        )
        return cmd

    raise PandocError(f"Unsupported output format: {output_format}")


def _pandoc_env(output_dir: Path, style_dir: str, output_format: str) -> dict[str, str]:
    env = os.environ.copy()
    if output_format != "pdf":
        return env

    env.setdefault("TEXMFCACHE", str(output_dir))
    env.setdefault("TEXMFVAR", str(output_dir))

    texinputs = style_dir
    existing_texinputs = env.get("TEXINPUTS")
    if existing_texinputs:
        if texinputs not in existing_texinputs.split(os.pathsep):
            env["TEXINPUTS"] = texinputs + os.pathsep + existing_texinputs
    else:
        env["TEXINPUTS"] = texinputs + os.pathsep
    return env


def _write_metadata_file(output_dir: Path, metadata: dict[str, Any] | None) -> Path | None:
    if not metadata:
        return None
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".yaml",
        prefix="vaultchef-meta-",
        dir=output_dir,
        delete=False,
    ) as fh:
        yaml.safe_dump(metadata, fh, sort_keys=True, allow_unicode=False)
        return Path(fh.name)
