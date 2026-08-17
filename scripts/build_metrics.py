#!/usr/bin/env python3
"""Generate markdown/meta/metrics.md from the indexed corpus.

``metrics.md`` is the repo's at-a-glance picture of the curriculum: how much
content exists, how it is distributed across the ten stages, and where the
long and short chapters are. CLAUDE.md asks that it be refreshed after
significant content changes, which only works if refreshing is one command.

The previous metrics.md was produced by an ad-hoc shell pipeline against the
**old flat layout** (ten `markdown/N.STAGE.md` files). Since the split into
209 per-chapter files it has been unrecoverably stale — it reported 15
documents, and its header carried a literal, never-expanded
``$(date '+%B %d, %Y at %I:%M %p')``. This script replaces that pipeline.

What it counts
--------------
The **indexed** corpus — every chapter and site resource listed in
``manifest.json`` — so metrics describe exactly the surface the Adepthood app
publishes, and can never disagree with the manifest about what exists. Files
under ``markdown/`` that the manifest does not index (stage ``README.md`` and
``00-table-of-contents.md`` navigation, ``backup/``, ``meta/`` itself) are
excluded; they are duplicates or scaffolding and would double-count. Anything
else unindexed is reported in an "Unindexed files" section rather than
silently dropped.

Word counts are taken over the chapter **body** (frontmatter removed, fenced
code stripped) counting whitespace-separated tokens that contain at least one
alphanumeric character — so Markdown furniture (``---``, ``|``, ``**``) does
not inflate the totals. Reading time is words / 250 wpm, matching the
convention the previous metrics.md used.

Determinism
-----------
Output is a pure function of the corpus: no timestamp, no locale, no network.
That is what makes ``--check`` meaningful — it can tell "metrics.md is stale"
apart from "metrics.md was regenerated a second later". A timestamp header
would make every run a diff.

``--check`` is deliberately **not** wired into Content CI. The manifest is a
consumed contract, so drift there is a build break; metrics.md is
informational, and failing a content PR for an unrefreshed word count would
be friction without a payoff. Run it in CI only if that trade changes.

Usage::

    python scripts/build_metrics.py            # write markdown/meta/metrics.md
    python scripts/build_metrics.py --check    # verify the committed file is current
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"
MANIFEST_PATH = REPO_ROOT / "manifest.json"
METRICS_PATH = MARKDOWN_DIR / "meta" / "metrics.md"

WORDS_PER_MINUTE = 250
WORDS_PER_PAGE = 250

FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)
FENCE_RE = re.compile(r"^(```|~~~)")
HEADING_RE = re.compile(r"^(#{2,6})\s+\S")
ALNUM_RE = re.compile(r"[0-9A-Za-z]")

# Navigation and scaffolding that duplicate chapter content (see docstring).
UNCOUNTED_NAMES = {"README.md", "00-table-of-contents.md"}
UNCOUNTED_DIRS = {"backup", "meta", "images", ".obsidian"}

# Recurring vocabulary worth tracking release over release. Matched
# case-insensitively on word boundaries over chapter bodies.
KEY_TERMS = [
    "practice",
    "meditation",
    "awareness",
    "self",
    "energy",
    "wavelength",
    "habit",
    "body",
]


class MetricsError(Exception):
    """A corpus problem that must abort generation."""


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub("", text, count=1)


def strip_code_fences(lines: list[str]) -> list[str]:
    """Drop fenced code blocks — they are markup, not prose."""
    out, in_fence = [], False
    for line in lines:
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return out


def count_words(lines: list[str]) -> int:
    """Whitespace tokens carrying at least one alphanumeric character."""
    return sum(1 for line in lines for tok in line.split() if ALNUM_RE.search(tok))


def count_headings(lines: list[str]) -> int:
    return sum(1 for line in lines if HEADING_RE.match(line))


def measure(path: Path) -> dict:
    """Word/line/character/heading counts for one Markdown file."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:  # manifest points at a file that is gone
        raise MetricsError(f"{rel(path)}: listed in manifest.json but missing") from exc
    body = strip_frontmatter(raw)
    lines = body.splitlines()
    prose = strip_code_fences(lines)
    return {
        "words": count_words(prose),
        "lines": len(lines),
        "chars": len(body),
        "headings": count_headings(prose),
        "prose": prose,
    }


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def reading_minutes(words: int) -> int:
    return max(1, round(words / WORDS_PER_MINUTE)) if words else 0


