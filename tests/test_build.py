from __future__ import annotations

import json
from pathlib import Path
import stat
import pytest

from vaultchef.build import build_cookbook, _parse_cookbook_meta
from vaultchef.config import resolve_config
from vaultchef.errors import ConfigError, MissingFileError


def _write_mock_pandoc(tmp_path: Path) -> Path:
    script = tmp_path / "pandoc"
    script.write_text(
        """#!/usr/bin/env python3
import sys

args = sys.argv
out = None
for i, arg in enumerate(args):
    if arg == '-o' and i + 1 < len(args):
        out = args[i + 1]

if out:
    with open(out, 'wb') as fh:
        fh.write(b'%PDF-1.4\\n%mock')
""",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


# Purpose: verify build dry run.
def test_build_dry_run(tmp_path: Path, example_vault: Path, temp_home: Path, monkeypatch) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg = resolve_config({"vault_path": str(example_vault), "project": str(tmp_path)})
    result = build_cookbook("Family Cookbook", cfg, dry_run=True, verbose=False)
    assert result.baked_md.exists()
    assert not result.pdf.exists()
    assert not (tmp_path / "build" / "Family Cookbook.pdf").exists()


# Purpose: verify build runs pandoc.
def test_build_runs_pandoc(tmp_path: Path, example_vault: Path, temp_home: Path, monkeypatch) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    pandoc = _write_mock_pandoc(tmp_path)
    cfg = resolve_config(
        {
            "vault_path": str(example_vault),
            "project": str(tmp_path),
            "pandoc_path": str(pandoc),
        }
    )
    result = build_cookbook("Family Cookbook", cfg, dry_run=False, verbose=False)
    build_pdf = tmp_path / "build" / "Family Cookbook.pdf"
    final_pdf = cwd / "Family Cookbook.pdf"
    assert build_pdf.exists()
    assert final_pdf.exists()
    assert result.pdf == final_pdf


# Purpose: verify build writes web app bundle output.
def test_build_writes_web_library_bundle(tmp_path: Path, example_vault: Path, temp_home: Path, monkeypatch) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg = resolve_config({"vault_path": str(example_vault), "project": str(tmp_path)})
    result = build_cookbook("Family Cookbook", cfg, dry_run=False, verbose=False, output_format="web")
    build_index = tmp_path / "build" / "vaultchef-web" / "content" / "index.json"
    final_index = cwd / "vaultchef-web" / "content" / "index.json"
    assert build_index.exists()
    assert final_index.exists()
    assert (cwd / "vaultchef-web" / "index.html").exists()
    payload = json.loads(final_index.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert len(payload["recipes"]) >= 1
    assert len(payload["cookbooks"]) >= 1
    assert result.output == (cwd / "vaultchef-web")
    assert result.output_format == "web"


# Purpose: verify web build copies recipe images and emits reader structure.
def test_build_web_copies_images_and_reader_blocks(tmp_path: Path, temp_home: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    cookbooks = vault / "Cookbooks"
    images = vault / "Images"
    recipes.mkdir(parents=True)
    cookbooks.mkdir(parents=True)
    images.mkdir(parents=True)

    (images / "hero.jpg").write_bytes(b"hero")
    recipes.joinpath("R1.md").write_text(
        "---\nrecipe_id: 1\ntitle: R1\nmenu: Nice one\nimage: Images/hero.jpg\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n",
        encoding="utf-8",
    )
    cookbooks.joinpath("Book.md").write_text(
        "---\ntitle: Book\nsubtitle: Reader Test\n---\n\nWelcome intro line.\n\n# Chapter One\n![[Recipes/R1]]\n",
        encoding="utf-8",
    )

    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path)})

    result = build_cookbook("Book", cfg, dry_run=False, verbose=False, output_format="web")
    assert result.output == (cwd / "vaultchef-web")

    payload = json.loads((cwd / "vaultchef-web" / "content" / "index.json").read_text(encoding="utf-8"))
    recipe = payload["recipes"][0]
    assert recipe["image"].startswith("assets/images/")
    assert recipe["image_alt"] == "R1"
    assert (cwd / "vaultchef-web" / recipe["image"]).exists()

    cookbook = payload["cookbooks"][0]
    assert cookbook["reader_intro_html"] != ""
    assert any(block.get("type") == "chapter" for block in cookbook["reader_blocks"])
    assert any(block.get("type") == "recipe" for block in cookbook["reader_blocks"])

    err = capsys.readouterr().err
    assert "Warning: missing image" not in err


