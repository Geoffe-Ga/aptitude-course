#!/usr/bin/env python3
"""Normalize HTML-heavy Google-Docs Markdown into the clean CommonMark dialect
defined in CONTENT_FORMAT.md (issue #18).

The corpus was exported from Google Docs and a handful of files still carry
inline HTML: ``<span class="...">`` wrappers (often splitting text mid-word),
empty spans inside headings, ``<a>``/``<img>`` tags, and ``&amp;``/``&nbsp;``
entities. The app renders Markdown natively and disallows raw HTML, so those
bodies must be reduced to clean Markdown.

This is **reformatting, not rewriting**: every visible prose word must survive
untouched. The script therefore reads each file (the in-memory copy), computes
the normalized version, and *asserts that the sequence of visible prose words is
identical before and after*. If a single word would be added or dropped, the
file is left unchanged and the run aborts with a diff of the offending tokens.

Usage::

    python scripts/normalize_markdown.py            # normalize in place
    python scripts/normalize_markdown.py --check     # verify only, write nothing
    python scripts/normalize_markdown.py --stage 02-purple   # limit to one stage
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = REPO_ROOT / "markdown"

# Directories under markdown/ that are NOT part of the published corpus.
EXCLUDED_DIRS = {"backup", "images", "meta", ".obsidian"}

# A file is a normalization candidate only if it actually contains raw HTML or
# HTML entities. This keeps the diff to the files that need it and avoids
# cosmetic whitespace churn on the (already clean) rest of the corpus.
MARKUP_RE = re.compile(r"</?[a-zA-Z][^>]*>|<img\b|&[a-zA-Z]+;|&#[0-9]+;")


# --------------------------------------------------------------------------- #
# Normalization
# --------------------------------------------------------------------------- #
def normalize(text: str) -> str:
    """Return the clean-Markdown form of ``text`` (word-preserving)."""
    # 1. Decode HTML entities (&amp; -> &, &nbsp; -> NBSP, &#39; -> ', ...).
    text = html.unescape(text)
    # Normalize the non-breaking space that &nbsp; decodes to.
    text = text.replace(" ", " ")

    # 2. Unwrap <span ...> ... </span> — keep the inner text, drop the tags.
    #    Span attributes (style="width:624px", class="c5") carry no prose, so
    #    removing them with the empty string rejoins words Google Docs split
    #    mid-token across styling spans (e.g. "T</span><span>he" -> "The").
    text = re.sub(r"</?span[^>]*>", "", text)

    # 3. <a href="URL">TEXT</a>  ->  [TEXT](URL)   (multiline-safe)
    text = re.sub(
        r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>',
        lambda m: f"[{m.group(2).strip()}]({m.group(1)})",
        text,
        flags=re.DOTALL,
    )

    # 4. <img ... src="URL" ...>  ->  ![](URL)
    #    Google-Docs image tags span multiple lines (src on one line, a long
    #    style="width:624.00px; ..." on the next) and some are *unclosed*
    #    (no '>' at all). The tempered ``(?:(?!\n\n)[^>])`` lets the match run
    #    across single newlines up to the closing '>', but never past a blank
    #    line — so an unclosed tag ends at its paragraph break instead of
    #    swallowing the rest of the document.
    img_inner = r"(?:(?!\n\n)[^>])"
    text = re.sub(
        rf'<img\b{img_inner}*?src="([^"]*)"{img_inner}*?(?:/?>|(?=\n\n)|\Z)',
        lambda m: f"![]({m.group(1)})",
        text,
    )

    # 5. Unwrap any other known structural/inline tags (keeps inner text).
    text = re.sub(
        r"</?(?:div|p|br|font|col|colgroup|table|tbody|thead|tr|td|th|"
        r"b|i|u|strong|em|small|sub|sup)[^>]*>",
        "",
        text,
    )

    # 6. A heading whose only content was an image becomes a bare image
    #    (drops the now-meaningless "### " left over from "### <span><img></span>").
    text = re.sub(
        r"(?m)^#{1,6}[ \t]+(!\[[^\]]*\]\([^)]*\))[ \t]*$",
        r"\1",
        text,
    )

    # 7. Drop headings left empty by removed empty spans (e.g. "### ").
    text = re.sub(r"(?m)^#{1,6}[ \t]*$\n?", "", text)

    # 8. Tidy whitespace: strip trailing spaces, collapse 3+ blank lines to 1.
    text = re.sub(r"[ \t]+(?=\n)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


# --------------------------------------------------------------------------- #
# Word-identity verification
# --------------------------------------------------------------------------- #
# Unclosed/multi-line <img ...> (no '>' before the next blank line), matched so
# the verifier's before-baseline drops the same junk the normalizer does.
_IMG_OPEN_RE = re.compile(r"<img\b(?:(?!\n\n)[^>])*?(?:/?>|(?=\n\n)|\Z)")
_TAG_RE = re.compile(r"<[^>]+>")
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)*")


def visible_words(text: str) -> list[str]:
    """Extract the sequence of visible prose words, ignoring all markup.

    Applied identically to the before- and after-text so that any word added
    or dropped by normalization shows up as a difference. URLs, image refs,
    HTML tags (incl. attributes like style="width:624px" and unclosed/multi-line
    <img>), and entity encodings are stripped; link *text* is kept.

    Tags are removed with the *empty* string (not a space) so words Google Docs
    split mid-token across styling spans ("T</span><span>he") collapse back to
    one word ("The"), matching the normalizer. Real word boundaries survive
    because the separating space lives in the text, outside the tags.
    """
    text = html.unescape(text).replace(" ", " ")
    text = _IMG_OPEN_RE.sub("", text)      # drop <img> incl. unclosed/multiline
    text = _TAG_RE.sub("", text)           # drop remaining HTML tags + attrs
    text = _MD_IMAGE_RE.sub("", text)      # drop markdown images (alt + url)
    text = _MD_LINK_RE.sub(r"\1", text)    # markdown links -> link text only
    return _WORD_RE.findall(text)


def first_divergence(a: list[str], b: list[str]) -> str:
    """Human-readable description of where two word lists first differ."""
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            ctx_a = " ".join(a[max(0, i - 3) : i + 4])
            ctx_b = " ".join(b[max(0, i - 3) : i + 4])
            return f"  at word #{i}:\n    before: …{ctx_a}…\n    after : …{ctx_b}…"
    if len(a) != len(b):
        extra, where = (a[len(b):], "before") if len(a) > len(b) else (b[len(a):], "after")
        return f"  {where} has {len(extra)} extra trailing word(s): {extra[:8]}"
    return "  (no divergence found)"


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def corpus_files(stage: str | None) -> list[Path]:
    files: list[Path] = []
    for path in sorted(MARKDOWN_DIR.rglob("*.md")):
        rel_parts = path.relative_to(MARKDOWN_DIR).parts
        if rel_parts[0] in EXCLUDED_DIRS:
            continue
        if stage and not str(path).startswith(str(MARKDOWN_DIR / stage)):
            continue
        files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only; write nothing")
    parser.add_argument("--stage", default=None, help="limit to one stage folder, e.g. 02-purple")
    args = parser.parse_args()

    changed: list[Path] = []
    failures: list[tuple[Path, str]] = []

    for path in corpus_files(args.stage):
        original = path.read_text(encoding="utf-8")
        if not MARKUP_RE.search(original):
            continue  # already clean — no raw HTML or entities to remove
        updated = normalize(original)

        before_words = visible_words(original)
        after_words = visible_words(updated)
        if before_words != after_words:
            failures.append((path, first_divergence(before_words, after_words)))
            continue

        if updated != original:
            changed.append(path)
            if not args.check:
                path.write_text(updated, encoding="utf-8")

    rel = lambda p: p.relative_to(REPO_ROOT)
    if failures:
        print("WORD-IDENTITY CHECK FAILED — no files written:\n", file=sys.stderr)
        for path, detail in failures:
            print(f"✗ {rel(path)}\n{detail}\n", file=sys.stderr)
        return 1

    verb = "would change" if args.check else "changed"
    if changed:
        print(f"{verb} {len(changed)} file(s) (words verified identical):")
        for path in changed:
            print(f"  {rel(path)}")
    else:
        print("All files already clean — nothing to change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
