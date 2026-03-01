from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


# Purpose: verify web app template files are present.
def test_webapp_template_files_exist() -> None:
    base = ROOT / "templates" / "webapp"
    assert (base / "index.html").exists()
    assert (base / "app.css").exists()
    assert (base / "app.js").exists()


# Purpose: verify web app script includes hash routes and morph animation hooks.
def test_webapp_script_includes_routes_and_morph() -> None:
    text = (ROOT / "templates" / "webapp" / "app.js").read_text(encoding="utf-8")
    assert "/recipes/" in text
    assert "/cookbooks/" in text
    assert "pendingMorphRect" in text
    assert "vc-morph-overlay" in text
    assert "data-recipe-jump" in text


# Purpose: verify web app css preserves mobile tap target sizing.
def test_webapp_css_tap_targets() -> None:
    text = (ROOT / "templates" / "webapp" / "app.css").read_text(encoding="utf-8")
    assert "min-height: 44px" in text
