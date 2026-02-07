from __future__ import annotations

import subprocess
from typing import Mapping


def run_process(
    cmd: list[str],
    *,
    env: Mapping[str, str] | None = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=text,
        env=dict(env) if env is not None else None,
    )
