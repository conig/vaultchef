from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecipeSummary:
    recipe_id: str | None
    title: str
    path: Path
    category: str | None
    tags: list[str]


@dataclass(frozen=True)
class CookbookSummary:
    title: str
    stem: str
    path: Path
