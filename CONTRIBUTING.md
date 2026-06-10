# Contributing to the APTITUDE Course Corpus

> **Issue:** [#24](https://github.com/Geoffe-Ga/aptitude-course/issues/24) · **Epic:** [adepthood#388](https://github.com/Geoffe-Ga/adepthood/issues/388)
>
> This is the day-to-day authoring guide. The underlying contracts live in
> [CONTENT_FORMAT.md](./CONTENT_FORMAT.md) (Markdown dialect + frontmatter
> schema) and [CONSUMPTION.md](./CONSUMPTION.md) (what the app consumes and
> how releases ship). If those documents and this one ever disagree, they win
> — and please open an issue.

The corpus is plain Markdown under `markdown/`, indexed by a generated
`manifest.json` that the Adepthood app consumes at a pinned commit. Every
change must keep CI green; CI is what guarantees a broken chapter never
reaches the app.

---

## 1. Setup

```bash
pip install -r scripts/requirements.txt   # PyYAML + jsonschema
```

The three CI checks, runnable locally:

```bash
python scripts/build_manifest.py --check   # frontmatter + manifest drift
python scripts/check_links.py              # internal links/images/media[] resolve
npx markdownlint-cli2                      # dialect rules (no raw HTML, …)
```

Run all three before pushing and CI will pass on the first try.

---

## 2. Add a chapter

1. **Create the file** at `markdown/<NN-stage>/<NN-slug>.md`, where
   `<NN-stage>` is one of the ten stage directories (`01-beige` …
   `10-clearlight`) and `NN` is the next two-digit chapter number in that
   stage. The filename slug becomes the frontmatter `slug`.

2. **Add frontmatter** (full field reference: CONTENT_FORMAT.md §3):

   ```yaml
   ---
   id: beige-20                # "<stage-slug>-<chapter>", unique forever
   stage: 1                    # 1..10 — must match the directory
   chapter: 20                 # 1-based position in the stage
   order: 20                   # display order; usually equals chapter
   slug: my-new-chapter        # must equal the filename slug
   title: "My New Chapter"
   content_type: chapter       # chapter | essay | prompt | video (§3 below)
   release_day: 19             # days after the stage starts (§4 below)
   summary: "One-line teaser." # optional
   media: []                   # optional; CONTENT_FORMAT.md §6
   ---
   ```

3. **Write the body** in CommonMark (CONTENT_FORMAT.md §2): no raw HTML, no
   HTML entities, headings start at `##`, images via relative paths
   (`assets/foo.png` in the stage's `assets/` dir — CONTENT_FORMAT.md §6).

4. **Regenerate the manifest** and commit both the chapter and the manifest:

   ```bash
   python scripts/build_manifest.py
   git add markdown/<NN-stage>/<NN-slug>.md manifest.json
   ```

   A stale committed `manifest.json` fails CI (drift check).

5. **Open a PR.** CI runs the three checks above; all are required.

## Edit a chapter

Edit the body freely — no manifest rebuild needed unless you touched
frontmatter. If you changed `title`, `summary`, `order`, `release_day`, or
`media`, re-run `python scripts/build_manifest.py` and commit the manifest
with the edit. Never change `id` (see §5).

---

## 3. `content_type`

| Value | Use for |
|-------|---------|
| `chapter` | Standard teaching section — the default, almost everything. |
| `essay` | Standalone long-form piece, including the non-stage-gated pages in `markdown/resources/`. |
| `prompt` | A journaling/practice prompt presented as its own item. |
| `video` | An item whose primary payload is a `media[]` video. |

---

## 4. `release_day` (scheduling a release)

`release_day` is **days after the chapter's stage begins**, the single knob
controlling the in-app drip feed. It is authored by a human — it encodes
curricular intent.

- `release_day: 0` → unlocks the moment the stage starts.
- **Daily default:** chapter `n` → `release_day: n - 1` (chapter 1 on day 0,
  chapter 2 on day 1, …).
- Deviate deliberately: `0, 0, 0, 7, 14` front-loads three chapters and then
  drips weekly. A stage window with no chapter on a given day is simply a
  catch-up day.

This repo says nothing about calendar weeks — how stage windows map onto the
36-week program is owned by the app (CONTENT_FORMAT.md §4).

---

## 5. Identity rules (what must never change)

Stage numbering is **1–10 by archetype** (`01-beige` … `10-clearlight`;
table in CONTENT_FORMAT.md §4). On top of that:

1. **`id` is forever.** Unique repo-wide, never reused or renumbered once
   shipped — the app keys user progress on it.
2. **`(stage, chapter)` is unique** repo-wide.
3. **`slug` equals the filename slug** (`02-purple/06-the-practice….md` →
   `slug: the-practice…`). Renaming a file means changing its slug — avoid
   renames once a chapter has shipped; if unavoidable, keep `id` identical.

All three are enforced by `build_manifest.py` and CI.

---

## 6. How a change reaches the app

Merging is not deploying. Per [CONSUMPTION.md](./CONSUMPTION.md) §3–4:

```
PR merges → main is CI-green → tag content-vYYYY.MM.DD → adepthood bumps its
pinned SHA (CONTENT_VERSION) → app deploy
```

Cut a tag with `git tag content-v$(date +%Y.%m.%d) && git push origin --tags`.
Until the app bumps its pin, merged content sits safely unreleased.

---

## 7. Editing with Claude (or any agent)

The corpus is designed for direct agent editing — plain Markdown files, a
deterministic generator, and CI that catches every contract violation:

- Point the agent at this file, CONTENT_FORMAT.md, and the authoritative
  CSVs in `google_docs/database_of_course_curriculum/` (stage
  specifications, Rx/OD wavelength terms — see CLAUDE.md).
- After edits, have it run the three §1 commands; they are the same checks
  CI runs, so local green means CI green.
- `CLAUDE.md` carries the editorial voice and structural conventions for
  the curriculum itself.
