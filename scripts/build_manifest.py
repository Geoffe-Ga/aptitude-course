#!/usr/bin/env python3
"""Generate manifest.json from per-file YAML frontmatter (issue #20).

The Adepthood app consumes a single machine-readable index, not 209 loose
files. ``manifest.json`` is that contract (schema in ``schema/manifest.schema.json``,
aligned with adepthood#389). It is **generated** from frontmatter so the files
stay the source of truth and the manifest never drifts by hand.

The generator is pure and deterministic (no network, stable key order): the
same content always yields a byte-identical manifest. It fails loudly on
duplicate ``id`` / ``(stage, chapter)``, missing required fields, a bad
``content_type``/``release_day``, or a ``slug`` that disagrees with the
filename.

Usage::

    python scripts/build_manifest.py            # write manifest.json
    python scripts/build_manifest.py --check     # verify committed manifest is current
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"
RESOURCES_DIR = MARKDOWN_DIR / "resources"
MANIFEST_PATH = REPO_ROOT / "manifest.json"
SCHEMA_PATH = REPO_ROOT / "schema" / "manifest.schema.json"

SCHEMA_VERSION = "1.0.0"  # coordinate bumps with adepthood#389 (see CONSUMPTION.md)

EXCLUDED_DIRS = {"backup", "images", "meta", ".obsidian", "resources"}
STAGE_DIR_RE = re.compile(r"^\d{2}-[a-z0-9]+$")
CHAPTER_FILE_RE = re.compile(r"^(\d{2})-(.+)\.md$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONTENT_TYPES = {"chapter", "essay", "prompt", "video"}

# Field order in the emitted manifest (deterministic, human-readable).
CHAPTER_KEYS = ["id", "stage", "chapter", "order", "slug", "title",
                "content_type", "release_day", "summary", "media", "path"]
RESOURCE_KEYS = ["slug", "title", "description", "media", "path"]


class ManifestError(Exception):
    """A content/frontmatter problem that must abort the build."""


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ManifestError(f"{rel(path)}: missing frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ManifestError(f"{rel(path)}: malformed frontmatter delimiters")
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise ManifestError(f"{rel(path)}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError(f"{rel(path)}: frontmatter is not a mapping")
    return data


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
def collect_chapters() -> list[dict]:
    chapters: list[dict] = []
    for stage_dir in sorted(p for p in MARKDOWN_DIR.iterdir()
                            if p.is_dir() and STAGE_DIR_RE.match(p.name)):
        for path in sorted(stage_dir.iterdir()):
            m = CHAPTER_FILE_RE.match(path.name)
            if not m or m.group(1) == "00":  # skip TOC / non-chapter files
                continue
            fm = read_frontmatter(path)
            entry = {k: fm.get(k) for k in CHAPTER_KEYS if k in fm}
            entry.setdefault("media", [])
            entry["path"] = rel(path)
            entry["_filename_slug"] = m.group(2)
            chapters.append(entry)
    chapters.sort(key=lambda c: (c.get("stage", 0), c.get("order", 0)))
    return chapters


def collect_site_resources() -> list[dict]:
    if not RESOURCES_DIR.is_dir():
        return []
    resources: list[dict] = []
    for path in sorted(RESOURCES_DIR.glob("*.md")):
        fm = read_frontmatter(path)
        entry = {k: fm[k] for k in RESOURCE_KEYS if k in fm}
        if "description" not in entry and "summary" in fm:
            entry["description"] = fm["summary"]
        entry["path"] = rel(path)
        resources.append(entry)
    resources.sort(key=lambda r: r.get("slug", ""))
    return resources


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate(chapters: list[dict]) -> None:
    seen_ids: dict[str, str] = {}
    seen_stage_chapter: dict[tuple, str] = {}
    required = ["id", "stage", "chapter", "order", "slug", "title",
                "content_type", "release_day"]

    for c in chapters:
        path = c["path"]
        for field in required:
            if c.get(field) is None:
                raise ManifestError(f"{path}: missing required field '{field}'")

        if c["slug"] != c["_filename_slug"]:
            raise ManifestError(
                f"{path}: slug '{c['slug']}' != filename slug '{c['_filename_slug']}'")
        if not SLUG_RE.match(c["slug"]):
            raise ManifestError(f"{path}: slug '{c['slug']}' is not URL-safe")
        if c["content_type"] not in CONTENT_TYPES:
            raise ManifestError(f"{path}: bad content_type '{c['content_type']}'")
        if not isinstance(c["release_day"], int) or c["release_day"] < 0:
            raise ManifestError(f"{path}: release_day must be an int >= 0")
        if not (1 <= c["stage"] <= 10):
            raise ManifestError(f"{path}: stage {c['stage']} out of range 1..10")

        if c["id"] in seen_ids:
            raise ManifestError(
                f"duplicate id '{c['id']}' in {path} and {seen_ids[c['id']]}")
        seen_ids[c["id"]] = path

        key = (c["stage"], c["chapter"])
        if key in seen_stage_chapter:
            raise ManifestError(
                f"duplicate (stage,chapter)={key} in {path} and {seen_stage_chapter[key]}")
        seen_stage_chapter[key] = path


def validate_against_schema(manifest: dict) -> str:
    """Validate with jsonschema if available; otherwise note it was skipped."""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return "jsonschema not installed — relied on built-in checks"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    return "validated against schema/manifest.schema.json"


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def build_manifest() -> dict:
    chapters = collect_chapters()
    validate(chapters)
    clean_chapters = [{k: c[k] for k in CHAPTER_KEYS if k in c} for c in chapters]
    return {
        "schema_version": SCHEMA_VERSION,
        "chapters": clean_chapters,
        "site_resources": collect_site_resources(),
    }


def serialize(manifest: dict) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if committed manifest.json differs from a fresh build")
    args = parser.parse_args()

    try:
        manifest = build_manifest()
    except ManifestError as exc:
        print(f"manifest build FAILED: {exc}", file=sys.stderr)
        return 1

    schema_note = validate_against_schema(manifest)
    output = serialize(manifest)

    if args.check:
        if not MANIFEST_PATH.exists():
            print("manifest.json is missing — run scripts/build_manifest.py", file=sys.stderr)
            return 1
        if MANIFEST_PATH.read_text(encoding="utf-8") != output:
            print("manifest.json is STALE — re-run scripts/build_manifest.py and commit",
                  file=sys.stderr)
            return 1
        print(f"manifest.json is current "
              f"({len(manifest['chapters'])} chapters, "
              f"{len(manifest['site_resources'])} resources; {schema_note})")
        return 0

    MANIFEST_PATH.write_text(output, encoding="utf-8")
    print(f"wrote manifest.json: {len(manifest['chapters'])} chapters, "
          f"{len(manifest['site_resources'])} site resources; {schema_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
