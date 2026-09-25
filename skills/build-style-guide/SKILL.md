---
name: build-style-guide
description: Build a calibrated, validated prose style guide from an academic's own published papers, and package it as a personal `write-like-<name>` skill. Chunks 3+ papers into paragraphs, has blind subagents regenerate each paragraph from phrasing-free claims to get author-vs-LLM contrast pairs, analyzes the pairs in parallel shards, drafts a guide, calibrates its rules against measured frequencies (sentence-length distribution, connective rates per 1k words), and runs a blind held-out test (guided vs. unguided rewrites judged against the author's real paragraphs) before shipping. Use when someone says "make Claude write like me", "build my style guide", or "I want a write-like-me skill".
argument-hint: '[paths to 3+ of your papers (.tex preferred, .pdf ok), optional held-out paper, optional working dir]'
allowed-tools: Bash(python3*), Bash(pdftotext*), Bash(ls*), Bash(mkdir*), Bash(cp*), Bash(wc*), Bash(head*), Bash(open*), Read, Write, Edit, Glob, Grep, Agent
---

# Build Style Guide: "Write Like Me, Not Like Claude"

This skill turns a researcher's published papers into a **personal writing-style skill** (`~/.claude/skills/write-like-<name>/`). The finished skill rewrites or drafts prose in their voice and removes default-LLM tics. The method is contrastive and measured:

1. Take the author's real paragraphs.
2. Reduce each one to claims with no phrasing.
3. Have a fresh LLM rewrite the paragraph blind from those claims. Every difference between the two versions is style, because the content is the same.
4. Mine those differences for rules.
5. Replace every "never/always" with the author's measured rate.
6. Prove the guide works on a paper it has never seen before shipping it.

**Track record:** the pilot run of this pipeline, on one author's published finance papers, produced 284 pairs from 3 papers and a guide validated at 72% on a held-out paper. The target shape of the finished skill is `templates/write-like-SKILL.md`. Read it before Step 6.

## What to tell the user up front
- **Inputs:** at least **3 papers for training plus 1 more held out** for validation. LaTeX source (`.tex`) is much better than PDF. PDF extraction breaks paragraphs at page boundaries and mangles math. Solo-authored papers give the cleanest signal (see "Coauthor dilution" below).
- **Cost:** this is token-heavy. It runs about 8 pair-generation subagents per 300 paragraphs, 4 analysts, and roughly 9 validation subagents per round. Budget an hour or two of wall time.
- **Output:** a working directory with all intermediate data and two HTML viewers, plus the installed `write-like-<name>` skill.

## The lesson from the pilot run (read before writing any rules)
The pilot's **v1 guide scored 50% in blind validation, which is a wash.** Every analyst had reported that "the author writes shorter sentences than Claude." So v1 said "keep sentences short," and the guided writer chopped flowing sentences into staccato fragments, far shorter on average than the author's real sentences. Measuring the real distribution (mean, median, stdev, and the share of short, mid, and long sentences) and **stating it with numbers** fixed this. The measurement also softened other absolutes: a construction v1 banned outright turned out to have a small but real rate, so the rule became "sparingly, ~N per 1k words". The calibrated v2 scored **72%** (17 of 24 items won, one-sided p ≈ 0.03). General rule: **analysts overstate contrasts, so encode tendencies with measured rates and ban only what the author essentially never does.** The held-out losses also showed that over-banning hurts. The author used a construction the guide had banned on the held-out paper, and the ban cost those items.

## Coauthor dilution
Coauthored papers mix voices, and co-writers edit each other's sentences. The result is the "house style of papers this person is on," not provably their own sentences. That may be fine, but ask the user. If they have solo papers, prefer them for training. Then run `calibrate.py --by-paper` to see whether solo and coauthored papers differ on sentence length. Mention the mix in the guide's caveats either way.

---

## Workflow

`SCRIPTS` = this skill's `scripts/` directory. `WORKDIR` = the working directory (default `~/style-guide-<slug>/`, where `<slug>` is the lowercase first name, e.g. `jane`). All scripts use only the Python 3.8+ standard library. PDF input also needs `pdftotext` (`brew install poppler`) or `pip install pypdf`. Every script has `--help`.

