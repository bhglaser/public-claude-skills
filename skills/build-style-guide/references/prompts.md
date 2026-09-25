# Subagent prompt templates

These are the prompts used in the pilot run, rewritten to be general. Fill in the `{PLACEHOLDERS}` before sending. `{WORKDIR}` is the absolute path of the working directory, `{AUTHOR}` is the author's first name, and `{FIELD}` is their discipline (for example "academic finance" or "labor economics").

General rules for every subagent:
- Give each subagent **absolute paths** and **one input file** (or an explicit line range). Don't ask it to "find" anything.
- Tell it the exact output file and schema. Ask it to reply with a count, plus one example where noted, so you can check the work without opening the file.
- Launch all subagents of one step **in a single message** so they run in parallel.
- Subagents must write **valid JSONL**. LaTeX backslashes have to be JSON-escaped (`\\cite`). If a batch fails `pairs.py merge`, have the same subagent rewrite it; don't hand-edit.

---

## Prompt A: pair generation (Step 3), one per `pairs/in/batch_NN.jsonl`

```
You are generating paired training data for a writing-style study. Work carefully.

INPUT FILE: {WORKDIR}/pairs/in/batch_{NN}.jsonl
JSONL, one paragraph per line. Process EVERY line.
Each line has: id, paper, section, subsection, n_words, text. `text` is a paragraph
of prose from a published {FIELD} paper (the reference author's writing).

For EACH line, do these two steps IN ORDER:

STEP 1: extract claims with no phrasing. Read `text` and reduce it to a neutral
bullet list of ONLY its propositional content: the claims, definitions, quantities,
and any \cite{...}, \ref{...}, \eqref{...}, or inline math $...$ tokens it uses.
Strip out ALL of the author's stylistic phrasing, discourse markers, sentence order,
and word choice. Bullets should be terse and neutral: just the facts and claims.

STEP 2: regenerate blind. Working ONLY from your bullet list (do NOT look back at
`text`), write ONE paragraph conveying those claims, as if you were helping draft
this section of a {FIELD} paper. Write it the way YOU naturally would. Do NOT
imitate any style and do NOT try to sound "generic"; just write naturally. Keep the
\cite{...}, \ref{...}, \eqref{...}, and $...$ tokens where the claims use them.
The paragraph must assert the SAME claims as your bullets, with nothing added or dropped.

OUTPUT: write {WORKDIR}/pairs/batch_{NN}.jsonl, one JSON object per input line:
  {"id": ..., "paper": ..., "section": ..., "author": <original text verbatim>,
   "bullets": [<strings>], "llm": <your regenerated paragraph>}
Write valid JSON (escape backslashes). Then reply with the number of records written
and paste ONE complete example (id, author, bullets, llm) for quality review.
```

Why a two-step, bullets-first design: if you simply ask for a "rewrite" of the author's paragraph, the LLM stays too close to the original wording and its own tics never appear. That was the first failed attempt in the original run. Asking for "generic academic prose" doesn't work either. The fix is to reduce each paragraph to phrasing-free claims first, then regenerate blind from those claims.

---

## Prompt B: style analyst (Step 5), one per `analysis/in/shard_N.jsonl`

