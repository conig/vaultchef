from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecipeInfo:
    recipe_id: str | None
    title: str
    path: Path
    tags: list[str]

    def display(self, selected: bool) -> str:
        marker = "[x]" if selected else "[ ]"
        rid = f"{self.recipe_id}: " if self.recipe_id not in (None, "") else ""
        return f"{marker} {rid}{self.title}"


@dataclass(frozen=True)
class CookbookInfo:
    title: str
    stem: str
    path: Path

    def display(self) -> str:
        if self.title and self.title != self.stem:
            return f"{self.title} ({self.stem})"
        return self.stem
