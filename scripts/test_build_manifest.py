"""Gate tests for scripts/build_manifest.py (issue #75).

Run with ``python -m pytest scripts -q`` (CI job *Frontmatter + manifest*).
Each test writes a tiny ``resources/`` fixture to a temp dir and points the
generator at it, so the suite is hermetic and runs in well under a second.
The point is to prove the gate *fails* on a violating fixture, not only that
it passes on the committed corpus.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import build_manifest as bm


def _write_resource(root: Path, filename: str, slug: str, **extra: object) -> None:
    lines = [f"slug: {slug}", f'title: "{slug.title()}"', "content_type: essay",
             'description: "x"', "media: []"]
    lines += [f"{k}: {v}" for k, v in extra.items()]
    (root / filename).write_text("---\n" + "\n".join(lines) + "\n---\n\nBody.\n",
                                 encoding="utf-8")


@pytest.fixture
def resources_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "markdown" / "resources"
    root.mkdir(parents=True)
    monkeypatch.setattr(bm, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(bm, "RESOURCES_DIR", root)
    return root


def _collect_and_validate() -> list[dict]:
    resources = bm.collect_site_resources()
    bm.validate_site_resources(resources)
    return resources


def test_order_comes_from_filename_prefix(resources_dir: Path) -> None:
    _write_resource(resources_dir, "02-about.md", "about")
    _write_resource(resources_dir, "01-liminal-creep.md", "liminal-creep")

    resources = _collect_and_validate()

    assert [(r["order"], r["slug"]) for r in resources] == [
        (1, "liminal-creep"), (2, "about")]


def test_gap_in_order_fails(resources_dir: Path) -> None:
    _write_resource(resources_dir, "01-a.md", "a")
    _write_resource(resources_dir, "03-c.md", "c")

    with pytest.raises(bm.ManifestError, match="contiguous"):
        _collect_and_validate()


def test_duplicate_order_fails(resources_dir: Path) -> None:
    _write_resource(resources_dir, "01-a.md", "a")
    _write_resource(resources_dir, "01-b.md", "b")

    with pytest.raises(bm.ManifestError, match="contiguous"):
        _collect_and_validate()


def test_order_not_starting_at_one_fails(resources_dir: Path) -> None:
    _write_resource(resources_dir, "02-a.md", "a")

    with pytest.raises(bm.ManifestError, match="contiguous"):
        _collect_and_validate()


def test_unprefixed_filename_fails(resources_dir: Path) -> None:
    _write_resource(resources_dir, "about.md", "about")

    with pytest.raises(bm.ManifestError, match="NN-slug.md"):
        _collect_and_validate()


def test_frontmatter_order_must_agree_with_prefix(resources_dir: Path) -> None:
    _write_resource(resources_dir, "01-a.md", "a", order=2)

    with pytest.raises(bm.ManifestError, match="filename prefix"):
        _collect_and_validate()


def test_slug_must_match_filename_slug(resources_dir: Path) -> None:
    _write_resource(resources_dir, "01-a.md", "b")

    with pytest.raises(bm.ManifestError, match="filename slug"):
        _collect_and_validate()


def test_committed_corpus_is_an_ordered_start_here_list() -> None:
    """The real resources/ dir carries the agreed reading order (issue #75)."""
    resources = bm.collect_site_resources()
    bm.validate_site_resources(resources)

    assert [r["slug"] for r in resources] == [
        "liminal-creep", "about", "energy-scaffolding", "aptitude-stages",
        "archetypal-wavelength", "wavelength-explainer", "notes-and-chords"]
