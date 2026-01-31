from __future__ import annotations

import subprocess

import pytest

from vaultchef import tex
from vaultchef.errors import ConfigError
from vaultchef.tex import check_tex_dependencies, format_tex_report, install_tex_packages


def test_check_tex_dependencies_all_present(monkeypatch) -> None:
    monkeypatch.setattr(tex, "_has_binary", lambda name: True)
    monkeypatch.setattr(tex, "_has_tex_package", lambda name: True)
    result = check_tex_dependencies("lualatex")
    assert result.checked_packages is True
    assert result.missing_binaries == []
    assert result.missing_required == []
    assert result.missing_optional == []
    assert format_tex_report(result) == ["TeX dependencies OK."]


def test_check_tex_dependencies_missing_kpsewhich(monkeypatch) -> None:
    def has_binary(name: str) -> bool:
        return False if name == "kpsewhich" else True

    monkeypatch.setattr(tex, "_has_binary", has_binary)
    monkeypatch.setattr(tex, "_has_tex_package", lambda name: True)
    result = check_tex_dependencies("lualatex")
    assert result.checked_packages is False
    assert "kpsewhich" in result.missing_binaries
    lines = format_tex_report(result)
    assert "Package checks skipped" in lines[-1]


def test_check_tex_dependencies_missing_packages(monkeypatch) -> None:
    monkeypatch.setattr(tex, "_has_binary", lambda name: True)

    def has_pkg(name: str) -> bool:
        return name not in ("geometry", "fancyhdr")

    monkeypatch.setattr(tex, "_has_tex_package", has_pkg)
    result = check_tex_dependencies("lualatex")
    assert "geometry" in result.missing_required
    assert "fancyhdr" in result.missing_optional


def test_check_tex_dependencies_missing_engine(monkeypatch) -> None:
    def has_binary(name: str) -> bool:
        return name != "xelatex"

    monkeypatch.setattr(tex, "_has_binary", has_binary)
    monkeypatch.setattr(tex, "_has_tex_package", lambda name: True)
    result = check_tex_dependencies("xelatex")
    assert "xelatex" in result.missing_binaries


def test_format_tex_report_missing_packages() -> None:
    result = tex.TexCheckResult(
        missing_required=["geometry"],
        missing_optional=["fancyhdr"],
        missing_binaries=[],
        checked_packages=True,
    )
    lines = format_tex_report(result)
    assert "Missing required packages" in lines[0]
    assert "Missing optional packages" in lines[1]


def test_install_tex_packages_missing_tlmgr(monkeypatch) -> None:
    monkeypatch.setattr(tex, "_has_binary", lambda name: False)
    with pytest.raises(ConfigError):
        install_tex_packages(["geometry"])


def test_install_tex_packages_noop() -> None:
    install_tex_packages([])


def test_install_tex_packages_runs(monkeypatch) -> None:
    monkeypatch.setattr(tex, "_has_binary", lambda name: True)
    called = {}

    def fake_run(cmd, check, capture_output, text):
        called["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(tex.subprocess, "run", fake_run)
    install_tex_packages(["geometry", "xcolor"])
    assert called["cmd"] == ["tlmgr", "install", "geometry", "xcolor"]


def test_install_tex_packages_failure(monkeypatch) -> None:
    monkeypatch.setattr(tex, "_has_binary", lambda name: True)

    def fake_run(cmd, check, capture_output, text):
        raise subprocess.CalledProcessError(1, cmd, output="oops", stderr="boom")

    monkeypatch.setattr(tex.subprocess, "run", fake_run)
    with pytest.raises(ConfigError):
        install_tex_packages(["geometry"])


def test_has_binary(monkeypatch) -> None:
    monkeypatch.setattr(tex.shutil, "which", lambda name: "/bin/yes")
    assert tex._has_binary("yes") is True
    monkeypatch.setattr(tex.shutil, "which", lambda name: None)
    assert tex._has_binary("nope") is False


def test_has_tex_package(monkeypatch) -> None:
    def fake_run(cmd, check, capture_output, text):
        return subprocess.CompletedProcess(cmd, 0, "/path/package.sty\n", "")

    monkeypatch.setattr(tex.subprocess, "run", fake_run)
    assert tex._has_tex_package("geometry") is True

    def fake_run_empty(cmd, check, capture_output, text):
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(tex.subprocess, "run", fake_run_empty)
    assert tex._has_tex_package("geometry") is False

    def fake_run_missing(cmd, check, capture_output, text):
        raise FileNotFoundError()

    monkeypatch.setattr(tex.subprocess, "run", fake_run_missing)
    assert tex._has_tex_package("geometry") is False