### Step 0: Intake
Ask the user for, or confirm, these items:
1. Name (for `write-like-<slug>`) and field (e.g. "academic finance"). The field goes into the subagent prompts.
2. Paths to the **training papers** (3+; more is better; 3 gave ~280 usable paragraphs). For each paper: solo or coauthored, and roughly when it was written. Older work such as a job-market paper may not reflect the current voice. Let the user decide whether to include it.
3. One **held-out paper** that is NOT in the training set. It is used only for validation. Prefer a solo paper, or one with a different coauthor.
4. The WORKDIR. Create `WORKDIR/{chunks,pairs,analysis,versions,validation}`.

Use `.tex` when it exists. For multi-file projects, point at the main file; `\input`/`\include` are expanded.

### Step 1: Chunk the training papers
```
python3 SCRIPTS/chunk.py Name1=path/one.tex Name2=path/two.tex Name3=path/three.pdf --out WORKDIR/chunks
```
This keeps narrative paragraphs of 30 words or more. It drops display math, floats, theorem/proof environments, appendix, bibliography, acknowledgments, and math-fragment lead-ins. Inline `$...$` stays in, because it is part of the voice. Short `Name`s become the ids (`Name1:001`). **Check:** aim for 200–400 paragraphs in total. `head -3` a paper's JSONL and spot-check that the text is clean prose. If a paper yields almost nothing, its prose may live in `\input` files the chunker couldn't find, or its PDF extraction failed.

### Step 2: Chunk and sample the held-out paper
```
python3 SCRIPTS/chunk.py Heldout=path/four.tex --out WORKDIR/chunks/heldout --no-combined
python3 SCRIPTS/validate.py heldout --chunks WORKDIR/chunks/heldout/Heldout.jsonl --n 24 --dir WORKDIR/validation
```
This samples 24 clean paragraphs of 60–220 words, spread evenly through the paper. Do this now so the held-out text never leaks into the analysis. **Do not read the held-out paragraphs while writing the guide.**

### Step 3: Generate the contrast pairs (parallel subagents)
```
python3 SCRIPTS/pairs.py split --chunks WORKDIR/chunks/all.jsonl --size 40 --out WORKDIR/pairs/in
```
Launch **one subagent per batch file, all in one message**, using **Prompt A** in `references/prompts.md`. Each subagent first extracts phrasing-free claim bullets, then writes its own paragraph from the bullets alone. Output goes to `WORKDIR/pairs/batch_NN.jsonl` with the schema `{id, paper, section, author, bullets, llm}`. When all are done:
```
python3 SCRIPTS/pairs.py merge --chunks WORKDIR/chunks/all.jsonl --batches 'WORKDIR/pairs/batch_*.jsonl' --out WORKDIR/pairs/all_pairs.jsonl
```
`merge` validates JSON and schema, restores the verbatim author text from the chunks, and lists missing ids. Re-run the subagent for any batch with missing ids or bad JSON. It also reports author-vs-LLM word similarity. For reference, the pilot run had a mean of 0.69 and a range of 0.15–1.00. Spot-check the most similar pairs. They should be degenerate chunks (name lists, equation fragments), not lazy paraphrases. **Do not ask for a "rewrite" or for "generic prose":** a rewrite stays too close to the original and hides the tics, and "generic" doesn't work. The bullets-first design is what makes the pairs useful.

### Step 4: Filter, view, shard
```
python3 SCRIPTS/pairs.py filter --in WORKDIR/pairs/all_pairs.jsonl --out WORKDIR/pairs/all_pairs_filtered.jsonl
python3 SCRIPTS/pairs.py viewer --in WORKDIR/pairs/all_pairs_filtered.jsonl --out WORKDIR/pairs/viewer.html --name "<First name>"
python3 SCRIPTS/pairs.py shard  --in WORKDIR/pairs/all_pairs_filtered.jsonl --n 4 --out WORKDIR/analysis/in
```
The filter drops pairs that are near-identical (sim ≥ 0.90), math fragments, acknowledgments, or under 35 words. The pilot run kept 284 of 319. Offer the user the viewer (side by side, sorted by divergence, with toggleable claim bullets). Reading 10 pairs usually convinces people the method works, and they often spot tics themselves. Use 4 shards for about 300 pairs, or roughly one per 70 pairs.

### Step 5: Analyze the pairs (parallel subagents)
Launch **one analyst per shard, all in one message**, with **Prompt B**. Each analyst writes `WORKDIR/analysis/shard_N.md`: patterns stated as contrasts across six dimensions, with example ids and quoted phrases. Patterns found independently in several shards are the most robust.