def humanize_minutes(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    if not hours:
        return f"{mins} minutes"
    return f"{hours} hours, {mins} minutes"


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise MetricsError(
            "manifest.json not found — run scripts/build_manifest.py first"
        )
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetricsError(f"manifest.json is not valid JSON: {exc}") from exc


def stage_label(chapter_path: str) -> tuple[str, str]:
    """('01-beige', 'BEIGE') from 'markdown/01-beige/01-what-is-beige.md'."""
    folder = chapter_path.split("/")[1]
    return folder, folder.split("-", 1)[1].upper()


def collect(manifest: dict) -> tuple[list[dict], list[dict]]:
    """Measure every indexed chapter and site resource."""
    chapters = []
    for entry in manifest.get("chapters", []):
        path = REPO_ROOT / entry["path"]
        stats = measure(path)
        folder, name = stage_label(entry["path"])
        chapters.append({**entry, **stats, "folder": folder, "stage_name": name})

    resources = []
    for entry in manifest.get("site_resources", []):
        stats = measure(REPO_ROOT / entry["path"])
        resources.append({**entry, **stats})

    if not chapters:
        raise MetricsError("manifest.json lists no chapters — nothing to measure")
    return chapters, resources


def group_by_stage(chapters: list[dict]) -> list[dict]:
    stages: dict[int, dict] = {}
    for c in chapters:
        s = stages.setdefault(
            c["stage"],
            {
                "stage": c["stage"],
                "name": c["stage_name"],
                "chapters": 0,
                "words": 0,
                "headings": 0,
            },
        )
        s["chapters"] += 1
        s["words"] += c["words"]
        s["headings"] += c["headings"]
    return [stages[k] for k in sorted(stages)]


def find_unindexed(manifest: dict) -> list[str]:
    """Markdown under markdown/ that is neither indexed nor known scaffolding."""
    indexed = {e["path"] for e in manifest.get("chapters", [])}
    indexed |= {e["path"] for e in manifest.get("site_resources", [])}
    loose = []
    for path in sorted(MARKDOWN_DIR.rglob("*.md")):
        parts = path.relative_to(MARKDOWN_DIR).parts
        if set(parts[:-1]) & UNCOUNTED_DIRS or path.name in UNCOUNTED_NAMES:
            continue
        if rel(path) not in indexed:
            loose.append(rel(path))
    return loose


def count_term(term: str, chapters: list[dict]) -> int:
    pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
    return sum(len(pattern.findall(line)) for c in chapters for line in c["prose"])


def table(headers: list[str], aligns: list[str], rows: list[list[str]]) -> list[str]:
    sep = {"l": "---", "r": "---:", "c": ":---:"}
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(sep[a] for a in aligns) + "|")
    out.extend("| " + " | ".join(r) + " |" for r in rows)
    return out


