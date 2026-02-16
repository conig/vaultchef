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
    output_pdf: str,
    cfg: EffectiveConfig,
    verbose: bool,
    extra_metadata: dict[str, Any] | None = None,
    extra_resource_paths: list[str] | None = None,
) -> None:
    paths = resolve_project_paths(cfg)
    output_dir = Path(output_pdf).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    resource_paths = [str(paths.style_dir)]
    if extra_resource_paths:
        for path in extra_resource_paths:
            if path and path not in resource_paths:
                resource_paths.append(path)

    cmd: list[str] = [
        cfg.pandoc.pandoc_path,
        str(input_md),
        "-o",
        str(output_pdf),
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
    env = _pandoc_env(output_dir, str(paths.style_dir))
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


def _pandoc_env(output_dir: Path, style_dir: str) -> dict[str, str]:
    env = os.environ.copy()
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
