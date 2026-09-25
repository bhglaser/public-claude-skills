---
name: discussion-init
description: Initialize a directory for writing a conference discussion. The user drops in the paper PDF and a PDF of the discussion invitation email. The skill identifies both PDFs (without renaming), surfaces the discussion logistics from the invitation (conference, session, date, length), deep-reads the paper, writes a PAPER_GUIDE.md (argument + contribution + notation key + discussion hooks), creates an empty discussion_notes.md for the user to fill as they learn the paper, and builds a /beautiful_deck that teaches the paper back to them so they can write the discussion. Run from inside the dump directory.
allowed-tools: Bash(ls*), Bash(pwd*), Bash(pdftotext*), Bash(pdfinfo*), Bash(python*), Bash(find*), Bash(basename*), Bash(wc*), Read, Write, Edit, Glob, Agent, Skill
argument-hint: (none — run from inside the discussion directory)
---

# Discussion-Init: Set Up a Conference-Discussion Directory

This skill prepares a working directory for writing a conference discussion of a paper. The user is the assigned discussant at a conference (WFA, AFA, NBER, etc.). They drop two PDFs into a directory: the **paper** they are discussing, and a PDF of the **invitation email** that assigned them the discussion. This skill identifies both, pulls the discussion logistics out of the invitation, deeply reads the paper, creates an empty notes file for them to fill as they learn the paper, and builds a Beamer deck that teaches the paper back to them so they can prepare the discussion.

It leaves the dumped PDFs untouched and scaffolds no LaTeX report. Its deliverables are: an **empty `discussion_notes.md`** scratchpad the user owns, a **`PAPER_GUIDE.md`** reference, the **teaching deck** (with its reusable TikZ figures), and the kept reading intermediates (`paper_text.md` + the `paper_split/` chunks). Everything except the originals is fair game to keep — the user reuses the figures and the raw pages when building the actual discussion deck.

## When This Skill Is Invoked

The current working directory contains, at minimum, the paper PDF and a PDF of the discussion-invitation email. The user has invoked `/discussion-init` from inside that directory. The skill takes no arguments.

## Step 1: Show Context

Run `pwd` and `ls` to show the user what's in the directory. If there is already a `discussion_notes.md`, a `PAPER_GUIDE.md`, or a `teaching_deck/` folder present, **stop and warn** — show what exists and ask whether to overwrite. Never silently clobber notes the user may have already started.

## Step 2: Identify the PDFs (Peek, Don't Rename)

List all PDFs. For each, peek at the first page with `pdftotext -l 1 <file> -` to get the title / heading and classify it:

| Role | First-page cues |
|------|-----------------|
| Paper | Long (15+ pages); title page with author list and abstract |
| Invitation email | Short (1–2 pages); email headers (From/To/Subject/Date); language like "discussant", "discussion", "session", "we would like to invite you" |

Use `pdfinfo <file>` page count to disambiguate — the paper is long, the invitation is short. Present the proposed mapping (`file.pdf → role`) and ask the user to confirm before proceeding. A silent misidentification corrupts every downstream step.

**Do NOT rename or move the dumped files.** Keep the original filenames exactly as dumped. Originals are never deleted or moved. All derivative files (`paper_text.md`, `discussion_notes.md`, `teaching_deck/`) live alongside them.

## Step 3: Surface the Discussion Logistics from the Invitation

The invitation is short — read it directly (`pdftotext <invitation>.pdf -`). Extract whatever logistics it states, and surface them to the user plainly:

- **Conference** and year (WFA, AFA, NBER, EFA, …)
- **Date / time** of the session (and city, if travel)
- **Session title** or theme, if given
- **Discussion length** (conference discussions are typically 10–15 min — note it if stated, since it sizes the deck)
- **Any deadline** for sending slides to the organizer
- **Who to send slides to** / the organizer's name

These logistics are not written to a file (the notes file stays empty — see Step 5); they are reported to the user now so they have the context, and they tune the deck length in Step 6.

## Step 4: Deep-Read the Paper (split-pdf in a Subagent)

Papers are long. Reading the full PDF directly will either crash the session ("prompt too long") or produce shallow, hallucinated output. Use the `split-pdf` skill (`~/.claude/skills/split-pdf/SKILL.md`).

**Agent isolation is required.** Because this skill keeps working after the read, the PDF reading MUST run inside a subagent. Launch an Agent (subagent_type: general-purpose) with a self-contained prompt:

