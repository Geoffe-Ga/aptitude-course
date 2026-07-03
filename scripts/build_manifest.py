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

Each stage's optional ``stage_intros[]`` entry (content-repo spec CR-B,
adepthood#717, ``schema_version`` ``1.1.0``) is **derived**, not authored: it
is a second, ungated, non-drip-fed manifest view onto that stage's existing
chapter 1 ("What is `<Stage>`?"), not a separate file. There is no dedicated
intro Markdown to write or keep in sync — the tier disappears on its own if a
stage ever has no chapter 1.

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

SCHEMA_VERSION = "1.1.0"  # coordinate bumps with adepthood#389 (see CONSUMPTION.md)

EXCLUDED_DIRS = {"backup", "images", "meta", ".obsidian", "resources"}
STAGE_DIR_RE = re.compile(r"^\d{2}-[a-z0-9]+$")
CHAPTER_FILE_RE = re.compile(r"^(\d{2})-(.+)\.md$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONTENT_TYPES = {"chapter", "essay", "prompt", "video"}

# Field order in the emitted manifest (deterministic, human-readable).
CHAPTER_KEYS = ["id", "stage", "chapter", "order", "slug", "title",
                "content_type", "release_day", "summary", "media", "path"]
RESOURCE_KEYS = ["slug", "title", "description", "media", "path"]
STAGE_INTRO_KEYS = ["stage", "id", "slug", "title", "summary", "path"]


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


def collect_stage_intros(chapters: list[dict]) -> list[dict]:
    """Derive stage_intros[] from each stage's own chapter 1.

    A stage's existing "What is <Stage>?" chapter already serves as its
    start-here reading, so the intro is a second, ungated, non-drip-fed
    manifest entry pointing at that same file — never a separately authored
    one. ``id``/``slug`` are mechanically derived from the stage folder name
    (distinct from the chapter's own ``id``/``slug`` so the app can key the
    intro card independently of the drip-fed chapter row); ``title`` and
    ``summary`` are reused verbatim from the chapter's frontmatter.
    """
    intros: list[dict] = []
    for c in chapters:
        if c.get("chapter") != 1:
            continue
        folder = c["path"].split("/")[1]  # e.g. "01-beige"
        folder_slug = folder.split("-", 1)[1]  # e.g. "beige"
        entry = {
            "stage": c["stage"],
            "id": f"{folder_slug}-intro",
            "slug": f"{folder_slug}-introduction",
            "title": c["title"],
            "path": c["path"],
        }
        if c.get("summary"):
            entry["summary"] = c["summary"]
        intros.append(entry)
    intros.sort(key=lambda i: i["stage"])
    return intros


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
def validate(chapters: list[dict]) -> dict[str, str]:
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

        validate_media(c["media"], path)

    return seen_ids


def validate_stage_intros(intros: list[dict], seen_ids: dict[str, str]) -> None:
    """Validate stage_intros[] per content-repo spec CR-B/CR-C (adepthood#717)."""
    seen_stages: dict[int, str] = {}
    required = ["stage", "id", "slug", "title", "path"]

    for intro in intros:
        path = intro["path"]
        for field in required:
            if intro.get(field) is None:
                raise ManifestError(f"{path}: missing required field '{field}'")

        if not isinstance(intro["stage"], int) or not (1 <= intro["stage"] <= 10):
            raise ManifestError(f"{path}: stage {intro['stage']} out of range 1..10")
        if not SLUG_RE.match(intro["slug"]):
            raise ManifestError(f"{path}: slug '{intro['slug']}' is not URL-safe")

        if intro["id"] in seen_ids:
            raise ManifestError(
                f"duplicate id '{intro['id']}' in {path} and {seen_ids[intro['id']]}")
        seen_ids[intro["id"]] = path

        if intro["stage"] in seen_stages:
            raise ManifestError(
                f"duplicate stage_intro for stage {intro['stage']} in {path} "
                f"and {seen_stages[intro['stage']]}")
        seen_stages[intro["stage"]] = path


MEDIA_TYPES = {"video", "image", "audio"}


def validate_media(media, path: str) -> None:
    """Validate media[] shape per CONTENT_FORMAT.md §6.3 (issue #25)."""
    if not isinstance(media, list):
        raise ManifestError(f"{path}: media must be a list")
    for i, item in enumerate(media):
        where = f"{path}: media[{i}]"
        if not isinstance(item, dict):
            raise ManifestError(f"{where}: must be a mapping")
        unknown = set(item) - {"type", "url", "path", "poster", "caption"}
        if unknown:
            raise ManifestError(f"{where}: unknown field(s) {sorted(unknown)}")
        if item.get("type") not in MEDIA_TYPES:
            raise ManifestError(
                f"{where}: type must be one of {sorted(MEDIA_TYPES)}")
        has_url, has_path = "url" in item, "path" in item
        if has_url == has_path:
            raise ManifestError(f"{where}: exactly one of url/path is required")
        if has_url and not str(item["url"]).startswith("https://"):
            raise ManifestError(f"{where}: url must be an absolute https:// URL")
        for field in ("path", "poster", "caption"):
            if field in item and not isinstance(item[field], str):
                raise ManifestError(f"{where}: {field} must be a string")


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
    seen_ids = validate(chapters)
    clean_chapters = [{k: c[k] for k in CHAPTER_KEYS if k in c} for c in chapters]

    intros = collect_stage_intros(chapters)
    validate_stage_intros(intros, seen_ids)
    clean_intros = [{k: i[k] for k in STAGE_INTRO_KEYS if k in i} for i in intros]

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "chapters": clean_chapters,
        "site_resources": collect_site_resources(),
    }
    if clean_intros:
        manifest["stage_intros"] = clean_intros
    return manifest


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
              f"{len(manifest['site_resources'])} resources, "
              f"{len(manifest.get('stage_intros', []))} stage intros; {schema_note})")
        return 0

    MANIFEST_PATH.write_text(output, encoding="utf-8")
    print(f"wrote manifest.json: {len(manifest['chapters'])} chapters, "
          f"{len(manifest['site_resources'])} site resources, "
          f"{len(manifest.get('stage_intros', []))} stage intros; {schema_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
