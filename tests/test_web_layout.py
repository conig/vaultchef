from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


# Purpose: verify web template includes cook-mode layout hooks.
def test_web_template_includes_recipe_shell_hooks() -> None:
    text = (ROOT / "templates" / "cookbook.html").read_text(encoding="utf-8")
    assert ".vc-recipe-shell" in text
    assert ".vc-col-left" in text
    assert ".vc-col-right" in text
    assert ".vc-section + .vc-section" in text


# Purpose: verify web filter emits semantic recipe column wrappers.
def test_web_filter_emits_semantic_recipe_wrappers() -> None:
    text = (ROOT / "filters" / "web.lua").read_text(encoding="utf-8")
    assert '"vc-recipe-shell"' in text
    assert '"vc-recipe-col", "vc-col-left"' in text
    assert '"vc-recipe-col", "vc-col-right"' in text
    assert '"vc-section", "vc-section-ingredients"' in text
    assert '"vc-section", "vc-section-method"' in text


# Purpose: verify web template includes music pairing hooks.
def test_web_template_includes_music_pairing_hooks() -> None:
    text = (ROOT / "templates" / "cookbook.html").read_text(encoding="utf-8")
    assert ".vc-music-panel" in text
    assert ".vc-music-panel-desktop" in text
    assert ".vc-music-panel-mobile" in text
    assert "data-vc-music-url" in text
    assert "toYouTubeMusicUrl" in text


# Purpose: verify pdf template supports music listen URL.
def test_pdf_template_includes_music_link_field() -> None:
    text = (ROOT / "templates" / "cookbook.tex").read_text(encoding="utf-8")
    assert "$if(album_youtube_url)$" in text
    assert "\\item \\textbf{Listen:} \\url{$album_youtube_url$}" in text