### Step 6: Write the v1 guide
Use **Prompt C**, or write it yourself after reading all the shard reports. Output goes to `WORKDIR/versions/STYLE_GUIDE_v1.md`. Structure: how to use it, ranked rules grouped into (a) openings, (b) connectives, (c) rhythm and punctuation, (d) diction, (e) surface conventions, then a blacklist, 10–12 verbatim gold pairs, and caveats. Quote examples verbatim from `all_pairs_filtered.jsonl`. Do not paraphrase them.

### Step 7: Calibrate with real frequencies (turn absolutes into tendencies)
```
python3 SCRIPTS/calibrate.py WORKDIR/pairs/all_pairs_filtered.jsonl --by-paper --md WORKDIR/calibration.md --json WORKDIR/calibration.json
```
This reports the author's pooled sentence-length distribution (mean, median, stdev, p10/p90, and short/mid/long shares) next to the LLM's, plus the rate per 1,000 words of about 35 constructions for both the author and the LLM. Each construction gets a verdict: `AVOID`, `LLM-TIC`, `AUTHOR`, or `similar`. For field-specific constructions, pass `--patterns FILE` (a JSON list of `[label, regex, "i"?]`). Then rewrite the guide as `WORKDIR/versions/STYLE_GUIDE_v2.md` and copy it to `WORKDIR/STYLE_GUIDE.md`:
- **Add a "§0 Sentence length" section first**, with the measured mean, median, stdev, and short/mid/long shares. Tell the writer to *match the distribution and vary lengths*, never to "shorten" or "lengthen" as such.
- **Attach a measured rate to every rule** (e.g. "'Thus,' 1.5/1k", "payoff colons sparingly, ~0.7/1k").
- **Ban outright only `AVOID` items** (author ≈0/1k). Rephrase `LLM-TIC` items as "sparingly". Keep `AUTHOR` items as habits to use. **Drop any analyst rule the numbers contradict or mark `similar`**; those are not discriminators.
- If `--by-paper` shows a large difference between solo and coauthored papers, say which one the guide follows.

### Step 8: Blind held-out validation (parallel subagents)
Tags: `v2` is the calibrated guide. Optionally also run `v1` to show the effect of calibration. Rounds reuse the same bullets and baseline.
1. **Bullets:** 2 subagents with **Prompt D** (lines 1–12 and 13–24 of `heldout_chunks.jsonl`). Outputs: `validation/bullets_1.jsonl` and `validation/bullets_2.jsonl`.
2. **Baseline and guided, in one message:** 2 baseline writers with **Prompt E** (`baseline_1/2.jsonl`, no guide) and 2 guided writers with **Prompt F** (`guided_<tag>_1/2.jsonl`, reads `STYLE_GUIDE.md`; fill in the §0 numbers). Both work from the bullets only.
3. `python3 SCRIPTS/validate.py blind --dir WORKDIR/validation --tag v2`. This prints an objective tic table (author vs baseline vs guided). **Check mean words/sentence first.** If guided is well below the author, the guide over-chops, which was exactly v1's failure. The command also writes `judge_items_v2.jsonl` (A/B randomized) and the secret `judge_key_v2.json`.
4. **Judges:** 3 subagents with **Prompt G**, in one message, writing `votes_v2_1..3.jsonl`. Judges never see the key or the guide.
5. `python3 SCRIPTS/validate.py decode --dir WORKDIR/validation --tag v2`. This prints the guided win rate, per-judge tallies, per-item majority with a one-sided binomial p-value, unanimity, and every lost item with the judges' reasons.

**Reading the result** (24 items, 3 judges): about 50% means the guide adds nothing. **17/24 items (p ≈ 0.03) or a ≥65% judgment win rate is a pass.** The pilot run went from 50% to 72%. High unanimity means the judges see a real difference. Lots of split votes means the style signal is weak.

### Step 9: Iterate (usually 1–2 rounds)
Read the lost items: their baseline vs guided text and the judges' reasons. Build the viewer with `validate.py viewer --dir WORKDIR/validation --tags v1 v2 ... --name "<First name>"`. Typical causes:
- **Length off:** guided runs too short or too uniform. Tighten §0.
- **Over-banned construction:** the author does use it. Soften it to a rate.
- **Missing habit:** the judges cite something the author does that the guide never mentions, such as enumerations or repeated connectives. Add it only if the training pairs confirm it (check the rate with calibrate `--patterns`).

