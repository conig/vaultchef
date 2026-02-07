from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
from typing import Sequence

from .errors import ConfigError


REQUIRED_TEX_PACKAGES = (
    "geometry",
    "hyperref",
    "xcolor",
)
OPTIONAL_TEX_PACKAGES = (
    "enumitem",
    "titlesec",
    "titling",
    "microtype",
    "fontspec",
    "fancyhdr",
)


@dataclass(frozen=True)
class TexCheckResult:
    missing_required: list[str]
    missing_optional: list[str]
    missing_binaries: list[str]
    checked_packages: bool


def check_tex_dependencies(pdf_engine: str | None = None) -> TexCheckResult:
    missing_binaries: list[str] = []
    checked_packages = True
    engine = pdf_engine or "lualatex"

    if not _has_binary("kpsewhich"):
        missing_binaries.append("kpsewhich")
        checked_packages = False
    if not _has_binary(engine):
        missing_binaries.append(engine)

    missing_required: list[str] = []
    missing_optional: list[str] = []
    if checked_packages:
        for name in REQUIRED_TEX_PACKAGES:
            if not _has_tex_package(name):
                missing_required.append(name)
        for name in OPTIONAL_TEX_PACKAGES:
            if not _has_tex_package(name):
                missing_optional.append(name)

    return TexCheckResult(
        missing_required=missing_required,
        missing_optional=missing_optional,
        missing_binaries=missing_binaries,
        checked_packages=checked_packages,
    )


def format_tex_report(result: TexCheckResult) -> list[str]:
    lines: list[str] = []
    if result.missing_binaries:
        lines.append(f"Missing TeX binaries: {', '.join(result.missing_binaries)}")
    if not result.checked_packages:
        lines.append("Package checks skipped (kpsewhich not available).")
        return lines
    if result.missing_required:
        lines.append(f"Missing required packages: {', '.join(result.missing_required)}")
    if result.missing_optional:
        lines.append(f"Missing optional packages: {', '.join(result.missing_optional)}")
    if not lines:
        lines.append("TeX dependencies OK.")
    return lines


def install_tex_packages(packages: Sequence[str]) -> None:
    if not packages:
        return
    if not _has_binary("tlmgr"):
        raise ConfigError("tlmgr not found; install TeX packages manually.")
    cmd = ["tlmgr", "install", *packages]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr
        stdout = exc.stdout
        raise ConfigError(f"tlmgr failed: {stderr or stdout}") from exc


def _has_binary(name: str) -> bool:
    return shutil.which(name) is not None


def _has_tex_package(name: str) -> bool:
    try:
        result = subprocess.run(
            ["kpsewhich", f"{name}.sty"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0 and bool(result.stdout.strip())
