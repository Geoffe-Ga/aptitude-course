#!/usr/bin/env python3
"""Add per-chapter YAML frontmatter to every stage chapter (issue #19).

With bodies cleaned (#18) and the schema fixed (#17), each chapter needs the
frontmatter block that makes the corpus machine-readable for the manifest
generator (#20) and the app's seed.

Everything except ``release_day`` is derived **mechanically** from the existing
``markdown/<NN-stage>/<NN-slug>.md`` convention, so the metadata cannot disagree
with the file's location:

* ``stage``        = the folder's numeric prefix (1..10)
* ``chapter``      = 1-based position within the stage (sorted by filename)
* ``order``        = same as ``chapter``
* ``slug``         = filename with the ``NN-`` prefix and ``.md`` stripped
* ``id``           = ``"<stage-slug>-<chapter>"`` (e.g. ``beige-1``)
* ``title``        = the file's first Markdown heading
* ``content_type`` = ``chapter``
* ``release_day``  = ``chapter - 1`` (the "daily" drip default; a human may
                     later hand-tune this where the curriculum intends another
                     cadence — that is the single non-mechanical knob)

This script **only prepends** the block: the body bytes are asserted unchanged.
It is idempotent — files that already begin with frontmatter are skipped.

Usage::

    python scripts/add_frontmatter.py            # write frontmatter in place
    python scripts/add_frontmatter.py --check     # report only, write nothing
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"

STAGE_DIR_RE = re.compile(r"^(\d{2})-([a-z0-9]+)$")
CHAPTER_FILE_RE = re.compile(r"^(\d{2})-(.+)\.md$")
HEADING_RE = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t]*$")


def stage_dirs() -> list[Path]:
    return sorted(p for p in MARKDOWN_DIR.iterdir() if p.is_dir() and STAGE_DIR_RE.match(p.name))


def chapter_files(stage_dir: Path) -> list[Path]:
    """Numbered section files in display order, excluding the TOC (00-...)."""
    files = []
    for p in stage_dir.iterdir():
        m = CHAPTER_FILE_RE.match(p.name)
        if m and m.group(1) != "00":  # skip 00-table-of-contents (navigational)
            files.append(p)
    return sorted(files, key=lambda p: p.name)


def slug_from_filename(name: str) -> str:
    return CHAPTER_FILE_RE.match(name).group(2)


def title_from_body(text: str, fallback_slug: str) -> str:
    for line in text.splitlines():
        if not line.strip():
            continue
        m = HEADING_RE.match(line)
        if m:
            return m.group(1).strip()
        break  # first non-empty line wasn't a heading; use the fallback
    return fallback_slug.replace("-", " ").title()


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_frontmatter(*, id_: str, stage: int, chapter: int, slug: str,
                      title: str, release_day: int) -> str:
    lines = [
        "---",
        f"id: {id_}",
        f"stage: {stage}",
        f"chapter: {chapter}",
        f"order: {chapter}",
        f"slug: {slug}",
        f"title: {yaml_quote(title)}",
        "content_type: chapter",
        f"release_day: {release_day}",
        "media: []",
        "---",
        "",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report only; write nothing")
    args = parser.parse_args()

    written: list[Path] = []
    skipped = 0
    failures: list[str] = []

    for stage_dir in stage_dirs():
        stage_num = int(STAGE_DIR_RE.match(stage_dir.name).group(1))
        stage_slug = STAGE_DIR_RE.match(stage_dir.name).group(2)

        for chapter, path in enumerate(chapter_files(stage_dir), start=1):
            original = path.read_text(encoding="utf-8")
            if original.startswith("---\n") or original.startswith("---\r\n"):
                skipped += 1
                continue

            slug = slug_from_filename(path.name)
            frontmatter = build_frontmatter(
                id_=f"{stage_slug}-{chapter}",
                stage=stage_num,
                chapter=chapter,
                slug=slug,
                title=title_from_body(original, slug),
                release_day=chapter - 1,
            )
            updated = frontmatter + original

            # Body must be byte-for-byte unchanged — frontmatter is prepended only.
            if updated[len(frontmatter):] != original:
                failures.append(f"{path}: body would change (refusing to write)")
                continue

            written.append(path)
            if not args.check:
                path.write_text(updated, encoding="utf-8")

    rel = lambda p: p.relative_to(REPO_ROOT)
    if failures:
        print("BODY-UNCHANGED CHECK FAILED — no files written:", file=sys.stderr)
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        return 1

    verb = "would add" if args.check else "added"
    print(f"{verb} frontmatter to {len(written)} chapter(s); {skipped} already had it.")
    by_stage: dict[str, int] = {}
    for p in written:
        by_stage[p.parent.name] = by_stage.get(p.parent.name, 0) + 1
    for stage in sorted(by_stage):
        print(f"  {stage}: {by_stage[stage]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