Save the new guide as `versions/STYLE_GUIDE_v3.md`, copy it to `STYLE_GUIDE.md`, and rerun **only the guided writers and the judges** under the new tag. Reuse the same bullets and baseline. Stop when the guide passes, or after about 3 rounds. The held-out items start to act like training data once you tune against them. If you iterate more, sample fresh held-out paragraphs, from other sections or another paper, for the final number.

### Step 10: Ship the `write-like-<slug>` skill
1. Create `~/.claude/skills/write-like-<slug>/`. If that path isn't writable in this session, write the files to `WORKDIR/skill/` and give the user the `cp -r` command.
2. `STYLE_GUIDE.md`: the final calibrated guide. Put the §0 length distribution first, then the rules with rates, the blacklist of `AVOID` items, the gold pairs, and caveats covering coauthor mix, corpus size, typos, and scope.
3. `SKILL.md`: fill in `templates/write-like-SKILL.md`. Include the frontmatter (`name`, a `description` that names the voice and the top tics, and `argument-hint`), rewrite and draft modes, the compact calibrated rules, the blacklist, a 5-item self-check with sentence-length variation first, and a provenance line with the real numbers (pairs, papers, words, held-out win rate, version history). Optional: a register dial (formal / conversational / general) that changes diction and apparatus while keeping the sentence-level rules.
4. Smoke test: draft one paragraph on a topic from the user's field with the new skill, and one without it. Show both, and ask the user to flag any remaining tic. In the pilot, the first real uses turned up two tics that the pairs had missed, both cases of the writer rating the importance of its own claims. Add such findings to the blacklist and self-check. User feedback after shipping is part of the method.

### Step 11: Report to the user
Report: the papers used, pairs kept, the measured length distribution, the top 5 rules, the validation result per round (win rate, items won, p-value), where the skill lives, how to invoke it (`/write-like-<slug> <text | file.tex | topic>`), and the paths to both viewers (`pairs/viewer.html` and `validation/results_viewer.html`). `open <file>` may be blocked by a sandbox. If so, give the path.

---

## Working directory layout
```
WORKDIR/
  chunks/        <Name>.jsonl per paper, all.jsonl; heldout/<Name>.jsonl
  pairs/         in/batch_NN.jsonl (inputs), batch_NN.jsonl (subagent outputs),
                 all_pairs.jsonl, all_pairs_filtered.jsonl, viewer.html
  analysis/      in/shard_N.jsonl, shard_N.md
  versions/      STYLE_GUIDE_v1.md, _v2.md, ...
  STYLE_GUIDE.md current guide (what guided writers read)
  calibration.md / calibration.json
  validation/    heldout_chunks.jsonl, bullets_K.jsonl, baseline_K.jsonl,
                 guided_<tag>_K.jsonl, candidates_<tag>.jsonl, judge_items_<tag>.jsonl,
                 judge_key_<tag>.json, votes_<tag>_J.jsonl, decoded_<tag>.jsonl,
                 results_viewer.html
```

## Scripts
| Script | Does |
|---|---|
| `chunk.py` | .tex/.pdf/.txt/.md → prose paragraphs JSONL. Expands `\input`, strips comments and non-prose environments, cuts appendix and bibliography, drops acknowledgments and math fragments, tracks section titles. |
| `pairs.py split/merge/filter/shard/viewer` | Batches chunks for the pair subagents. Merges and validates their output (verbatim check, missing ids, similarity report). Filters degenerate pairs and adds `sim`. Shards for the analysts. Builds the side-by-side HTML viewer. |
| `calibrate.py` | Sentence-length distribution and construction rates per 1k words, author vs LLM, with AVOID / LLM-TIC / AUTHOR / similar verdicts. `--by-paper`, `--patterns`, `--md`, `--json`. |
| `validate.py heldout/blind/decode/viewer` | Samples held-out paragraphs. Merges bullets, baseline, and guided output, prints the tic table, and writes blinded judge items plus a key. Decodes votes into a win rate, majority, binomial p, and lost items. Builds the multi-round results viewer. |
| `stylemetrics.py` | Shared sentence splitting, word counts, similarity, the default construction patterns, and JSONL I/O. |

## Guardrails
- Treat the user's papers as read-only. Write only inside WORKDIR and the new skill directory.
- Never show the held-out paragraphs or the judge key to the analysts, guided writers, or judges.
- Don't claim a win rate you didn't decode. Report the losses too.
- The guide's scope is the genre it was built from, usually journal prose. Say so in the finished skill.
