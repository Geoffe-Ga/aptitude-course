# Content Format Specification

> **Status:** canonical · **Issue:** [#17](https://github.com/Geoffe-Ga/aptitude-course/issues/17) · **Epic:** [adepthood#388](https://github.com/Geoffe-Ga/adepthood/issues/388)
>
> This document defines the contract that the Adepthood app consumes. It is the
> single source of truth for **(1)** the Markdown dialect every chapter is
> written in and **(2)** the YAML frontmatter schema that makes the corpus
> machine-readable. The fields here are aligned field-for-field with the app's
> manifest contract defined in
> [adepthood#389](https://github.com/Geoffe-Ga/adepthood/issues/389)
> (`backend/content/manifest.schema.json`). **Any change to the fields or their
> types is a versioned, breaking change** that must be coordinated with
> adepthood#389 and reflected in `schema_version` (see
> [CONSUMPTION.md](./CONSUMPTION.md), issue #22).

This is a **specification only**. It does not edit the existing chapters — that
is the job of issue [#18](https://github.com/Geoffe-Ga/aptitude-course/issues/18)
(normalize bodies) and issue
[#19](https://github.com/Geoffe-Ga/aptitude-course/issues/19) (add frontmatter).

---

## 1. Why this exists

Today this repository holds **219 chapter files** under
`markdown/<NN-stage>/<NN-slug>.md` across 10 stages
(`01-beige` … `10-clearlight`), converted from Google Docs. They carry inline
HTML (spans, styled tables, `&nbsp;`, font/anchor cruft), have **no
frontmatter**, and there is **no machine-readable index**. The Adepthood app
cannot reliably parse this.

The target pipeline is:

```
markdown/<NN-stage>/<NN-slug>.md   (clean Markdown + YAML frontmatter)
        │
        ▼  scripts/build_manifest.py  (issue #20)
manifest.json                      (generated, schema-versioned contract)
        │
        ▼  vendored at a pinned SHA into adepthood backend/content/
Adepthood app renders Markdown natively
```

Files stay the source of truth; the manifest is **generated** from their
frontmatter so it never drifts by hand.

---

## 2. The Markdown dialect

Chapter and resource **bodies** are **[CommonMark](https://commonmark.org/)**
with a small, safe, widely-portable feature set. The app renders Markdown
natively (e.g. `react-native-markdown-display`) and **does not execute HTML**.

### 2.1 Allowed

| Feature | Notes |
|---------|-------|
| Headings | ATX style (`#`, `##`, …). See §2.3 for level rules. |
| Paragraphs & line breaks | Blank line between blocks. |
| Emphasis | `*italic*`, `**bold**`. |
| Lists | Ordered (`1.`) and unordered (`-`). Nested via indentation. |
| Links | `[text](url)` — `https://`, `mailto:`, or repo-relative paths. |
| Images | `![alt](path)` — repo-relative paths preferred (see §6). |
| Blockquotes | `>` — used heavily for the literary quotes in the corpus. |
| Code | Inline `` `code` `` and fenced ```` ``` ```` blocks. |
| Tables | GitHub-Flavored Markdown pipe tables. |
| Thematic breaks | `---` on its own line. |

### 2.2 Disallowed

- **Raw HTML of any kind** in the body — no `<span>`, `<div>`, `<table>`,
  `<br>`, `<font>`, `<col>`, inline `style=` attributes, etc. CI (issue #21)
  enforces a "no raw HTML" rule.
- **HTML entities** where a literal character will do: write `&` not `&amp;`,
  a real space not `&nbsp;`, straight or curly quotes directly rather than
  `&quot;`/`&#39;`.
- **Embedded scripts/iframes** — video is referenced via frontmatter `media[]`
  (see §6), never inline.

### 2.3 Heading levels

- The chapter **title lives in frontmatter** (`title:`), not implicitly in the
  body.
- A body **may** open with a single `#` (H1) that repeats the title. If present
  there must be **exactly one** H1.
- Section headings within the body start at `##` (H2) and nest downward
  (`###`, `####`). Do not skip levels.

> Note: the legacy corpus currently opens most sections at `##` with no H1.
> Normalization (issue #18) reconciles this; this spec defines the target.

---

## 3. Frontmatter schema

Every chapter file **must** begin with a YAML frontmatter block delimited by
`---` lines, before any body content.

```yaml
---
id: beige-1                 # stable, unique across the whole repo
stage: 1                    # 1..10 (archetype index)
chapter: 1                  # 1-based position within the stage
order: 1                    # display order within the stage
slug: what-is-beige         # URL-safe; matches the filename slug
title: "What Is Beige?"     # human title (quote if it contains : or ?)
content_type: chapter       # chapter | essay | prompt | video
release_day: 0              # days after stage start; 0 = unlocks immediately
summary: "One-line teaser." # optional
media: []                   # optional; see §6 and issue #25
---
```

### 3.1 Field reference

| Field | Type | Required | Rule |
|-------|------|----------|------|
| `id` | string | yes | Stable, unique repo-wide. Format `"<stage-slug>-<chapter>"`, e.g. `beige-1`, `clearlight-3`. Never reuse or renumber once shipped. |
| `stage` | integer | yes | `1`–`10`, the archetype index (see §4). |
| `chapter` | integer | yes | `1`-based position within the stage. `(stage, chapter)` is unique repo-wide. |
| `order` | integer | yes | Display order within the stage. Usually equals `chapter`; kept separate so display order can change without breaking identity. |
| `slug` | string | yes | URL-safe (`[a-z0-9-]+`). **Must match the filename slug** (the part after the `NN-` numeric prefix). |
| `title` | string | yes | Human-readable. Quote in YAML if it contains `:`, `?`, `#`, or leading punctuation. |
| `content_type` | enum | yes | One of `chapter`, `essay`, `prompt`, `video` (see §5). |
| `release_day` | integer | yes | `≥ 0`. Days after the stage starts that this item unlocks (see §5.2). |
| `summary` | string | no | One-line teaser. Omit rather than leave empty. |
| `media` | array | no | Non-inline media references; see §6. Defaults to `[]`. |

Types and field **names** match adepthood#389's `manifest.schema.json` exactly.
The manifest generator (issue #20) adds the file's relative `path`; authors do
not write `path` in frontmatter.

### 3.2 Identity & uniqueness rules

1. **`id` is unique** across the entire repository and never changes once
   shipped (the app keys reads on it).
2. **`(stage, chapter)` is unique** across the repository.
3. **`slug` matches the filename slug.** For
   `markdown/01-beige/01-what-is-beige.md`, the filename slug is
   `what-is-beige`, so `slug: what-is-beige`.
4. `stage`/`chapter`/`order`/`slug` are **derived mechanically** from the
   existing `<NN-stage>/<NN-slug>.md` folder + filename convention (issue #19),
   so they cannot disagree with the file's location.

These rules are checked by the manifest generator (#20) and enforced by CI
(#21). A violation fails the build.

---

## 4. Stage-numbering reconciliation

The content repo numbers stages **1–10 by archetype**:

| `stage` | Folder | Archetype |
|---------|--------|-----------|
| 1 | `01-beige` | Beige — Survival |
| 2 | `02-purple` | Purple — Mythic |
| 3 | `03-red` | Red — Power |
| 4 | `04-blue` | Blue — Conformity |
| 5 | `05-orange` | Orange — Rationality |
| 6 | `06-green` | Green — Plurality |
| 7 | `07-yellow` | Yellow — Integrative |
| 8 | `08-teal` | Teal — True Self |
| 9 | `09-ultraviolet` | Ultraviolet — Unity |
| 10 | `10-clearlight` | Clear Light — Emptiness |

The Adepthood app runs a **36-week** program and uses its own `1..36` stage
model. **The mapping from content `stage` (1–10) onto the app's week/stage
model is owned by the app** (adepthood#392 seed + adepthood#389 architecture),
**not** by this repo. The content side authors only:

- `stage` = the archetype index `1..10`, and
- `release_day` = the offset **within that stage's window** (see §5.2).

This repo makes **no assumption** about how many calendar weeks a stage spans or
where it falls in the 36-week schedule. That keeps content authoring decoupled
from the app's gating model (which is out of scope per the epic's guardrail).

---

## 5. `content_type` and `release_day` semantics

### 5.1 `content_type`

| Value | Meaning |
|-------|---------|
| `chapter` | Standard teaching section of a stage (the default; the vast majority of files). |
| `essay` | Standalone long-form piece, including the non-stage-gated site resources (issue #23). |
| `prompt` | A journaling/practice prompt presented as its own item. |
| `video` | An item whose primary payload is a video referenced via `media[]` (§6). |

When in doubt, use `chapter`. Site-resource pages use `essay` and carry **no**
`stage`/`release_day` (they are not stage-gated — see issue #23).

### 5.2 `release_day`

`release_day` is the number of days **after a stage begins** that an item
becomes available, mirroring today's drip-feed behavior
(`PLAN_DURATION_DAYS = 21` per stage in the app).

- `release_day: 0` → unlocks immediately when the stage starts.
- Default authoring pattern (**"daily"**): chapter `n` (1-based) →
  `release_day = n - 1`. So chapter 1 → day 0, chapter 2 → day 1, …
- If a stage ships fewer chapters than its window length, the remaining days
  are a catch-up window with no new reading.
- Authors may deviate from the daily default where the curriculum intends a
  different cadence (e.g. front-loaded or weekly); `release_day` is the single
  authored knob.

`release_day` is **authored by a human** (issue #19), not derived — it encodes
curricular intent, unlike `stage`/`chapter`/`order`/`slug` which are mechanical.

---

## 6. Media & assets (summary)

> The full convention is specified in issue
> [#25](https://github.com/Geoffe-Ga/aptitude-course/issues/25) and will be
> expanded in this section. The contract below is the agreed shape.

- **Images** are committed in-repo under `markdown/<NN-stage>/assets/` and
  referenced with **repo-relative paths** in Markdown
  (`![alt](assets/diagram.png)`), so they vendor into the app image with the
  content — no runtime network fetch.
- **Video / large media** is referenced from frontmatter `media[]` rather than
  embedded inline:

  ```yaml
  media:
    - type: video           # video | image | audio
      url: https://cdn.example.com/beige-intro.mp4
      poster: assets/beige-intro-poster.png   # optional
      caption: "Beige introduction"            # optional
  ```

- The manifest generator (#20) validates `media[]`; the CI link-check (#21)
  verifies repo-relative asset paths resolve.

---

## 7. Worked example (end to end)

**File:** `markdown/01-beige/01-what-is-beige.md`

```markdown
---
id: beige-1
stage: 1
chapter: 1
order: 1
slug: what-is-beige
title: "What Is Beige?"
content_type: chapter
release_day: 0
summary: "The automatic survival mode beneath civil society's thin veneer."
media: []
---

# What Is Beige?

About the automatic, reactionary survival mode upon which civil society is a
thin veneer, fantasy author Patrick Rothfuss paints the following scene.

> Then someone touched me on the shoulder. I jumped fully two feet into the air
> and narrowly avoided falling on Simmon in the howling, scratching, biting
> blur that had been my only method of defense in Tarbean.

— Patrick Rothfuss, *The Name of the Wind*

Beige relates to the aspect of our identity that deals with making sure we have
something to eat, we're watered, and the people around us won't slit our
throats in our sleep.
```

**What the generator (#20) emits for this file in `manifest.json`:**

```json
{
  "id": "beige-1",
  "stage": 1,
  "chapter": 1,
  "order": 1,
  "slug": "what-is-beige",
  "title": "What Is Beige?",
  "content_type": "chapter",
  "release_day": 0,
  "summary": "The automatic survival mode beneath civil society's thin veneer.",
  "media": [],
  "path": "markdown/01-beige/01-what-is-beige.md"
}
```

---

## 8. Change control

- This spec is a **contract**. Renaming a field, changing a type, or changing
  identity rules requires a `schema_version` bump (semver) coordinated with
  adepthood#389 and documented in [CONSUMPTION.md](./CONSUMPTION.md).
- Additive, optional fields are a **minor** bump. Removing or retyping a field,
  or tightening a rule, is a **major** bump.
- See [CONTRIBUTING.md](./CONTRIBUTING.md) (issue #24) for the day-to-day
  authoring workflow.