```
You are a prose-style analyst. You will study paired paragraphs to characterize the
writing style of a {FIELD} author ("{AUTHOR}") in contrast to a default LLM.

INPUT: {WORKDIR}/analysis/in/shard_{N}.jsonl (JSONL). Read and analyze EVERY line.
Each record has: id, paper, section, author (the author's real paragraph), bullets
(claims with no phrasing), llm (a fresh paragraph written by an LLM from the bullets
alone: same content, independent prose), sim (word similarity; lower = more divergent).

Both `author` and `llm` express the SAME content, so every difference is STYLE.
Your job is to characterize the systematic differences.

Analyze along these dimensions. For EACH pattern, give 2-3 concrete example ids and
quote the differing phrases:
1. Sentence structure and openings: how the author opens sentences and paragraphs
   vs how the LLM does (front-loaded conditions? topic sentences? agent-first vs
   object-first? "If" vs "Suppose"?).
2. Discourse markers and connectives: the author's ("Thus", "However", "In other
   words"...) vs the LLM's ("Consequently", "by contrast", "Importantly", "Notably",
   "This raises the question", colons before payoffs...).
3. Rhetorical tics: LLM constructions such as the "not X, it's Y" antithesis,
   escalation ("what matters more..."), dramatization ("it's worth pausing on", "the
   key mechanism is"), pseudo-clefts ("It is X that...", "X is what does Y"),
   rating one's own claims ("and this matters as much as X"), and hedging. Note which
   appear in llm but NOT in author, and vice versa.
4. Diction and register: word choices where they diverge (plain vs escalated verbs,
   latinate vs plain, colloquial vs formal).
5. Sentence length and rhythm: which side is more clause-heavy? Which uses more
   em-dashes and semicolons? Does the author fuse or split? Be careful: report what
   you see, and do not assume the author is "shorter".
6. Anything else distinctive (surface conventions like "US" vs "United States",
   hyphenation, footnotes vs in-text citations, first person singular vs plural).

OUTPUT: write a markdown file {WORKDIR}/analysis/shard_{N}.md with one section per
dimension. State each pattern as a crisp contrast ("{AUTHOR} does X; the LLM does Y")
with the example ids and quoted phrases. Be specific and stick to the evidence; no vague
generalities. Say whether each pattern is consistent or only occasional. Then reply
with a 5-bullet summary of your strongest findings.
```

---

## Prompt C: synthesize the v1 guide (Step 6)

Run this as one subagent, or do it yourself if the shard reports fit in context. In the original run the synthesis subagent crashed and the main agent finished it by hand.

```
You are writing a style guide that teaches an LLM to write {FIELD} prose like a
specific author ("{AUTHOR}") instead of in its own default voice. The guide will be
an instruction file that an LLM reads before drafting prose for the author.

INPUTS:
1. Analyst reports (read all): {WORKDIR}/analysis/shard_1.md ... shard_{K}.md
2. Pair data: {WORKDIR}/pairs/all_pairs_filtered.jsonl (id, paper, section, author,
   bullets, llm, sim). Use it to pull VERBATIM text when you cite an id; never
   paraphrase an example.

Write {WORKDIR}/versions/STYLE_GUIDE_v1.md with these sections:
## 1. How to use this guide (2-4 sentences; say it is contrastive, derived from
   {N_PAIRS} pairs across {N_PAPERS} papers).
## 2. The rules. Merge and DEDUPLICATE the shard findings into one ranked list of
   concrete, actionable rules. Rank by robustness: note "(all K shards)" or
   "(shards 1, 3)". For each rule: an imperative ("Open with the agent: 'We
   report...', not the object."), the LLM anti-pattern it replaces, and ONE verbatim
   example pair with its id. Group into (a) sentence openings and information order,
   (b) connectives, (c) rhythm and punctuation, (d) diction and register, (e) surface
   conventions.
## 3. Near-absent constructions (blacklist): a scannable list of constructions to
   avoid, each with the author's substitute.
## 4. Gold example pairs: 10-12 instructive pairs (favor low sim, but cover every
   paper and several dimensions): id, the author fragment, the LLM fragment, and a
   one-line note on what it teaches.
## 5. Caveats: typos the LLM "fixes" (don't reproduce errors), coauthored papers
   dilute the signal, and the corpus is small.

State tendencies as tendencies. Don't turn "the author does X more often" into
"never do Y" unless the construction is truly absent. Write tightly; every rule
must be usable while drafting a paragraph. Reply with the section headers and the
top 8 rules, one line each.
```

---

## Prompt D: claim bullets for held-out paragraphs (Step 8), 2 subagents, 12 lines each