# Purpose: verify web build warns on missing image paths.
def test_build_web_warns_on_missing_images(tmp_path: Path, temp_home: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    cookbooks = vault / "Cookbooks"
    recipes.mkdir(parents=True)
    cookbooks.mkdir(parents=True)

    recipes.joinpath("R1.md").write_text(
        "---\nrecipe_id: 1\ntitle: R1\nimage: Images/missing.jpg\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n",
        encoding="utf-8",
    )
    cookbooks.joinpath("Book.md").write_text("---\ntitle: Book\n---\n\n![[Recipes/R1]]\n", encoding="utf-8")

    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path)})

    build_cookbook("Book", cfg, dry_run=False, verbose=True, output_format="web")
    captured = capsys.readouterr()
    assert "Warning: missing image for recipe 'R1'" in captured.err
    assert "Image warnings: 1" in captured.out


# Purpose: verify build missing cookbook.
def test_build_missing_cookbook(tmp_path: Path, example_vault: Path, temp_home: Path) -> None:
    cfg = resolve_config({"vault_path": str(example_vault), "project": str(tmp_path)})
    with pytest.raises(MissingFileError):
        build_cookbook("Does Not Exist", cfg, dry_run=True, verbose=False)


# Purpose: verify web build does not require cookbook name lookup.
def test_build_web_ignores_missing_cookbook_name(
    tmp_path: Path, example_vault: Path, temp_home: Path, monkeypatch
) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg = resolve_config({"vault_path": str(example_vault), "project": str(tmp_path)})
    result = build_cookbook("Does Not Exist", cfg, dry_run=False, verbose=False, output_format="web")
    assert result.output == (cwd / "vaultchef-web")
    assert (cwd / "vaultchef-web" / "content" / "index.json").exists()


# Purpose: verify build rejects unsupported format.
def test_build_rejects_unsupported_format(tmp_path: Path, example_vault: Path, temp_home: Path) -> None:
    cfg = resolve_config({"vault_path": str(example_vault), "project": str(tmp_path)})
    with pytest.raises(ConfigError):
        build_cookbook("Family Cookbook", cfg, dry_run=True, verbose=False, output_format="epub")


# Purpose: verify parse cookbook meta variants.
def test_parse_cookbook_meta_variants() -> None:
    assert _parse_cookbook_meta("No frontmatter") == {}
    assert _parse_cookbook_meta("---\n- a\n---\n") == {}
    assert _parse_cookbook_meta("---\nsubtitle: null\n---\n") == {}
    assert _parse_cookbook_meta("---\nauthor: [A, B]\n---\n")["author"] == "A, B"
    date_meta = _parse_cookbook_meta("---\ndate: 2026-02-24\n---\n")
    assert date_meta["date"] == "Tuesday, February 24, 2026"
    assert date_meta["web_date"] == "Tuesday, February 24, 2026"
    split_meta = _parse_cookbook_meta(
        "---\nsubtitle: Tuesday, February 24, 2026 · Bright and tropical menu\ndate: 2026-02-24\n---\n"
    )
    assert split_meta["subtitle"] == "Bright and tropical menu"
    assert split_meta["date"] == "Tuesday, February 24, 2026"
    assert split_meta["web_description"] == "Bright and tropical menu"
    assert split_meta["web_date"] == "Tuesday, February 24, 2026"
    inferred_date_meta = _parse_cookbook_meta(
        "---\nsubtitle: Tuesday, February 24, 2026 · Bright and tropical menu\n---\n"
    )
    assert inferred_date_meta["date"] == "Tuesday, February 24, 2026"
    bad_yaml = "---\n: [\n---\n"
    assert _parse_cookbook_meta(bad_yaml) == {}
    meta = _parse_cookbook_meta(
        "---\ninclude_title_page: true\nalbum_title: Test Album\nshopping_compact: false\n---\n"
    )
    assert meta["include_intro_page"] is True
    assert meta["album_title"] == "Test Album"
    assert meta["has_music_pairing"] is True
    assert meta["shopping_compact"] is False
    meta = _parse_cookbook_meta("---\nalbum_youtube_url: https://music.youtube.com/watch?v=abc123\n---\n")
    assert meta["album_youtube_url"] == "https://music.youtube.com/watch?v=abc123"
    assert meta["has_music_pairing"] is True
    meta = _parse_cookbook_meta("---\ninclude_intro_page: false\ninclude_title_page: true\n---\n")
    assert meta["include_intro_page"] is False
    assert _parse_cookbook_meta("---\ninclude_intro_page: 1\n---\n")["include_intro_page"] is True
    assert _parse_cookbook_meta("---\ninclude_intro_page:\n  nested: true\n---\n") == {}
    assert _parse_cookbook_meta("---\ninclude_intro_page: \"yes\"\n---\n")["include_intro_page"] is True
    assert _parse_cookbook_meta("---\ninclude_intro_page: \"off\"\n---\n")["include_intro_page"] is False
    assert _parse_cookbook_meta("---\ninclude_intro_page: \"maybe\"\n---\n") == {}
    meta = _parse_cookbook_meta(
        "---\nsubtitle: Tuesday, February 24, 2026 · Bright and tropical menu\ndate: 2026-02-24\n---\n"
    )
    assert meta["date"] == "Tuesday, February 24, 2026"
    parsed = _parse_cookbook_meta(
        "---\n"
        + "date: !!timestamp '2026-02-24 09:30:00'\n"
        + "subtitle: Tuesday, February 24, 2026 · Bright and tropical menu\n"
        + "---\n"
    )
    assert parsed["date"] == "Tuesday, February 24, 2026"


