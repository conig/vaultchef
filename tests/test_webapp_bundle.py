from __future__ import annotations

from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parents[1]


# Purpose: verify web app template files are present.
def test_webapp_template_files_exist() -> None:
    base = ROOT / "templates" / "webapp"
    assert (base / "index.html").exists()
    assert (base / "app.css").exists()
    assert (base / "app.js").exists()
    assert (base / "interaction.mjs").exists()
    assert 'id="vc-feature-slot"' in (base / "index.html").read_text(encoding="utf-8")


# Purpose: verify web app script includes hash routes and morph animation hooks.
def test_webapp_script_includes_routes_and_morph() -> None:
    text = (ROOT / "templates" / "webapp" / "app.js").read_text(encoding="utf-8")
    assert "/recipes/" in text
    assert "/cookbooks/" in text
    assert 'from "./interaction.mjs"' in text
    assert "pendingMorphRect" in text
    assert "vc-morph-overlay" in text
    assert "data-scroll-target" in text
    assert "reader_blocks" in text
    assert "vc-recipe-card" in text
    assert "renderRecipeHero" in text
    assert "toYouTubeMusicUrl" in text
    assert "data-vc-music-url" in text
    assert "data-cookbook-nav-toggle" in text
    assert "vc-nav-open" in text
    assert "getFeaturedDateNightCookbook" in text
    assert "renderSidebarFeature" in text
    assert "transitioncancel" in text
    assert "clearMorphArtifacts" in text
    assert "vc-mode-recipe-reader" in text
    assert "data-recipe-layout" in text


# Purpose: verify web app css preserves mobile tap target sizing.
def test_webapp_css_tap_targets() -> None:
    text = (ROOT / "templates" / "webapp" / "app.css").read_text(encoding="utf-8")
    assert "min-height: 44px" in text
    assert ".vc-mode-cookbook" in text
    assert ".vc-cookbook-shell" in text
    assert ".vc-hero" in text
    assert ".vc-music-link" in text
    assert ".vc-cookbook-nav-toggle" in text
    assert ".vc-nav-icon-bar" in text
    assert ".vc-feature-card" in text
    assert ".vc-mode-recipe-reader" in text
    assert ".vc-detail-back-btn" in text


# Purpose: verify pure interaction helpers classify taps vs scroll gestures correctly.
def test_webapp_interaction_helpers() -> None:
    interaction = (ROOT / "templates" / "webapp" / "interaction.mjs").as_uri()
    script = f"""
import {{ isMobileViewport, shouldActivateCard, shouldMorphCardOpen, shouldSyncCookbookNav }} from {json.dumps(interaction)};

const result = {{
  mobile: isMobileViewport(447),
  desktop: isMobileViewport(1200),
  touchTap: shouldActivateCard({{
    pointerType: "touch",
    startX: 10,
    startY: 10,
    endX: 14,
    endY: 16,
    scrollDeltaY: 0,
    elapsedMs: 180,
    wasCancelled: false,
  }}),
  touchScroll: shouldActivateCard({{
    pointerType: "touch",
    startX: 10,
    startY: 10,
    endX: 12,
    endY: 35,
    scrollDeltaY: 22,
    elapsedMs: 210,
    wasCancelled: false,
  }}),
  mouseOpen: shouldActivateCard({{
    pointerType: "mouse",
    startX: 10,
    startY: 10,
    endX: 80,
    endY: 80,
    scrollDeltaY: 0,
    elapsedMs: 700,
    wasCancelled: false,
  }}),
  morphMobile: shouldMorphCardOpen({{ width: 447, reducedMotion: false }}),
  morphDesktop: shouldMorphCardOpen({{ width: 1200, reducedMotion: false }}),
  syncBlocked: shouldSyncCookbookNav({{ now: 100, suppressUntil: 500 }}),
  syncOpen: shouldSyncCookbookNav({{ now: 700, suppressUntil: 500 }}),
}};

process.stdout.write(JSON.stringify(result));
"""
    output = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(output.stdout)
    assert result == {
        "mobile": True,
        "desktop": False,
        "touchTap": True,
        "touchScroll": False,
        "mouseOpen": True,
        "morphMobile": False,
        "morphDesktop": True,
        "syncBlocked": False,
        "syncOpen": True,
    }
