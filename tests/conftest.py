from __future__ import annotations

from pathlib import Path
import ast
import dis
import sys
import types
import pytest

EXECUTED: dict[str, set[int]] = {}

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _tracer(frame, event, arg):  # pragma: no cover - exercised indirectly
    if event != "line":
        return _tracer
    filename = frame.f_code.co_filename
    if filename.startswith(str(SRC)):
        EXECUTED.setdefault(filename, set()).add(frame.f_lineno)
    return _tracer


sys.settrace(_tracer)


@pytest.fixture()
def example_vault() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "VaultExample"


@pytest.fixture()
def temp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def pytest_sessionfinish(session, exitstatus):  # pragma: no cover - test helper
    sys.settrace(None)
    missing = _coverage_missing()
    if missing:
        details = []
        for file, lines in sorted(missing.items()):
            details.append(f"{file}: {lines}")
        raise AssertionError("Missing coverage lines:\n" + "\n".join(details))


def _coverage_missing() -> dict[str, list[int]]:
    missing: dict[str, list[int]] = {}
    for path in SRC.rglob("*.py"):
        if _is_coverage_exempt(path):
            continue
        expected = _executable_lines(path)
        executed = EXECUTED.get(str(path), set())
        diff = sorted(expected - executed)
        if diff:
            missing[str(path)] = diff
    return missing


def _is_coverage_exempt(path: Path) -> bool:
    """Allow intentionally dynamic UI modules to evolve without hard coverage gating."""
    if path.name == "tui.py":
        return True
    if "tui" in path.parts:
        return True
    return False


def _executable_lines(path: Path) -> set[int]:
    text = path.read_text(encoding="utf-8")
    code = compile(text, str(path), "exec")
    lines = _code_lines(code)
    lines -= _signature_lines(text)

    filtered: set[int] = set()
    file_lines = text.splitlines()
    for line_no in lines:
        if line_no is None:
            continue
        if line_no <= 0 or line_no > len(file_lines):
            continue
        line = file_lines[line_no - 1].strip()
        if not line or line.startswith("#"):
            continue
        if "# pragma: no cover" in line:
            continue
        filtered.add(line_no)
    return filtered


def _code_lines(code: types.CodeType) -> set[int]:
    lines = {lineno for _, lineno in dis.findlinestarts(code) if lineno is not None}
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            lines.update(_code_lines(const))
    return lines


def _signature_lines(text: str) -> set[int]:
    tree = ast.parse(text)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.body:
                continue
            start = node.lineno + 1
            first_body = node.body[0].lineno
            for line_no in range(start, first_body):
                lines.add(line_no)
    return lines