def render(manifest: dict, chapters: list[dict], resources: list[dict]) -> str:
    stages = group_by_stage(chapters)
    stage_words = sum(s["words"] for s in stages)
    resource_words = sum(r["words"] for r in resources)
    total_words = stage_words + resource_words
    total_lines = sum(c["lines"] for c in chapters) + sum(r["lines"] for r in resources)
    total_chars = sum(c["chars"] for c in chapters) + sum(r["chars"] for r in resources)
    total_files = len(chapters) + len(resources)

    L: list[str] = []
    L.append("# APTITUDE Course - Comprehensive Statistics")
    L.append("")
    L.append(
        "_Generated by `scripts/build_metrics.py` from `manifest.json` — "
        "do not edit by hand._"
    )
    L.append("")
    L.append("---")
    L.append("")

    L.append("## 📊 Overview")
    L.append("")
    L.append(f"- **Indexed Files**: {total_files} ({len(chapters)} chapters, "
             f"{len(resources)} site resources)")
    L.append(f"- **Total Words**: {total_words:,}")
    L.append(f"- **Total Lines**: {total_lines:,}")
    L.append(f"- **Total Characters**: {total_chars:,}")
    L.append(
        f"- **Reading Time**: ~{reading_minutes(total_words)} minutes "
        f"(~{humanize_minutes(reading_minutes(total_words))} at "
        f"{WORDS_PER_MINUTE} wpm)"
    )
    L.append(
        f"- **Book Equivalent**: ~{round(total_words / WORDS_PER_PAGE):,} pages "
        f"({WORDS_PER_PAGE} words/page)"
    )
    L.append(f"- **Manifest Schema**: `{manifest.get('schema_version', 'unknown')}`")
    L.append("")
    L.append("---")
    L.append("")

    L.append("## 📚 Stage-by-Stage Breakdown")
    L.append("")
    L.extend(
        table(
            ["Stage", "Name", "Chapters", "Words", "Avg/Chapter", "Reading Time"],
            ["l", "l", "r", "r", "r", "r"],
            [
                [
                    f"Stage {s['stage']}",
                    s["name"],
                    f"{s['chapters']}",
                    f"{s['words']:,}",
                    f"{round(s['words'] / s['chapters']):,}",
                    f"~{reading_minutes(s['words'])} min",
                ]
                for s in stages
            ],
        )
    )
    L.append("")
    L.append("**Stage Summary:**")
    L.append("")
    L.append(f"- Total Stage Content: {stage_words:,} words")
    L.append(f"- Average per Stage: {round(stage_words / len(stages)):,} words")
    L.append(f"- Average per Chapter: {round(stage_words / len(chapters)):,} words")
    L.append(f"- Total Reading Time (Stages): ~{reading_minutes(stage_words)} minutes")
    L.append("")
    L.append("---")
    L.append("")

    L.append("## 📖 Supporting Materials")
    L.append("")
    L.extend(
        table(
            ["Document", "Words", "Lines", "Reading Time"],
            ["l", "r", "r", "r"],
            [
                [
                    r["title"],
                    f"{r['words']:,}",
                    f"{r['lines']:,}",
                    f"~{reading_minutes(r['words'])} min",
                ]
                for r in sorted(resources, key=lambda r: r["slug"])
            ],
        )
    )
    L.append("")
    L.append("---")
    L.append("")

    L.append("## 🎯 Depth Analysis")
    L.append("")
    ranked = sorted(chapters, key=lambda c: (-c["words"], c["path"]))
    L.append("**Longest chapters:**")
    L.append("")
    for c in ranked[:5]:
        L.append(f"- {c['stage_name']} · {c['title']} — {c['words']:,} words")
    L.append("")
    L.append("**Shortest chapters:**")
    L.append("")
    for c in reversed(ranked[-5:]):
        L.append(f"- {c['stage_name']} · {c['title']} — {c['words']:,} words")
    L.append("")
    by_words = sorted(stages, key=lambda s: (-s["words"], s["stage"]))
    L.append(
        f"**Widest spread:** {by_words[0]['name']} ({by_words[0]['words']:,} words) "
        f"vs. {by_words[-1]['name']} ({by_words[-1]['words']:,} words) — a "
        f"{by_words[0]['words'] - by_words[-1]['words']:,}-word gap."
    )
    L.append("")
    L.append("---")
    L.append("")

    L.append("## 🔍 Content Richness")
    L.append("")
    L.append("**Headings (`##` and deeper) per stage:**")
    L.append("")
    for s in stages:
        L.append(f"- {s['name']}: {s['headings']} headings across "
                 f"{s['chapters']} chapters")
    L.append("")
    L.append("**Key practice terms (across all chapters):**")
    L.append("")
    for term in KEY_TERMS:
        L.append(f'- "{term}": {count_term(term, chapters):,} mentions')
    L.append("")
    L.append("---")
    L.append("")

    L.append("## 🎓 Course Completion Metrics")
    L.append("")
    L.append("**If you read everything:**")
    L.append("")
    L.append(
        f"- **Total Time Investment**: ~{humanize_minutes(reading_minutes(total_words))} "
        "of reading"
    )
    L.append(f"- **Stages**: {len(stages)}, {len(chapters)} chapters in total")
    L.append("- **Plus Practice Time**: daily practice, 1-45 minutes/day")
    L.append("- **Total Course Duration**: 9 months")
    L.append("")

    loose = find_unindexed(manifest)
    if loose:
        L.append("---")
        L.append("")
        L.append("## ⚠️ Unindexed Files")
        L.append("")
        L.append(
            "Present under `markdown/` but absent from `manifest.json`, so **not "
            "counted above** and not published to the app:"
        )
        L.append("")
        for path in loose:
            L.append(f"- `{path}`")
        L.append("")

    L.append("---")
    L.append("")
    L.append(
        "_Counts cover chapter bodies only: frontmatter and fenced code are "
        "excluded, as are stage `README.md` and `00-table-of-contents.md` "
        f"navigation files. Reading time assumes {WORDS_PER_MINUTE} wpm._"
    )
    L.append("")
    L.append('_"The practice IS the path."_')
    L.append("")
    return "\n".join(L)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed metrics.md matches a fresh build (exit 1 if not)",
    )
    args = parser.parse_args()

    try:
        manifest = load_manifest()
        chapters, resources = collect(manifest)
        rendered = render(manifest, chapters, resources)
    except MetricsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.check:
        if not METRICS_PATH.exists():
            print(f"error: {rel(METRICS_PATH)} is missing", file=sys.stderr)
            return 1
        if METRICS_PATH.read_text(encoding="utf-8") != rendered:
            print(
                f"error: {rel(METRICS_PATH)} is out of date — "
                "run python scripts/build_metrics.py",
                file=sys.stderr,
            )
            return 1
        print(f"{rel(METRICS_PATH)} is current")
        return 0

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(rendered, encoding="utf-8")
    total = sum(c["words"] for c in chapters) + sum(r["words"] for r in resources)
    print(
        f"wrote {rel(METRICS_PATH)} "
        f"({len(chapters)} chapters, {len(resources)} resources, {total:,} words)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
