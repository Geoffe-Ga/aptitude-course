#!/usr/bin/env python3
"""Generate markdown/meta/metrics.md — and the GitHub Pages version of it.

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

Two outputs, one document
-------------------------
The statistics are assembled once into a small block model (headings,
paragraphs, lists, tables) which is then serialized to either Markdown or a
self-contained HTML page. Both formats therefore always say the same thing —
there is no Markdown-to-HTML conversion step to drift, and no third-party
parser to depend on. Adding a section means adding it once.

The HTML page is what ``.github/workflows/metrics-pages.yml`` publishes to
GitHub Pages on every push to ``main``, so the published numbers reflect the
merge that just landed rather than the last time someone remembered to run
this script.

Determinism
-----------
Output is a pure function of the corpus: no timestamp, no locale, no network.
That is what makes ``--check`` meaningful — it can tell "metrics.md is stale"
apart from "metrics.md was regenerated a second later". A timestamp header
would make every run a diff. Build provenance for the published page is
injected by CI through ``--stamp`` instead, so it never touches the committed
Markdown.

``--check`` is deliberately **not** wired into Content CI. The manifest is a
consumed contract, so drift there is a build break; metrics.md is
informational, and failing a content PR for an unrefreshed word count would
be friction without a payoff. Run it in CI only if that trade changes.

Usage::

    python scripts/build_metrics.py                 # write markdown/meta/metrics.md
    python scripts/build_metrics.py --check         # verify the committed file is current
    python scripts/build_metrics.py --html site     # write site/index.html for Pages
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

PAGE_TITLE = "APTITUDE Corpus Statistics"

WORDS_PER_MINUTE = 250
WORDS_PER_PAGE = 250

FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)
FENCE_RE = re.compile(r"^(```|~~~)")
HEADING_RE = re.compile(r"^(#{2,6})\s+\S")
ALNUM_RE = re.compile(r"[0-9A-Za-z]")

# Inline Markdown the block model supports, in the order it is applied.
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
INLINE_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
INLINE_ITALIC_RE = re.compile(r"_([^_]+)_")

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


# --------------------------------------------------------------------------
# Measuring
# --------------------------------------------------------------------------


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


# --------------------------------------------------------------------------
# The document model — built once, serialized twice
# --------------------------------------------------------------------------


def h1(text: str) -> dict:
    return {"kind": "heading", "level": 1, "text": text}


def h2(text: str) -> dict:
    return {"kind": "heading", "level": 2, "text": text}


def para(text: str) -> dict:
    return {"kind": "para", "text": text}


def bullets(items: list[str]) -> dict:
    return {"kind": "list", "items": items}


def rule() -> dict:
    return {"kind": "rule"}


def table(headers: list[str], aligns: list[str], rows: list[list[str]]) -> dict:
    return {"kind": "table", "headers": headers, "aligns": aligns, "rows": rows}


def build_document(
    manifest: dict, chapters: list[dict], resources: list[dict]
) -> list[dict]:
    """Assemble every statistic into format-agnostic blocks."""
    stages = group_by_stage(chapters)
    stage_words = sum(s["words"] for s in stages)
    resource_words = sum(r["words"] for r in resources)
    total_words = stage_words + resource_words
    total_lines = sum(c["lines"] for c in chapters) + sum(r["lines"] for r in resources)
    total_chars = sum(c["chars"] for c in chapters) + sum(r["chars"] for r in resources)
    total_files = len(chapters) + len(resources)
    total_minutes = reading_minutes(total_words)

    doc: list[dict] = [
        h1("APTITUDE Course - Comprehensive Statistics"),
        para(
            "_Generated by `scripts/build_metrics.py` from `manifest.json` — "
            "do not edit by hand._"
        ),
        rule(),
        h2("📊 Overview"),
        bullets(
            [
                f"**Indexed Files**: {total_files} ({len(chapters)} chapters, "
                f"{len(resources)} site resources)",
                f"**Total Words**: {total_words:,}",
                f"**Total Lines**: {total_lines:,}",
                f"**Total Characters**: {total_chars:,}",
                f"**Reading Time**: ~{total_minutes} minutes "
                f"(~{humanize_minutes(total_minutes)} at {WORDS_PER_MINUTE} wpm)",
                f"**Book Equivalent**: ~{round(total_words / WORDS_PER_PAGE):,} pages "
                f"({WORDS_PER_PAGE} words/page)",
                f"**Manifest Schema**: `{manifest.get('schema_version', 'unknown')}`",
            ]
        ),
        rule(),
        h2("📚 Stage-by-Stage Breakdown"),
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
        ),
        para("**Stage Summary:**"),
        bullets(
            [
                f"Total Stage Content: {stage_words:,} words",
                f"Average per Stage: {round(stage_words / len(stages)):,} words",
                f"Average per Chapter: {round(stage_words / len(chapters)):,} words",
                f"Total Reading Time (Stages): ~{reading_minutes(stage_words)} minutes",
            ]
        ),
        rule(),
        h2("📖 Supporting Materials"),
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
        ),
        rule(),
        h2("🎯 Depth Analysis"),
    ]

    ranked = sorted(chapters, key=lambda c: (-c["words"], c["path"]))
    doc.append(para("**Longest chapters:**"))
    doc.append(
        bullets(
            [
                f"{c['stage_name']} · {c['title']} — {c['words']:,} words"
                for c in ranked[:5]
            ]
        )
    )
    doc.append(para("**Shortest chapters:**"))
    doc.append(
        bullets(
            [
                f"{c['stage_name']} · {c['title']} — {c['words']:,} words"
                for c in reversed(ranked[-5:])
            ]
        )
    )
    by_words = sorted(stages, key=lambda s: (-s["words"], s["stage"]))
    doc.append(
        para(
            f"**Widest spread:** {by_words[0]['name']} "
            f"({by_words[0]['words']:,} words) vs. {by_words[-1]['name']} "
            f"({by_words[-1]['words']:,} words) — a "
            f"{by_words[0]['words'] - by_words[-1]['words']:,}-word gap."
        )
    )

    doc.append(rule())
    doc.append(h2("🔍 Content Richness"))
    doc.append(para("**Headings (`##` and deeper) per stage:**"))
    doc.append(
        bullets(
            [
                f"{s['name']}: {s['headings']} headings across "
                f"{s['chapters']} chapters"
                for s in stages
            ]
        )
    )
    doc.append(para("**Key practice terms (across all chapters):**"))
    doc.append(
        bullets(
            [f'"{term}": {count_term(term, chapters):,} mentions' for term in KEY_TERMS]
        )
    )

    doc.append(rule())
    doc.append(h2("🎓 Course Completion Metrics"))
    doc.append(para("**If you read everything:**"))
    doc.append(
        bullets(
            [
                f"**Total Time Investment**: ~{humanize_minutes(total_minutes)} "
                "of reading",
                f"**Stages**: {len(stages)}, {len(chapters)} chapters in total",
                "**Plus Practice Time**: daily practice, 1-45 minutes/day",
                "**Total Course Duration**: 9 months",
            ]
        )
    )

    loose = find_unindexed(manifest)
    if loose:
        doc.append(rule())
        doc.append(h2("⚠️ Unindexed Files"))
        doc.append(
            para(
                "Present under `markdown/` but absent from `manifest.json`, so "
                "**not counted above** and not published to the app:"
            )
        )
        doc.append(bullets([f"`{p}`" for p in loose]))

    doc.append(rule())
    doc.append(
        para(
            "_Counts cover chapter bodies only: frontmatter and fenced code are "
            "excluded, as are stage `README.md` and `00-table-of-contents.md` "
            f"navigation files. Reading time assumes {WORDS_PER_MINUTE} wpm._"
        )
    )
    doc.append(para('_"The practice IS the path."_'))
    return doc


# --------------------------------------------------------------------------
# Serializers
# --------------------------------------------------------------------------


def render_markdown(doc: list[dict]) -> str:
    lines: list[str] = []
    for block in doc:
        kind = block["kind"]
        if kind == "heading":
            lines.append(f"{'#' * block['level']} {block['text']}")
        elif kind == "para":
            lines.append(block["text"])
        elif kind == "list":
            lines.extend(f"- {item}" for item in block["items"])
        elif kind == "rule":
            lines.append("---")
        elif kind == "table":
            sep = {"l": "---", "r": "---:", "c": ":---:"}
            lines.append("| " + " | ".join(block["headers"]) + " |")
            lines.append("|" + "|".join(sep[a] for a in block["aligns"]) + "|")
            lines.extend("| " + " | ".join(row) + " |" for row in block["rows"])
        lines.append("")
    return "\n".join(lines)


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline_html(text: str) -> str:
    """Render the inline Markdown subset the document model uses.

    Code spans are stashed before emphasis is applied and restored after, so
    that punctuation *inside* code is never read as a delimiter — otherwise
    the underscore in ``build_metrics.py`` closes an italic run and the tags
    interleave.
    """
    out = escape_html(text)
    spans: list[str] = []

    def stash(match: re.Match[str]) -> str:
        spans.append(match.group(1))
        return f"\x00{len(spans) - 1}\x00"

    out = INLINE_CODE_RE.sub(stash, out)
    out = INLINE_BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = INLINE_ITALIC_RE.sub(r"<em>\1</em>", out)
    for index, code in enumerate(spans):
        out = out.replace(f"\x00{index}\x00", f"<code>{code}</code>")
    return out


PAGE_CSS = """\
:root {
  color-scheme: light dark;
  --bg: #fbfaf8;
  --surface: #ffffff;
  --text: #1c1b19;
  --muted: #5f5b54;
  --border: #e2ded7;
  --accent: #6b4fa0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16151a;
    --surface: #1e1d24;
    --text: #ece9f0;
    --muted: #a19cad;
    --border: #34313d;
    --accent: #b9a2e8;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 2.5rem 1.25rem 4rem;
  background: var(--bg);
  color: var(--text);
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
main { max-width: 52rem; margin: 0 auto; }
h1 {
  font-size: 1.9rem;
  line-height: 1.2;
  margin: 0 0 .5rem;
  letter-spacing: -0.01em;
}
h2 {
  font-size: 1.2rem;
  margin: 2.5rem 0 .75rem;
  padding-bottom: .4rem;
  border-bottom: 1px solid var(--border);
}
p { margin: .75rem 0; }
ul { margin: .75rem 0; padding-left: 1.25rem; }
li { margin: .3rem 0; }
hr { display: none; }
code {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: .1em .35em;
  font-size: .875em;
}
em { color: var(--muted); font-style: normal; }
.table-wrap { overflow-x: auto; margin: 1rem 0; }
table {
  border-collapse: collapse;
  width: 100%;
  min-width: 32rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
}
th, td { padding: .55rem .75rem; border-bottom: 1px solid var(--border); }
th {
  text-align: left;
  font-size: .8rem;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: var(--muted);
}
tbody tr:last-child td { border-bottom: none; }
td.r, th.r { text-align: right; font-variant-numeric: tabular-nums; }
td.c, th.c { text-align: center; }
.stamp {
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: .85rem;
}
.stamp a { color: var(--accent); }
"""


def render_html(doc: list[dict], stamp: str | None = None) -> str:
    body: list[str] = []
    pending: list[str] = []  # consecutive list blocks merge into one <ul>

    def flush() -> None:
        if pending:
            body.append("<ul>")
            body.extend(pending)
            body.append("</ul>")
            pending.clear()

    for block in doc:
        kind = block["kind"]
        if kind == "list":
            pending.extend(f"<li>{inline_html(i)}</li>" for i in block["items"])
            continue
        flush()
        if kind == "heading":
            level = block["level"]
            body.append(f"<h{level}>{inline_html(block['text'])}</h{level}>")
        elif kind == "para":
            body.append(f"<p>{inline_html(block['text'])}</p>")
        elif kind == "rule":
            body.append("<hr>")
        elif kind == "table":
            aligns = block["aligns"]
            body.append('<div class="table-wrap">')
            body.append("<table>")
            head = "".join(
                f'<th class="{a}">{inline_html(h)}</th>'
                for h, a in zip(block["headers"], aligns)
            )
            body.append(f"<thead><tr>{head}</tr></thead>")
            body.append("<tbody>")
            for row in block["rows"]:
                cells = "".join(
                    f'<td class="{a}">{inline_html(c)}</td>'
                    for c, a in zip(row, aligns)
                )
                body.append(f"<tr>{cells}</tr>")
            body.append("</tbody></table></div>")
    flush()

    if stamp:
        body.append(
            f'<p class="stamp">{escape_html(stamp)}</p>'
        )

    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape_html(PAGE_TITLE)}</title>\n"
        f"<style>\n{PAGE_CSS}</style>\n"
        "</head>\n"
        "<body>\n<main>\n"
        + "\n".join(body)
        + "\n</main>\n</body>\n</html>\n"
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed metrics.md matches a fresh build (exit 1 if not)",
    )
    parser.add_argument(
        "--html",
        metavar="DIR",
        help="write DIR/index.html (the GitHub Pages build) instead of metrics.md",
    )
    parser.add_argument(
        "--stamp",
        metavar="TEXT",
        help="provenance line for the HTML page (CI passes the commit); "
        "never written into the Markdown, which stays deterministic",
    )
    args = parser.parse_args()

    if args.check and args.html:
        print("error: --check and --html are mutually exclusive", file=sys.stderr)
        return 2

    try:
        manifest = load_manifest()
        chapters, resources = collect(manifest)
        doc = build_document(manifest, chapters, resources)
    except MetricsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.html:
        out_dir = Path(args.html)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "index.html"
        out_path.write_text(render_html(doc, args.stamp), encoding="utf-8")
        print(f"wrote {out_path}")
        return 0

    rendered = render_markdown(doc)

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