```
You are extracting claim bullets with no phrasing from academic paragraphs.

INPUT: {WORKDIR}/validation/heldout_chunks.jsonl (JSONL, 1-indexed). Process ONLY
lines {START} through {END}.
Each record has: id, paper, section, n_words, text.

For each line, reduce `text` to a neutral bullet list of ONLY its propositional
content: the claims, definitions, quantities, and any \cite{...}, \ref{...},
\eqref{...}, or inline math $...$ tokens. Strip ALL stylistic phrasing, discourse
markers, sentence order, and word choice. Terse, flat, factual bullets.

OUTPUT: write {WORKDIR}/validation/bullets_{K}.jsonl, one JSON object per line:
  {"id":..., "section":..., "author": <original text verbatim>, "bullets": [<strings>]}
Reply with the count written.
```

The bullets are shared: baseline and guided writers regenerate from **identical** inputs, which makes the comparison fair.

---

## Prompt E: baseline writer (Step 8), 2 subagents, run once and reuse across rounds

```
You are drafting paragraphs for a {FIELD} paper from bullet-point notes.

INPUT: {WORKDIR}/validation/bullets_{K}.jsonl (JSONL). Process every line.
Each record has: id, section, author, bullets. IGNORE the `author` field entirely:
do NOT read it or imitate it. Work ONLY from `bullets`.

For each line: from the bullets alone, write ONE paragraph conveying exactly those
claims, as if you were helping draft this section of a {FIELD} paper. Write it the
way you naturally would. Keep any \cite{...}, \ref{...}, \eqref{...}, and $...$
tokens. Assert the same claims as the bullets, with nothing added or dropped.

OUTPUT: write {WORKDIR}/validation/baseline_{K}.jsonl, one JSON object per line:
  {"id":..., "baseline": <your paragraph>}
Reply with the count written.
```

---

## Prompt F: guided writer (Step 8), 2 subagents per round

```
You are drafting paragraphs for a {FIELD} paper from bullet-point notes, following
an author's style guide.

STEP 0: Read the style guide carefully: {WORKDIR}/STYLE_GUIDE.md. Apply it. Pay
special attention to the section on SENTENCE LENGTH: the author's measured
distribution is {MEAN} words mean, about {SHORT}% short (<15 words), {MID}% mid
(15-35), and {LONG}% long (>35). Match that distribution. Do NOT uniformly shorten
or lengthen. Most rules are tendencies with measured rates, not absolute bans; an
occasional use of a "sparingly" construction is correct.

INPUT: {WORKDIR}/validation/bullets_{K}.jsonl (JSONL). Process every line.
Each record has: id, section, author, bullets. IGNORE the `author` field entirely:
do NOT read or imitate it. Work ONLY from `bullets`.

For each line: from the bullets alone, write ONE paragraph conveying exactly those
claims, applying STYLE_GUIDE.md. Keep any \cite{...}, \ref{...}, \eqref{...},
and $...$ tokens. Assert the same claims as the bullets, with nothing added or dropped.

OUTPUT: write {WORKDIR}/validation/guided_{TAG}_{K}.jsonl, one JSON object per line:
  {"id":..., "guided": <your paragraph>}
Reply with the count written and the average words-per-sentence you aimed for.
```

---

## Prompt G: blind judge (Step 8), 3 subagents per round

```
You are a blind judge in a writing-STYLE study. For each item you get a REFERENCE
paragraph (by a target author) and two candidate paragraphs, "optionA" and
"optionB", that express the SAME content as the reference and as each other.
Content is held constant, so judge ONLY on prose style and voice: sentence rhythm
and length, sentence openings, connective choice, diction and register, punctuation
habits. Decide which candidate reads more like it was written by the same author
as the REFERENCE.

INPUT: {WORKDIR}/validation/judge_items_{TAG}.jsonl (JSONL). Each line:
{id, reference, optionA, optionB}. Judge every line.

For each item, choose "A" or "B". You MUST choose one; no ties. A and B are
randomized, so do not favor a position.

OUTPUT: write {WORKDIR}/validation/votes_{TAG}_{J}.jsonl, one JSON per item:
  {"id":..., "choice":"A" or "B", "reason":"<one short clause>"}
Reply with your A-count vs B-count.
```

Never give a judge the `judge_key_{TAG}.json` file, the words "baseline" or "guided", or the style guide. If a judge dies mid-run, rerun it from scratch under the same `{J}`.
