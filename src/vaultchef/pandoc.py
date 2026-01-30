from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .config import EffectiveConfig
from .paths import resolve_project_paths
from .errors import PandocError


def run_pandoc(
    input_md: str,
    output_pdf: str,
    cfg: EffectiveConfig,
    verbose: bool,
    extra_metadata: dict[str, str] | None = None,
) -> None:
    paths = resolve_project_paths(cfg)
    output_dir = Path(output_pdf).parent
    texmf_cache = output_dir
    texmf_var = output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
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
        str(paths.style_dir),
    ]
    if extra_metadata:
        for key, value in extra_metadata.items():
            cmd.extend(["--metadata", f"{key}={value}"])
    if verbose:
        print(" ".join(cmd))
    env = os.environ.copy()
    env.setdefault("TEXMFCACHE", str(texmf_cache))
    env.setdefault("TEXMFVAR", str(texmf_var))
    texinputs = str(paths.style_dir)
    existing_texinputs = env.get("TEXINPUTS")
    if existing_texinputs:
        if texinputs not in existing_texinputs.split(os.pathsep):
            env["TEXINPUTS"] = texinputs + os.pathsep + existing_texinputs
    else:
        env["TEXINPUTS"] = texinputs + os.pathsep
    try:
        subprocess.run(cmd, check=True, capture_output=not verbose, text=True, env=env)
    except FileNotFoundError as exc:
        raise PandocError("pandoc not found") from exc
    except subprocess.CalledProcessError as exc:
        raise PandocError(f"pandoc failed: {exc.stderr or exc.stdout}") from exc
