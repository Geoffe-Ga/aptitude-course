# Graph Report - .  (2026-07-17)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 164 nodes · 217 edges · 14 communities (13 shown, 1 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a47daf24`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13

## God Nodes (most connected - your core abstractions)
1. `required` - 11 edges
2. `ManifestError` - 7 edges
3. `build_manifest()` - 7 edges
4. `path` - 6 edges
5. `media_item` - 6 edges
6. `required` - 6 edges
7. `main()` - 6 edges
8. `read_frontmatter()` - 6 edges
9. `rel()` - 6 edges
10. `main()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `rel()`  [INFERRED]
  scripts/normalize_markdown.py → scripts/build_manifest.py

## Import Cycles
- None detected.

## Communities (14 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.10
Nodes (22): properties, type, pattern, type, minimum, type, content_type, id (+14 more)

### Community 1 - "Community 1"
Cohesion: 0.19
Nodes (20): Exception, build_manifest(), collect_chapters(), collect_site_resources(), collect_stage_intros(), main(), ManifestError, Path (+12 more)

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (16): type, type, media_item, additionalProperties, anyOf, properties, required, type (+8 more)

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (16): items, type, $ref, properties, chapters, schema_version, site_resources, stage_intros (+8 more)

### Community 4 - "Community 4"
Cohesion: 0.26
Nodes (12): content_type, id, media, order, path, release_day, slug, stage (+4 more)

### Community 5 - "Community 5"
Cohesion: 0.17
Nodes (12): site_resource, type, items, type, description, media, slug, additionalProperties (+4 more)

### Community 6 - "Community 6"
Cohesion: 0.18
Nodes (10): chapters, schema_version, site_resources, additionalProperties, description, $id, required, $schema (+2 more)

### Community 7 - "Community 7"
Cohesion: 0.20
Nodes (10): audio, chapter, essay, image, prompt, video, enum, type (+2 more)

### Community 8 - "Community 8"
Cohesion: 0.36
Nodes (9): build_frontmatter(), chapter_files(), main(), Path, Numbered section files in display order, excluding the TOC (00-...)., slug_from_filename(), stage_dirs(), title_from_body() (+1 more)

### Community 9 - "Community 9"
Cohesion: 0.29
Nodes (9): corpus_files(), first_divergence(), main(), normalize(), Path, Extract the sequence of visible prose words, ignoring all markup.      Applied i, Human-readable description of where two word lists first differ., Return the clean-Markdown form of ``text`` (word-preserving). (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.22
Nodes (9): additionalProperties, minimum, type, $defs, chapter, stage_intro, chapter, additionalProperties (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.36
Nodes (7): iter_markdown_files(), iter_media_targets(), iter_targets(), main(), Path, Yield (line_number, target) for each inline link/image outside code fences., Yield (label, target) for relative media[] path/poster entries (issue #25).

### Community 12 - "Community 12"
Cohesion: 0.40
Nodes (4): chapters, schema_version, site_resources, stage_intros

## Knowledge Gaps
- **62 isolated node(s):** `convert_docs.sh script`, `schema_version`, `chapters`, `site_resources`, `stage_intros` (+57 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `$defs` connect `Community 10` to `Community 2`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Why does `properties` connect `Community 0` to `Community 10`, `Community 2`, `Community 5`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Why does `chapter` connect `Community 10` to `Community 0`, `Community 4`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **What connects `convert_docs.sh script`, `schema_version`, `chapters` to the rest of the system?**
  _62 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.1038961038961039 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.14166666666666666 - nodes in this community are weakly interconnected._