# Purpose: verify build without title metadata.
def test_build_without_title_metadata(tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    cookbooks = vault / "Cookbooks"
    recipes.mkdir(parents=True)
    cookbooks.mkdir(parents=True)
    recipes.joinpath("R1.md").write_text(
        "---\nrecipe_id: 1\ntitle: R1\n---\n\n## Ingredients\n- a\n\n## Method\n1. b\n",
        encoding="utf-8",
    )
    cookbooks.joinpath("NoTitle.md").write_text("![[Recipes/R1]]\n", encoding="utf-8")

    pandoc = _write_mock_pandoc(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg = resolve_config(
        {"vault_path": str(vault), "project": str(tmp_path), "pandoc_path": str(pandoc)}
    )
    result = build_cookbook("NoTitle", cfg, dry_run=False, verbose=False)
    assert result.pdf.exists()


# Purpose: verify build adds intro shopping metadata.
def test_build_adds_intro_shopping_metadata(tmp_path: Path, temp_home: Path, monkeypatch) -> None:
    vault = tmp_path / "Vault"
    recipes = vault / "Recipes"
    cookbooks = vault / "Cookbooks"
    recipes.mkdir(parents=True)
    cookbooks.mkdir(parents=True)
    recipes.joinpath("R1.md").write_text(
        "---\nrecipe_id: 1\ntitle: R1\n---\n\n## Ingredients\n- 1 tbsp olive oil\n\n## Method\n1. b\n",
        encoding="utf-8",
    )
    recipes.joinpath("R2.md").write_text(
        "---\nrecipe_id: 2\ntitle: R2\n---\n\n## Ingredients\n- 2 tablespoons olive oil\n\n## Method\n1. b\n",
        encoding="utf-8",
    )
    cookbooks.joinpath("Book.md").write_text(
        "---\ninclude_intro_page: true\n---\n\n![[Recipes/R1]]\n![[Recipes/R2]]\n",
        encoding="utf-8",
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg = resolve_config({"vault_path": str(vault), "project": str(tmp_path)})

    captured: dict[str, object] = {}

    def fake_run_pandoc(
        input_md: str,
        output_pdf: str,
        cfg: object,
        verbose: bool,
        output_format: str = "pdf",
        extra_metadata: dict[str, object] | None = None,
        extra_resource_paths: list[str] | None = None,
    ) -> None:
        captured["metadata"] = extra_metadata or {}
        captured["output_format"] = output_format
        Path(output_pdf).write_bytes(b"%PDF-1.4\n%mock")

    monkeypatch.setattr("vaultchef.services.build_service.run_pandoc", fake_run_pandoc)
    result = build_cookbook("Book", cfg, dry_run=False, verbose=False)
    assert result.pdf.exists()
    meta = captured["metadata"]
    assert isinstance(meta, dict)
    assert meta["include_intro_page"] is True
    assert meta["shopping_items"] == ["3 tbsp olive oil"]
    assert captured["output_format"] == "pdf"
