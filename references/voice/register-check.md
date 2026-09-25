# Register Check — Anti-Slop Pass

A detect-and-repair pass for generated slide prose: titles, bullets, framing lines, conclusions.
It lists six habits that LLM-written slides fall into, with a repair direction for each.

**This file grows with you.** It ships with invented examples. Each time `/beautiful_deck` flags a line and
you rewrite it (Step 4.5), your rewrite is logged to `captured.jsonl` next to this file, and you can add
the pair to **Your exemplars** at the bottom. Your own pairs outrank the starter examples: after a few decks,
the file describes how *you* repair slop, not how anyone else does.

**Scope: prose register only.** This pass governs the *words*: sentence shape, diction, framing. It says
nothing about visual form. Creative use of space, boxes, layout, and TikZ is encouraged and never flagged
here. Voice and craft are separate axes; never let a prose check revert a good layout.

## How to use this

For each line you generate, scan it against the six tells below. When one fires, **repair the line, don't
delete it.** The repair direction is almost always one of these:

- **Verbs over essences.** Say what was *done* (constructs, shows, prices, distorts), not what something *is*.
- **Plain evaluatives.** *Nice, interesting, important, neat, impressive.* Not *compelling, profound, seminal, masterful, tour de force.*
- **Keep the mechanism.** Don't drop the clause that says how it works to make the line sound clean.
- **Let questions stay questions.** A real question answered plainly beats a question converted into a portentous declaration.
- **Keep the hedge.** *Necessarily, may, might, probably, seems.* Slop deletes qualifiers to sound decisive.

**What the tool actually does.** In practice, generated slides lean on *structural* slop (aphorism,
antithesis, compression into a slogan, em-dash restatement) far more than on grand adjectives. Weight the
scan toward tells 1, 3, and 5.

The examples below are invented for illustration.

---

### 1. essence-claim — asserts what something *is* instead of what was *done*
Scan for: "is really/just X", "are not X — they are Y", copula-as-thesis, "at its core/heart/bottom".

- ✗ "Covenants are not contract terms — they are the lender's steering wheel"
  ✓ "Covenants let the lender intervene before default"
- ✗ "At its core, the result is a story about information"
  ✓ "The result comes from the lender learning about the borrower over time"

A plain copula is fine ("The tranche is the lemon"). The tell is the inflation ("is, in essence,"), not the "is".

### 2. inflated-evaluative — swaps a plain judgment word for a grand one
Scan for: compelling, profound, seminal, elegant (as praise), masterful, exquisite, tour de force, foundational.

- ✗ "A compelling paper on a profound question"
  ✓ "Nice paper on an important question"
- ✗ "A tour de force of data construction"
  ✓ "Impressive data work"

### 3. em-dash-apposition — an em-dash restating the subject as a grander abstraction
Scan for: " — a/an/the [grander noun phrase]" tacked onto a noun.

- ✗ "The paper builds a search model — a disciplined lens on the price of liquidity"
  ✓ "The paper calibrates a search model to price liquidity"
- ✗ "The puzzle is not why spreads widen — it is why they ever narrow"
  ✓ "Why do spreads ever narrow?"

### 4. nominalization — abstract noun as subject, verb and mechanism dropped
Scan for: "the plausibility/credibility/robustness of X hinges on...", "X's identifying power...".

- ✗ "The credibility of the identification hinges on a narrow exclusion restriction"
  ✓ "Identification needs the instrument to affect leverage only through rates, which seems strong"
- ✗ "The scarcity of default events forecloses robust estimation"
  ✓ "Defaults are rare, so there isn't much data to estimate this"

### 5. faux-aphorism — fragment, antithesis, or chiasmus for false weight
Scan for: balanced "X; Y" pairs, "not merely X but Y", fragments that sound quotable.

- ✗ "Liquidity is easy to supply — and impossible to recall."
  ✓ "Liquidity is easy to supply but hard to pull back once markets rely on it"
- ✗ "I have concerns, naturally. Concern is the discussant's job."
  ✓ "I have a few concerns, but that's my job"

The repair is often *longer* than the slop. Trade quotability for precision.

### 6. portentous-frame — grand stakes wrapped around a plain question or claim
Scan for: "This is the most fundamental question in...", "More than X, this is Y", "It is hard to overstate...".

- ✗ "This is the most fundamental question in banking: why do deposits run?"
  ✓ "Why do deposits run?"
- ✗ "More than a model of fund flows, this opens an entire frontier"
  ✓ "Opens up an interesting question about fund flows"

---

## Your exemplars

Add pairs from `captured.jsonl` here, in the form below, with the tell each one fired. When your pairs and the
starter examples disagree about how to repair a line, follow yours.

<!-- - ✗ "<flagged line>" (tell)
       ✓ "<your rewrite>" -->
