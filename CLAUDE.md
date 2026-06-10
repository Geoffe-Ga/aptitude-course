# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **APTITUDE Course** repository - a 10-stage, 9-month transformational curriculum teaching developmental psychology, meditation practices, and "vibrational intelligence" through the lens of the Archetypal Wavelength. The course is designed for neurodivergent spiritual seekers ("Liminal Creeps") who struggle with embodiment despite having mystical insights.

**Core acronym:** *Adepthood: Praxis and Theory for Integrating, Tuning, and Unbridling from Determinism Effectively*

**Note on the model:** APTITUDE reframes Wilber/Graves developmental models. Rather than a ladder to climb, the ten stages are like **notes on a musical scale**—you learn to play the right chords for each moment. Wholeness = the ability to express any stage healthily as the situation demands.

## Architecture & Content Structure

### The 10 Stages (Core Content)

Located in `markdown/[1-10].[STAGE_NAME].md`:

1. **BEIGE** - Agency/Survival (Biological Machine)
2. **PURPLE** - Receptivity/Mythic (Archetype Embodier)
3. **RED** - Self-Love/Power (Dominator)
4. **BLUE** - Community Love/Conformity (Victim)
5. **ORANGE** - Intellectual Understanding/Rationality (Status Seeker)
6. **GREEN** - Embodied Understanding/Plurality (Shadow Glorifier)
7. **YELLOW** - Systems Wisdom/Integrative (Despairing Analyst)
8. **TEAL** - Transcendent Wisdom/True Self Connection (True Self Embodier)
9. **ULTRAVIOLET** - Unity Being/Effortless Being (Blissy Adept)
10. **CLEAR LIGHT** - Emptiness Awareness (Whole Adept)

**Key Distinction (Updated Dec 2025):**
- **Teal (Stage 8)** focuses on **True Self Connection** - discovering the eternal Higher Self/Monad that transcends incarnation (NOT witness consciousness or non-duality)
- **Clear Light (Stage 10)** focuses on **Emptiness (śūnyatā)** - recognizing all phenomena are empty of inherent existence (NOT just non-duality)

### Stage File Structure

Each stage file (~11,000-14,000 words) follows this pattern:

- **What is [Stage]?** - Introduction and philosophical framing
- **The Mood of [Stage]** - Core quality (Rx/Medicine) with Integrated/Repressed/Excessive expressions
- **Journaling Prompts** - 4 prompts, 4x/week minimum
- **Relationship to Free Will** - Archetype and developmental view
- **Mode of the Wavelength** - Mode (Inhabit/Express/Collaborate/Integrate/Absorb/Be)
- **The Practice** - Primary meditative/embodied practice with duration
- **Alternatives for [Stage] Practice** - Multiple alternative practices of same duration
- **Default Habit** - Ongoing habit to build during 21-day stage
- **Divine Gender** - Masculine/Feminine archetypal energy
- **Gift** - Healthy capacity unlocked at this stage
- **Shadow** - Pathological expression to watch for
- **Full 6-Phase Wavelength Breakdown** - Rising, Peaking, Withdrawal, Diminishing, Bottoming Out, Restoration (each with Rx and OD)
- **Practicing [Quality] Off the Cushion** - Real-world application

### The Archetypal Wavelength (Central Framework)

A 6-phase sine wave underlying all cycles (emotional, creative, seasonal, etc.):

1. **Rising** - emergence, momentum building
2. **Peaking** - culmination, resonance, flow
3. **Withdrawal** - first decline, introspection
4. **Diminishing** - descent continues, letting go
5. **Bottoming Out** - nadir, fallow state, surrender
6. **Restoration** - renewal, phoenix rising

Each phase has:
- **Rx (Medicine)** - healthy expression
- **OD (Overdose/Toxic)** - pathological expression

**Critical:** Use exact Rx/OD terms from `google_docs/database_of_course_curriculum/The Archetypal Wavelength - Modes of the Wavelength.csv`

### Database Files (Single Source of Truth)

All authoritative stage specifications live in `google_docs/database_of_course_curriculum/`:

1. **APTITUDE Complete Map.csv** - PRIMARY REFERENCE
   - All stage details: categories, aspects, modes, archetypes, practices, habits, journaling prompts
   - Read as table with headers

2. **The Archetypal Wavelength - Modes of the Wavelength.csv** - ESSENTIAL
   - Exact Rx/OD terms for all 6 phases per stage
   - Two sections: Medicine dosages, Toxic dosages

3. **APTITUDE - Alternative Practices.csv**
   - Variable alternatives per stage (read TOP DOWN, rows uncorrelated)
   - All must match stage duration (e.g., 15min for Blue, 45min for Yellow)

4. **APTITUDE - Book Recommendations.csv**
   - Two books per stage to reference

5. **APTITUDE - Quotes.csv**
   - Read HORIZONTALLY (all in a row relate to stage in column A)

6. **The Archetypal Wavelength - Self-Care Strategies.csv**
   - Strategies for each phase when in OD expression

### Supporting Materials

- `markdown/resources/about.md` - Course introduction
- `markdown/resources/aptitude-stages.md` - Overview of all 10 stages
- `markdown/resources/archetypal-wavelength.md` - Wavelength theory
- `markdown/ExtendedInvitation.md` - Enrollment/philosophy
- `markdown/resources/liminal-creep.md` - Target audience definition
- `markdown/meta/metrics.md` - Auto-generated repository statistics

