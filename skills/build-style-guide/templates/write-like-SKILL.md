---
name: write-like-{slug}
description: Draft or rewrite {FIELD} prose in {FULL_NAME}'s writing style ({3-5 WORD SUMMARY OF THE VOICE, e.g. "flat, agent-first, plain-connective, varied-length sentences"}) and strip the default-LLM tics ({TOP 4-6 BLACKLIST ITEMS}). Use when writing or editing paragraphs for {FIRST_NAME}'s papers, or when asked to make text "sound like me / less like Claude."
argument-hint: '[text to rewrite, a .tex file path, or a topic to draft]'
---

# Write Like {FIRST_NAME}

Draft new {FIELD} prose, or rewrite existing prose, in {FIRST_NAME}'s voice instead of the default LLM voice.

**Provenance:** built from {N_PAIRS} content-matched paragraph pairs across {N_PAPERS} of {FIRST_NAME}'s papers (real prose vs. an independent LLM regeneration of the same claims). Calibrated against measured frequencies in ~{N_WORDS}k words of the author's writing. **Validated blind on a held-out paper: {WIN_RATE}% of paragraphs written with these rules were judged more like {FIRST_NAME} than the unguided baseline** ({N_ITEMS} paragraphs x {N_JUDGES} judges; earlier versions: {HISTORY, e.g. "v1 50%"}). The pipeline and data live in `{WORKDIR}`.

**Scope:** academic research prose (journal manuscripts): intros, model framing, results discussion, conclusions. NOT calibrated for email, referee reports, or slides.

## How to use

**Rewrite mode** (input is existing text or a `.tex` file): keep the content, claims, citations (`\cite{}`), refs (`\ref{}`), and math (`$...$`) exactly as they are. Change only the prose style, using the rules below. Do not add or drop any claim. Return the rewritten passage. For a file, show a before/after and offer to apply it.

**Draft mode** (input is a topic or bullet points): write the paragraph(s) from the content, in the style below.

**Always finish with the self-check** at the bottom before returning.

## The rules (calibrated tendencies, not bright lines)

### 0. Sentence length: match the distribution
{FIRST_NAME}'s sentences: **mean ≈ {MEAN} words, median {MEDIAN}, stdev ≈ {STDEV}**, roughly **{SHORT}% short (<15w), {MID}% mid (15–35w), {LONG}% long (>35w)**. Each paragraph should mix lengths. Do not uniformly shorten or lengthen.

### 1. Openings & information order
- {RULE, with the measured rate where one exists}

### 2. Connectives & discourse markers
- **Keep:** {the author's workhorses, with /1k rates}
- **Avoid the substitutes:** {LLM upgrades -> author's form}

### 3. Rhythm & punctuation
- {colons, em-dashes, semicolons: each with author rate vs LLM rate, e.g. "sparingly (~0.7/1k)"}

### 4. Diction & register
- {plain vs escalated verbs, repetition vs elegant variation, confidence of claims}

### 5. Surface conventions
- {e.g. "US" not "United States", hyphenation, footnote habits}

## Near-absent in {FIRST_NAME}: safe to avoid outright (the blacklist)
{Only constructions whose measured author rate is ~0 (calibrate.py verdict AVOID), each with the substitute.} Everything else is used at low but nonzero rates. Use it moderately; don't eliminate it.

## Self-check before returning
1. **Sentence lengths vary** around a mean of ~{MEAN}? (Most important.)
2. **No blacklist items** slipped in?
3. {Top author habit} where natural?
4. {Second habit}?
5. **Same claims, citations, refs, and math** as the source, with nothing added or dropped?

## Deeper reference
The full guide with verbatim gold before/after pairs is bundled here as `STYLE_GUIDE.md`.
