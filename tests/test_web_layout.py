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


# Purpose: verify web template includes mobile hamburger drawer hooks.
def test_web_template_includes_mobile_hamburger_hooks() -> None:
    text = (ROOT / "templates" / "cookbook.html").read_text(encoding="utf-8")
    assert ".vc-nav-icon" in text
    assert ".vc-nav-icon-bar" in text
    assert "Open navigation menu" in text
    assert "Close navigation menu" in text
    assert "translateX(calc(100% + 16px))" in text
    assert "VAULTCHEF" in text
    assert "$if(web_date)$" in text
    assert "$if(web_description)$" in text
    assert 'class="vc-date"' in text


# Purpose: verify pdf template keeps music metadata only (no URL link).
def test_pdf_template_excludes_music_link_field() -> None:
    text = (ROOT / "templates" / "cookbook.tex").read_text(encoding="utf-8")
    assert "$if(album_youtube_url)$" not in text
    assert "\\item \\textbf{Listen:}" not in text
