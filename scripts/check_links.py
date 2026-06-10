#!/usr/bin/env python3
"""Check that internal links and images in markdown/** resolve (issue #21).

Walks every Markdown file under ``markdown/`` (excluding ``backup/`` and
editor metadata), extracts inline links and images, and verifies that every
repo-internal target exists on disk. External targets (``https://``,
``http://``, ``mailto:``) are skipped — checking them needs the network,
which CI deliberately avoids. Pure-fragment links (``#anchor``) are skipped
as well; heading-anchor validation is out of scope here.

Relative targets are resolved against the containing file's directory.
Exits non-zero listing every broken reference.

Usage::

    python scripts/check_links.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"
EXCLUDED_DIRS = {"backup", ".obsidian"}

# Inline links/images: [text](target) or ![alt](target "title")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)<>\s]+)>?(?:\s+\"[^\"]*\")?\s*\)")
EXTERNAL_RE = re.compile(r"^(https?:|mailto:|tel:|data:)", re.IGNORECASE)
FENCE_RE = re.compile(r"^(```|~~~)")


def iter_markdown_files() -> list[Path]:
    files = []
    for path in sorted(MARKDOWN_DIR.rglob("*.md")):
        rel_parts = path.relative_to(MARKDOWN_DIR).parts
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        files.append(path)
    return files


def iter_targets(text: str):
    """Yield (line_number, target) for each inline link/image outside code fences."""
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Drop inline code spans so `[x](y)` inside backticks is ignored.
        stripped = re.sub(r"`[^`]*`", "", line)
        for m in LINK_RE.finditer(stripped):
            yield lineno, m.group(1)


def main() -> int:
    broken: list[str] = []
    checked = 0

    for path in iter_markdown_files():
        text = path.read_text(encoding="utf-8")
        for lineno, target in iter_targets(text):
            if EXTERNAL_RE.match(target):
                continue
            target_path = unquote(target.split("#", 1)[0])
            if not target_path:  # pure fragment link
                continue
            checked += 1
            resolved = (path.parent / target_path).resolve()
            if not resolved.exists():
                rel = path.relative_to(REPO_ROOT).as_posix()
                broken.append(f"{rel}:{lineno}: broken link '{target}'")

    if broken:
        print(f"link check FAILED — {len(broken)} broken reference(s):",
              file=sys.stderr)
        for line in broken:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"link check passed: {checked} internal references resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