### Content Source Pipeline

```
Google Docs (HTML exports)
  ↓
google_docs/*.html
  ↓ (via convert_docs.sh)
markdown/*.md
```

## Working with This Codebase

### Converting Google Docs to Markdown

```bash
./convert_docs.sh
```

This script:
1. Unzips all `.zip` files in `google_docs/`
2. Converts all `.html` files to GitHub-flavored markdown using Pandoc
3. Extracts images to `markdown/images/`
4. Outputs to `markdown/[filename].md`

**Requires:** Pandoc installed (`brew install pandoc`)

### Generating Statistics

```bash
cd markdown
# Run the metrics generation script (if exists)
# Or regenerate metrics.md from scratch
```

Current stats (Dec 2025):
- **126,680 total words** across 15 documents
- **117,565 words** in the 10 stage files (average ~11,750/stage)
- **~8.5 hours** total reading time
- **~470 minutes** for all 10 stages

### Git Workflow

```bash
# Repository initialized with remote
git remote -v  # origin: https://github.com/Geoffe-Ga/aptitude-course.git

# Standard workflow
git add .
git commit -m "Descriptive message"
git push origin main
```

## Writing & Editing Guidelines

### Core Principles

1. **Stages as chords, not rungs** - All ten stages are like notes on a musical scale; Wholeness emerges from playing the right chords for each moment. You don't climb past stages—you learn to express any stage healthily as the situation demands.
2. **Integration, not transcendence** - No stage is "higher" or "better." Each is an essential capacity. Beige (survival) is as vital as Clear Light (emptiness).
3. **No guru model** - Geoff explicitly rejects being a guru; encourage customization
4. **Embodiment for neurodivergent mystics** - Target "drowning mystics" who have insights but struggle with structure
5. **Energy Scaffolding** - One new habit every 21 days, sustainable momentum
6. **Cyclical not climactic** - No permanent enlightenment; contraction is as inevitable as expansion. Learning to surf the Wavelength means honoring both.

### Voice & Tone

- **Direct, conversational, non-academic** - Write like you're talking to a smart friend
- **Practical and embodied** - Ground mystical concepts in body/daily life
- **Honest about difficulty** - Don't spiritual bypass; name the struggle
- **Literary and rich** - Use metaphors, quotes, extended examples
- **Target ~900-950 words per section** for major topics

### When Editing or Expanding Stages

1. **Always reference the database CSV files first** - Don't guess specifications
2. **Maintain structural consistency** across stages (use existing stages as templates)
3. **Target ~12,000 words per stage** (current average: 11,750)
4. **Include:**
   - Literary quotes and extended metaphors
   - Concrete scenarios and examples
   - Detailed phenomenology (what it actually feels like)
   - Real-world "off the cushion" applications
   - Conceptual deep-dives (like "Energy Scaffolding" in Beige)
5. **Wavelength breakdowns must:**
   - Use exact Rx/OD terms from database
   - Include phenomenology for each phase
   - Provide off-cushion examples
   - Be ~900-950 words per phase for depth

### Conceptual Distinctions to Maintain

**Teal vs. Clear Light** (Critical - Updated Dec 2025):
- **Teal**: Connection to True Self/Higher Self/Monad - the eternal aspect that chose to incarnate
  - Practices: "I am in my knowing" (Selig), repatterning (Scott Britton), automatic writing
  - Discovery of transcendent self (NOT dissolution)
  - Archetype: True Self Embodier

- **Clear Light**: Recognition of Emptiness (śūnyatā)
  - All phenomena empty of inherent existence
  - Form is emptiness, emptiness is form (Heart Sutra)
  - Middle Way between nihilism and eternalism
  - Archetype: Adept (Whole Adept)

## Co-Authoring Prompts

The `prompts/` directory contains detailed briefs for AI co-authors:
- Read these carefully before writing new content
- They specify database references, visual infographic descriptions, and writing guidelines
- Use current date's prompt file (format: `YYYY-MM-DD-[topic]-prompt.md`)

## Common Queries

**Q: How long should each stage be?**
A: ~12,000 words (current range: 8,000-14,000). Purple (14,302) is the longest; Blue (8,131) is shortest.

**Q: What's the practice duration progression?**
A: 1min (Beige) → 5min (Purple) → 10min (Red) → 15min (Blue) → 20min (Orange) → 30min (Green) → 45min (Yellow/Teal) → 45min (Ultraviolet) → 45min (Clear Light)

**Q: How are stages organized developmentally?**
A: Based on Clare Graves' Spiral Dynamics + Ken Wilber's Growing Up stages + Integral Theory, with APTITUDE's unique focus on the "Free Will Line" of development.

**Q: Can I create new practices or habits?**
A: Check `APTITUDE - Alternative Practices.csv` first. New practices must match stage duration and philosophical focus. Habits should support Energy Scaffolding principle.

**Q: How do I handle the HTML span tags in some markdown files?**
A: These are artifacts from Google Docs conversion. When editing, preserve them or clean them up to proper markdown, but maintain all content.

## Repository Maintenance

- Keep `meta/metrics.md` updated after significant content changes
- Stage files should increment by ~200-500 words when adding depth (not doubling in size)
- When referencing practices, always check database for authoritative descriptions
- Maintain consistency in section headers across all 10 stages