- Input: absolute path to the paper PDF in the working directory.
- Instructions: follow the split-pdf skill — split into 4-page chunks in a `paper_split/` subdirectory of the working directory, read 3 at a time, produce a structured extract at `paper_text.md` alongside the source.
- **Keep all the reading artifacts.** Do **not** delete the `paper_split/` build directory, the page chunks, or any per-chunk reading notes the split-pdf skill produces. The user reuses these — to pull a specific page/figure, or to re-read a section while drafting. The only files never to touch are the original dumped PDFs. (This is a deliberate departure from the usual split-pdf cleanup step.)
- **Extract dimensions tuned for writing a discussion:**
  - Research question and why it is hard / interesting
  - Contribution relative to the literature (and the authors' own framing of it)
  - Model or empirical setup
  - **Every load-bearing assumption**, flagged explicitly
  - **Full notation glossary: each important symbol → its meaning** (mirror the paper's own symbols)
  - Main results, stated as the authors claim them
  - **Hooks for a discussant:** the single most surprising/important result; the weakest link or biggest "what if"; obvious robustness/alternative-explanation questions; how it connects to the broader literature. (Surface these as raw material — do not write the discussion.)
  - One-sentence statement of the paper's core claim
- Report back: a one-paragraph content summary, page count, and figure/table count.

After the agent returns, read `paper_text.md` (plain markdown, cheap) in the main conversation.

## Step 5: Create the Empty Discussion Notes File

Write `discussion_notes.md` to the working directory. **It must be empty** — the user fills it themselves as they learn the paper. Create it with no content (a zero-length file). Do **not** pre-populate it with a scaffold, headings, or extracted points; the whole purpose is a blank scratchpad they own.

(The paper's content and the discussant hooks from Step 4 live in `paper_text.md`, the `PAPER_GUIDE.md` written in Step 6, and the teaching deck — not in this file.)

## Step 6: Write the Paper Guide

Write `PAPER_GUIDE.md` to the working directory — the user's reference for the argument and notation while they read the paper and drafts the discussion. Populate every section from `paper_text.md`:

```markdown
# Paper Guide: <Title>

**Authors:** ...
**Venue:** <conference + year, from the invitation>
**Discussant:** <the user's name, from the invitation>

## Argument
A few paragraphs walking the paper's logic — the question, the setup, the mechanism, the result.

## Contribution
2–3 sentences on what is new relative to the literature, and the authors' own framing of it.

## Notation Guide

| Symbol | Meaning |
|--------|---------|
| ...    | ...     |

(Exhaustive — the discussant's cheat sheet. Mirror the paper's own symbols exactly.)

## Discussion Hooks
Neutral, factual raw material for the discussion — NOT a verdict:
- The single most surprising / important result
- The load-bearing assumptions each result rests on (distinguishing *assumed* from *proven or calibrated*)
- Obvious alternative explanations and the natural robustness questions a discussant would raise
- How the paper connects to the broader literature
```

This is the one written reference the user leans on; the `discussion_notes.md` from Step 5 stays their own empty scratchpad for the points they decide to make. Guard against overwriting an existing `PAPER_GUIDE.md` — confirm before clobbering.

## Step 7: Build the Teaching Deck via /beautiful_deck

Invoke the `beautiful_deck` skill to build a Beamer deck that teaches this paper to the user so they can write the discussion. **Pre-answer its Step-0 triage** so it does not re-interrogate them:

- **Q1 (source):** the paper — already split. Point beautiful_deck at `paper_text.md` (do not re-split).
- **Q2 (audience):** the custom **"Discussant preparing a discussion"** profile below — instruct beautiful_deck to use THIS profile *instead of* its standard audience table, and not to ask Q2.
- **Q3 (figure language):** none by default; only reproduce a figure if the paper truly needs one.
- **Q4 (format):** Beamer.
- **Q5 (main takeaway):** the paper's core claim, from Step 4. This is for planning the arc only; the deck ends on a plain summary, not a one-sentence closer.
- **Output:** into a `teaching_deck/` subfolder of the working directory.
- **Theme:** neutral house style.

**Keep the figures and make the TikZ reusable.** The user reuses the teaching deck's diagrams in their *actual* discussion deck, so the figure assets must survive. Instruct beautiful_deck to:
- **Write every schematic TikZ diagram as a standalone, `\input`-able snippet** in a `teaching_deck/figures/` (or `teaching_deck/tikz/`) folder — one file per diagram, each self-contained (its `\tikzset` styles either local or clearly noted), so it can be dropped into another deck. The deck `\input`s these rather than inlining the TikZ in the main `.tex`.
- **Never prune the `figures/` or `scripts/` directories**, even if a given diagram ended up inline or a folder looks empty. Leave the scaffold in place.
- Keep the `_outline.md` too.
This is a deliberate departure from beautiful_deck's default delivery — the diagrams are a reusable deliverable here, not throwaway deck internals.

**Theme dependency / graceful degradation.** `beautiful_deck`'s neutral house style lives at `~/.claude/references/latex_toolkit/themes/neutral/neutral.sty`. The repo's `install.sh` puts it there, but a manual install may have skipped it. Before relying on it, check whether the file exists. If it is missing, do **not** block — instruct beautiful_deck to build a **self-contained neutral theme inline in the deck preamble** (dark-navy `#2E4057` / slate `#4F6D7A` / warm-gray `#8A8780` / cream `#F7F5EF`, a 2mm left-rule frame title, `lmodern` + `professionalfonts`). The deck must compile with no external theme dependency.

### The "Discussant preparing a discussion" audience profile (pass this verbatim to beautiful_deck)

> **Logos 70% / Ethos 10% / Pathos 20%.** Goal: get an expert financial economist on top of an unfamiliar paper fast enough to **write a conference discussion of it** — comprehension first, with the raw material for constructive critique surfaced but not pre-judged. Lead with the question and why it's hard. State the model / empirical setup early and **flag every load-bearing assumption.** **Introduce notation explicitly, mirroring the paper's own symbols**, so the deck doubles as a notation key. Walk the main mechanism / identification. Present results as the authors claim them. Replace the usual "Devil's Advocate" slide with two factual slides: a **"Load-bearing assumptions"** slide listing what each result rests on (distinguishing *assumed* from *proven or calibrated*), and a **"Discussion hooks"** slide listing — neutrally — the most surprising result, the obvious alternative explanations, and the natural robustness questions a discussant would raise. Do not write the discussion or take a verdict; surface what a discussant could build on. Intuition-first ordering applies. ~15–18 slides, neutral theme.

## Step 8: Summarize and Hand Off

Show the user the resulting directory structure, e.g.:

```
WFA-2026-Smith-LiquidityShocks/
├── liquidity_shocks.pdf        # the paper — untouched original
├── invitation.pdf              # discussion invitation — untouched original
├── paper_split/                # split-pdf build: page chunks + per-chunk notes (KEPT)
├── paper_text.md               # split-pdf extract
├── PAPER_GUIDE.md              # argument + contribution + notation key + discussion hooks
├── discussion_notes.md         # EMPTY — the user's scratchpad to fill as they learn the paper
└── teaching_deck/              # beautiful_deck output
    ├── <deck>.pdf              # compiled teaching deck
    ├── <deck>.tex
    ├── <deck>_outline.md
    └── figures/                # standalone, reusable TikZ snippets (for the discussion deck)
```

Tell the user:
- The discussion logistics pulled from the invitation (conference, date, length, slide deadline / who to send to).
- `PAPER_GUIDE.md` is the reference for the argument, notation, and discussion hooks while they read.
- `discussion_notes.md` is their empty scratchpad — start dropping points there while reading.
- `teaching_deck/` is the deck that teaches the paper back to them; `teaching_deck/figures/` holds the reusable TikZ diagrams they can `\input` into their discussion deck.
- `paper_text.md` is the structured extract, and `paper_split/` keeps the underlying page chunks if they want the raw detail.

## Notes

- **Never delete or rename the dumped PDFs.** They are read in place. All generated files live alongside them.
- **`discussion_notes.md` starts empty — always.** Do not scaffold it. The user explicitly owns its content.
- **Use split-pdf in a subagent for the paper.** Reading a long paper directly in the main conversation will crash the session or produce hallucinated output.
- **Keep the intermediates.** Both the `paper_split/` reading artifacts and the `teaching_deck/figures/` TikZ are kept, not cleaned up — the user reuses them (raw pages while drafting; diagrams in their discussion deck). The only files off-limits to deletion are the original dumped PDFs.
- **The deck audience is fixed** to the "Discussant preparing a discussion" profile — pass it verbatim so beautiful_deck honors it rather than prompting for one of its standard rows.
- **Don't write the discussion.** This skill prepares the user to write it themselves — it surfaces hooks, it does not take a position.
- **`PAPER_GUIDE.md` is the one written reference** — argument, contribution, notation key, and discussion hooks, all drawn from `paper_text.md`. It is distinct from the empty `discussion_notes.md` scratchpad.
- **Guard against overwriting** an existing `discussion_notes.md`, `PAPER_GUIDE.md`, or `teaching_deck/` before writing.
