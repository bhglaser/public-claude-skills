---
name: beautiful_deck
description: End-to-end Beamer deck creation. Restructures content via the Rhetoric of Decks (ethos / pathos / logos), generates figures and tables from R or Python code first, compiles to zero warnings, runs /tikz for visual collision cleanup, and dispatches sub-agents for rhetoric and graphics audits. Use when creating a presentation from scratch or restructuring existing content into a new beautiful deck.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
argument-hint: [content-path-or-description]
---

# Beautiful Deck

This skill is the full deck-creation pipeline: blank slate to audited, compiled PDF, with accompanying scripts for figures and tables.

The guiding philosophy: **a deck is a performance medium, not a document**. It must be beautiful, technically rigorous, smoothly paced (MB/MC equivalence across slides), and visually clean at the pixel level. Every element earns its presence. Every title is an assertion. Every figure carries one message.

This skill is the orchestrator. It calls `/tikz` for visual cleanup, and dispatches sub-agents for rhetoric and graphics audits.

---

## Step 0: Triage — Gather Context Before Touching Anything

You MUST answer these questions before generating a single slide. If the user hasn't provided them in the invocation, ask explicitly. Do not guess.

### Q1: What is the source content?
- A paper draft (`.tex`, `.pdf`, `.md`)
- Existing lecture notes
- An existing deck to be restructured
- A description, and you generate from scratch
- A paper the user is reading — if yes, have they run `/split-pdf` on it? If yes, read the summaries. If not, ask whether to split first.

### Q2: Who is the audience?

Pick ONE and commit. Different audiences demand different rhetorical balances (per Aristotle). This table governs the whole deck.

| Context | Logos | Ethos | Pathos | Reasoning | Implications |
|---|---|---|---|---|---|
| **General Finance academic seminar** | 50% | 30% | 20% | Finance audiences span macro, micro, and theory — the "why should I care" is not automatic. Pathos through a sharp motivating puzzle or market anecdote at the open is load-bearing; if they don't buy the question, they won't listen to the identification. Logos still dominates the body. | Open with the puzzle or anecdote that makes the question land. Identification strategy by slide 4–5. Devil's Advocate required. ~25 slides. Neutral theme. |
| **Finance Theory academic seminar** | 65% | 25% | 10% | Theorists verify the model; they push back on any hidden assumption. Logos dominates. Ethos comes from elegance and discipline of setup. Pathos minimal — they're there for the math. | State the model by slide 2. Assumptions flagged explicitly. Proof sketches over appeals to intuition. Figures show comparative statics, not empirical fits. ~20–25 slides. Neutral theme. |
| **Conference presentation (20 min)** | 50% | 35% | 15% | Time-boxed. Audience decides in 3 minutes whether to listen. Ethos through tightness; pathos in framing "why this matters for the field." | Headline result on slide 2. No literature review. ~15 slides max. End on the headline result and a plain conclusion. Neutral theme. |
| **Real estate professionals (external talk)** | 30% | 30% | 40% | Practitioners reward concrete stories, market context, "what do I do with this." Pathos leads. Ethos through domain fluency (named deals, real cap rates). Logos kept simple. | Open with a market anecdote. Charts over equations. Implications slide is the centerpiece. Jargon explained once. ~20 slides. Neutral theme, possibly warmer accent. |
| **Coauthor working meeting** | 60% | 30% | 10% | Not a pitch — a thinking session. The coauthor is trusted, so ethos is not being earned slide-by-slide. Pathos is low because both parties already care. Logos dominates because the point is to argue through open questions, compare specifications, and decide next steps. Uncertainty is welcome; polish is wasted effort. | More text allowed. Document choices explicitly ("we chose X because Y, but Z is still open"). Open questions get their own slides. Robustness tables visible in full, not teased. Devil's Advocate is replaced by "What's still bothering me." ~15–25 slides but text-heavier than a seminar. Neutral theme. |

### Q3: Which code language for figures and tables?
**R** (ggplot2 + xtable/kable) or **Python** (matplotlib/seaborn + pandas to LaTeX). Pick ONE for the whole deck.

### Q4: Output format — Beamer (default) or something else?

**The default is always Beamer.** Do not switch formats unless the user explicitly asks. Beamer gives the richest control over typography, TikZ, math typesetting, and precise layout — and it compiles to a single PDF that projects reliably anywhere.

The user may request an alternative. Accept these on explicit request only:

- **Quarto (`.qmd` → HTML / reveal.js or PDF / Beamer)** — good for live coding demos
- **Typst** — newer, faster compiles, less mature ecosystem
- **reveal.js** — full web control, needs a browser to present

Whichever format is chosen, the Three Laws and the Aristotelian balance are unchanged. The format is the medium; the rhetoric is the substance. Everything below applies — one idea per slide, assertion titles, MB/MC equivalence, code-first figure generation, the rhetoric and graphics audits. Only the specific compile commands and preamble syntax change.

### Q5: What is the main takeaway?
The result or idea the deck is built around. Use it to plan the arc and to decide what goes in Act III. It is a planning aid, not slide text: do not compress it into a slogan, and do not put it on its own closing slide.

---

## Step 1: Design / Select the Theme

Use the neutral house style at `~/.claude/references/latex_toolkit/themes/neutral/neutral.sty`. Dark-navy + slate + warm gray, designed for research and external audiences. Copy into a project-local Theme/ folder or `\usepackage` from the absolute path.

If the user explicitly asks for a bespoke aesthetic tuned to *this* audience (e.g. "design something original for this conference talk"), treat this as an original-design request and construct a new palette / frame-title style / TikZ accent system from scratch. Do not reuse a previous deck's theme. Build on top of a theme package like `metropolis`, `moloch`, or `focus` if useful — they give sane defaults — but override colors, fonts, frame-title style, title slide, and bullets enough that the result is visually unrecognizable as the source. A reader should not be able to guess what theme package is underneath.

### Palette construction

When designing an original palette, pick a core accent (one color, not an ensemble). Examples:

| Audience | Core accent | Why |
|---|---|---|
| Finance theory seminar | DeepNavy #2E4057 | Anchored, matches the rhetorical weight of identification |
| Real estate external | WarmOrange #E85D04 | Human warmth, urgency, signals "this matters" |
| Conference talk | DeepTeal #0A5264 | Distinctive, academic, enough to be remembered |

Around the core, build a 10-color palette: 1 core, 1 secondary (analogous or complementary), 2 text (one dark, one warm gray), 2 backgrounds (cream + white), 1 alert (deep red), 1 success (forest green or teal), 2 tertiary chart colors. Define in `\definecolor{}` at preamble top. Body text must have contrast ratio ≥ 4.5:1 against background (WCAG AA).

### Frame-title style
Pick ONE:
- **Left rule** — thin colored vertical bar left of title (2mm wide, core accent)
- **Underline** — 1pt horizontal rule below title
- **Background tint** — very light tint of core accent behind title area
- **Simple bold** — no decoration, bold dark text, generous white space

Do not combine. The neutral.sty uses left rule.

### Typography
- `\usefonttheme{professionalfonts}` — required
- Body text: 24pt minimum. Title: `\huge`. Frame title: `\Large\bfseries`. Footnote floor: 18pt
- Sans-serif. Use already-installed fonts: `lmodern` (default), `roboto`, `fira`, `utopia`, `carlito`. Do not require font installation.
- Never justify. Always ragged right (`\RaggedRight`).

---

## Step 2: Design the Narrative Arc

Before writing any slides, write a **one-page outline** to `<deck_name>_outline.md`. Show it to the user before proceeding. This is the checkpoint where a user can course-correct cheaply.

### The pedagogical movement — intuition first, technical last

**This is the single most important rhetorical commitment in this skill.** Every topic, every section, every slide sequence must move in this order:

**Narrative → Application → Picture → Codeblock → Technical**

Not the reverse. Never the reverse.

| Stage | What it looks like | Why it comes here |
|---|---|---|
| **1. Narrative** | A story, a concrete scene, a named person in a named place facing a real problem. | Anchors the audience in something human and specific before anything abstract arrives. Activates pathos. Builds curiosity, not resistance. |
| **2. Application** | A specific example the audience can hold in their hand. "Suppose you are a hospital manager deciding..." | Makes the abstraction physical. They can *picture* the decision, not just parse symbols. |
| **3. Picture** | A figure, a diagram, a visual showing the pattern. One message per picture. Labeled directly. | Pictures carry intuition faster than words or equations. They see the relationship before they name it. |
| **4. Codeblock** | A short, readable snippet that shows how the idea is computed. Embedded in the deck, matching the palette, also saved as a standalone script. | Code is a concrete, operational form of the idea — more precise than a picture, more approachable than a theorem. |
| **5. Technical** | The equation. The theorem. The identification strategy in formal notation. The proof. | This arrives AFTER they already understand what it is saying. The technical becomes a compact summary of what they have intuited — not a wall to climb. |

**The anti-pattern is the lecture that opens with definitions, proves a theorem, and offers an example at the end "for intuition."** This treats the technical as primary and intuition as decorative. The correct pedagogy is the opposite: the intuition is the content; the technical statement is what you walk AWAY with, not what you walk IN with.

When sequencing a section, check every transition: am I moving toward the technical, not away from it? If you find yourself showing an equation before the figure that motivates it, swap them. If you find yourself writing "let $X$ be a random variable..." before the audience has a story to attach $X$ to, delete that slide.

**Exceptions to the order:**
- **Definitions of load-bearing terms** may appear early if unavoidably needed — but state the intuitive meaning first in plain English, formal definition on the *next* slide.
- **Roadmap slides** in long teaching decks can appear before the narrative begins (orientation) — but the first *content* slide must still be narrative.
- **Title slides and section dividers** are structural and exempt.

### The arc structure

Every deck has three acts. The proportions depend on audience (see Q2 table).

**Act I — Tension (open + setup).** 2–4 slides.
- Title slide
- Opening hook: a provocative question, a surprising statistic, or a concrete problem the audience recognizes. **NOT** an agenda, **NOT** "Today I'm going to talk about...", **NOT** a definition slide.
- The stakes: why does this matter? (Pathos lives here.)
- Roadmap (optional — only for teaching decks > 30 slides)

**Act II — Investigation (the argument).** 60–75% of the deck.
- Identification strategy early (academic seminars — skeptics want the source of variation before they'll engage with results)
- One idea per slide. Pyramid principle within each section: state the sub-claim, then support
- Alternate: dense technical slides with lighter summary / figure slides. This creates the "deck breathes" rhythm
- Devil's Advocate slide near the end of Act II (required for academic / external): "A skeptic would say..." followed by the response

**Act III — Resolution (takeaway).** 2–4 slides.
- The headline result, stated as a claim (title) with one figure or one equation supporting it
- Implications: what does this change? What should the audience do or believe differently?
- Conclusion slide: restate the main result(s) and what follows from them in plain sentences, in the author's register. No single centered "remember this" sentence, no slogan, no full-bleed closer. (This departs from the closing-slide advice in `rhetoric_of_decks.md`; follow this skill.)

### Titles as assertions

Every slide title must state a claim.

| Weak (label) | Strong (assertion) |
|---|---|
| Results | Treatment increased K/L ratio by 18% on average |
| Identification | We exploit the 10% WTO tariff ceiling as a mechanical dose |
| Methodology | Markups are computed via De Loecker–Warzynski, not Cobb-Douglas |
| Literature | Prior work confuses level effects with causal responses |
| Implications | A smaller subsidy would have generated the same K/L response |

If someone reads only the titles in sequence, they should understand the argument. Test this: write out just the titles. Does the sequence tell a coherent story? If not, the arc is broken.

### The outline checkpoint

Write the outline as:
```
# <Deck name> — Outline

## Audience and rhetoric
<Copy the Q1–Q5 answers here>

## Theme
<Neutral, or describe original palette>

## The arc
### Act I (slides 1–4)
  1. Title
  2. Opening: <hook>
  3. Stakes: <why this matters>
  4. Roadmap (optional)

### Act II (slides 5–N)
  5. <Assertion title>
  6. <Assertion title>
  ...

### Act III (slides N+1 to end)
  ...
  K. Conclusion: <main result(s) and implications, stated plainly>

## Figures and tables (code-first)
  - Figure 1: <what it shows, which script generates it>
  - Table 1: <what it contains, which script generates it>
```

**SHOW THIS OUTLINE TO THE USER AND WAIT FOR APPROVAL BEFORE WRITING SLIDES.** Do not skip. It is dramatically cheaper to fix the arc here than after every slide is written.

---

## Step 3: Figure and Table Generation — Code First, Then Embed

Non-negotiable order:

1. Write standalone scripts FIRST, in `scripts/` subdirectory
2. Run them FIRST, generating figures into `figures/` and tables into `tables/`
3. Only THEN write the `\includegraphics{}` and `\input{}` calls in the deck

The reverse order — writing `\includegraphics{figure_1.png}` first and generating `figure_1.png` to match — is the #1 cause of mismatched labels, wrong data, and broken compiles. Do not do it.

### 3.1 Scripts must be standalone

Each script runs on its own without depending on other scripts. A student opens `scripts/figure_3.R`, runs it, reproduces exactly `figures/figure_3.png`. That means:
- Imports at top
- Data loading at top (from `data/` — no hardcoded absolute paths)
- Figure / table export at bottom
- No shared state between scripts

### 3.2 Figure principles (R or Python)

- **One message per figure.** If you can't state the takeaway in one sentence, it's too complex
- **Title states the finding** (not the chart type). "Markups fell fastest at the 95th percentile" not "Markup distribution over time"
- **Direct labels, no legends** whenever possible. Label lines at endpoints, bars inside bars. Reserve legends for truly unreadable density
- **Match the deck's palette.** Import deck colors into the script so figures read as part of the deck
- **Figure background matches slide background.** matplotlib: `fig.set_facecolor()` and `ax.set_facecolor()`. ggplot2: `theme(plot.background = element_rect(fill = ...))`
- **Vector format (PDF)** for line charts and schematics. PNG only for images or dense rasters where vector would be too large
- **Check coordinates explicitly.** ggplot2 and matplotlib have silent failure modes: labels get clipped, legends obscure data, tick marks misalign. `/tikz` catches figure label positioning — use it

### 3.3 Table principles

- **Use `booktabs`** — no vertical rules, no double horizontal rules. Top, mid, bottom. Nothing else.
- **Highlight the key number.** A coefficient of interest should be boxed, colored, or bolded. Not all numbers are equal.
- **Strip everything that doesn't advance the argument.** SEs in parentheses, stars for significance, R² and N at bottom. No "Adj R²", no "F-stat", no "Prob > F" unless the argument depends on them.
- **Export to `.tex` fragments, not full tables.** Use `\input{tables/main_result.tex}` in the deck, so the script can regenerate without touching the deck source.

### 3.4 Embed code blocks in the deck

When the deck teaches code (teaching decks, pedagogical content), show the code **in the deck** using `listings` styled to the palette:

```latex
\begin{lstlisting}[basicstyle=\ttfamily\small,
                   keywordstyle=\color{DeepNavy}\bfseries,
                   commentstyle=\color{WarmGray}\itshape,
                   stringstyle=\color{Slate},
                   backgroundcolor=\color{Cream},
                   frame=single,
                   framesep=4pt,
                   rulecolor=\color{WarmGray}]
df |>
  summarize(.by = sic3,
    Delta_ln_theil = ln_theil[year == 2004] - ln_theil[year == 2001]
  ) |>
  drop_na()
\end{lstlisting}
```

Keep blocks short (< 12 lines). Longer code goes across slides or is replaced by a structural skeleton with the full version in the accompanying script.

**Every code block shown in the deck should correspond to a real script file in `scripts/` that can be handed to students.** The deck is the performance; the script is the reference.

---

## Step 4: Write the Slides

Now, and only now, start writing slides.

### 4.0 Load the voice guides BEFORE writing any prose

For prose-bearing seminar/discussion/research-talk audiences, read these two files first and write in that register from the first draft:

- `~/.claude/references/voice/register-check.md` — the six slop "tells" to avoid.
- `~/.claude/references/voice/voice-profile.md` — the user's own positive profile (what their prose actually does), **if it exists**. If it does not, skip it. `voice-profile.template.md` in the same folder shows the format.

Do not treat these as a post-hoc filter. Step 4.5 exists as the safety net, but every line it catches is a line that should not have been written — each flag costs the user a manual rewrite. Bias the first draft.

The failure mode is **structural, not lexical.** The tool's real slop is aphorism, antithesis, em-dash restatement, and compression-into-slogan — not grand adjectives. Concretely, while drafting:

- **Never convert a question into a declaration.** "Why do deposits run?" is the target; "Deposit runs: the standard lens breaks, and the fix is a single new primitive" is the failure.
- **Never use `---` to restate a subject more grandly.** If a dash is followed by a re-inflated noun phrase, cut it.
- **No quotable antithesis.** "not X --- it is Y", "not merely X but Y", balanced fragments. A longer, plainer sentence that makes a precise claim beats a tidy one that doesn't.
- **Keep hedges** (*necessarily, may, might, probably, seems*) and **keep the mechanism clause**. Do not delete either to tighten a line.
- Plain evaluatives only: *nice, cool, interesting, important, neat, impressive*.

### 4.1 The process

Work slide by slide, and also sequence by sequence. For each slide, before moving on:

1. Re-read the outline to confirm this slide's role in the arc
2. **Check the pedagogical movement within the section.** Where are we in Narrative → Application → Picture → Codeblock → Technical? If writing a technical slide, confirm the preceding slides have delivered the story, application, picture, and (if relevant) the code. If not, back up and write those first. Never let the technical arrive before the intuition.
3. Write the title as an assertion
4. Pick ONE visual element: a figure, an equation, a diagram, a single statistic, a code block. Not two.
5. Add minimal supporting text — a labeled setup ("From the FOC:", "Step 1:") or ONE concluding line. NEVER a wall of sentences.
6. Check: can someone in the back row read every character? If not, cut text or increase font.

### 4.2 The hard rules (no exceptions)

- **One idea per slide.** Two max for inseparable contrasts.
- **No wall of sentences.** If you catch yourself narrating what the audience can see, delete.
- **No bullet lists by default.** Find the structure (sequence, contrast, hierarchy, causal chain) and make it visible with layout.
- **No decoration without function.** Stock photos, clip art, decorative icons — delete.
- **White space is confidence.** Crowded slides signal anxiety. Generous margins signal authority.
- **TikZ before figures.** When a diagram can be drawn in TikZ, prefer TikZ over imported graphics. Vector quality, palette integration, in-place editing.
- **Write in the user's register from the first draft.** No aphorism, no em-dash restatement, no question-turned-declaration. See Step 4.0.

### 4.3 MB/MC equivalence — the rhythm check

After drafting the full deck, walk through it and rate each slide's MB (marginal benefit) and MC (marginal cost) on 1–5. The optimal deck has MB/MC approximately equal across slides. Look for:

- **Overloaded slides (MB/MC too low):** text in the footer, multiple competing ideas, charts with too many series. Split or simplify.
- **Underloaded slides (MB/MC too high):** a single word where a sentence would reinforce, wasted real estate. Add or merge.

**Exception: deliberate jump scares.** A sudden spike in density for rhetorical effect — a dense regression table, a provocative claim, a complex diagram. These must be INTENTIONAL. One or two per deck max.

### 4.4 TikZ Generation Defaults — Write Safe TikZ From the Start

These rules exist because `/tikz` (Step 6) is a repair tool, not a safety net. It can catch remaining collisions, but it cannot reliably fix diagrams that were never built with measurement in mind. Safe generation is the defense; `/tikz` is the check.

**Rule 1 — Always set explicit node dimensions.** Every `\node` must declare `minimum width` and `minimum height`. Never let TikZ autosize a box. Autosized boxes make arrow endpoints unpredictable and cause downstream collisions that `/tikz` cannot reliably repair. Example: `\node[draw, minimum width=3cm, minimum height=1cm] (A) {Label};`

**Rule 2 — Every edge label must carry a directional keyword.** Any `node[...]` placed on an arrow without `above`, `below`, `left`, `right`, `sloped`, `anchor=`, `pos=`, or `midway` will render ON the arrow line. This is never what you want. No exceptions.

**Rule 3 — Write a coordinate map comment before every tikzpicture.** Before the first `\node`, write a commented block listing every node name, its coordinates, and its intended dimensions. This forces spatial planning before drawing and makes `/tikz` audit passes faster:

```latex
% Coordinate map:
% (A) at (0,0)  — 3cm x 1cm — "Start"
% (B) at (4,0)  — 3cm x 1cm — "End"
% Arrow: A -> B, label "Step 1" above
```

**Rule 4 — Use canonical templates for the three standard diagram types.** Start from these safe skeletons:
- *DAG (causal diagram):* nodes in a grid with `circle, minimum size=0.8cm`, arrows with `above` or `below` labels, bend angles never exceeding 30 degrees.
- *Flow chart:* nodes with explicit `minimum width=3.5cm, minimum height=1cm, text width=3cm, align=center`, vertical spacing of at least 1.5cm between node centers, labels always as standalone `\node` above arrow midpoints rather than inline edge labels.
- *RDD threshold diagram:* x-axis as a plain `\draw` line, threshold as a `\draw[dashed]` vertical, score dots as `\filldraw` circles with labels placed `above` or `below` with explicit `yshift`.

**Rule 5 — Never use `scale` on a complex diagram.** `scale` shrinks coordinates but not text, creating invisible collisions where the math looks fine but the rendered output is broken. If a diagram is too large, redesign the coordinate layout at the intended size.

**Rule 6 — Never define parameterized TikZ styles inside a Beamer frame.** In Beamer, `#` inside a frame body is consumed by the frame's argument parser before TikZ sees it, causing "Illegal parameter number" errors. These errors cascade and resist all downstream fixes.

The fix: define ALL parameterized styles in the preamble using `\tikzset{}`:

```latex
% In the preamble — BEFORE \begin{document}:
\tikzset{
  mybox/.style={rectangle, draw=charcoal, thick, fill=lightbg,
                minimum width=3.5cm, minimum height=1cm,
                align=center, font=\small},
  myarrow/.style={->, thick, #1},
}
```

Inside frames, USE the styles but never DEFINE them with `#1`. This is a hard constraint of the Beamer/TikZ interaction.

### 4.5 Voice Register Check — interactive; the user rewrites in their own voice

**When:** after the slide prose is drafted, before the compile loop. **Applies to** prose-bearing seminar/discussion audiences. For teaching decks the register differs and no teaching voice guide exists yet — skip, or use judgment.

This is the **safety net**, not the primary defense — Step 4.0 loads the same guides at generation time so the first draft is already in register. A flag here means 4.0 leaked. If a batch produces many flags, that is a signal to strengthen 4.0, not just to fix the lines.

**Flag and explain — never rewrite, and never hand the user a finished replacement to approve.** The entire point is that *the user* rewrites every suspect line themselves, in their own words. That is what keeps their reps intact and keeps the captured pairs authentic: an AI-supplied rewrite skips their practice AND poisons `captured.jsonl`, whose `author` field must be their actual words, not the model's. The AI detects and names the problem; the user writes the fix.

**Scope — prose only.** This check governs the *words*: frame titles, framing sentences, evaluative lines, conclusions. It does **not** touch visual form. Never flag boxes, spatial layout, or TikZ — creative use of space is encouraged and is a separate axis (see Step 4.1–4.4). Voice ≠ craft.

Procedure:

1. Load the voice files:
   - `~/.claude/references/voice/register-check.md` — the six "tells" and repair directions.
   - `~/.claude/references/voice/voice-profile.md` — the user's positive profile (what to write instead), if it exists.
2. Scan every prose-bearing line in the deck against the six tells (essence-claim, inflated-evaluative, portentous-frame, faux-aphorism, em-dash-apposition, nominalization).
3. For each flagged line, present to the user — do NOT edit it, and do NOT propose a replacement sentence:
   - the line and its `file:line`,
   - the tell that fired, and in one phrase the *direction* of the fix (e.g. essence-claim → "say what it does, not what it is"). A direction, never a drop-in sentence.
   Then ask the user to **rewrite the line themselves, in their own words.** They may instead keep it as-is (mark deliberate). The AI flags and explains the tell; the rewrite is always the user's. Present flags in small batches, not one giant dump.
4. Apply the user's decision to the `.tex`.
5. **Capture every line the user rewrites** by appending one JSON object per rewrite to `~/.claude/references/voice/captured.jsonl` (create the file if absent). This file stays on the user's machine; it is their own growing corpus for refining `register-check.md` and `voice-profile.md` later.
   ```json
   {"genre":"discussion","source":"<this deck's name>","tell":"<tell that fired>","slop":"<the flagged AI line>","author":"<the user's rewrite>","emph":false,"captured":true}
   ```
   These captures are the living feed: real (slop → author) pairs that grow the corpus from actual corrections. Lines the user keeps as deliberate are not captured.
6. **Offer to grow the guide.** After the batch, show the user this deck's new captures and ask which to add to the **Your exemplars** section of `register-check.md`, each labelled with its tell. Add only the ones they approve. If a rewrite reflects a new habit they want to keep, rather than just undoing slop, offer to log it in `voice-profile.md` instead.
7. Re-run the scan once after edits to confirm no new tells were introduced, then proceed to Step 5.

This step is a feedback lens, not a generator — it surfaces drift and records how the user fixes it; it does not write their voice for them.

---

## Step 5: The Compile Loop — ZERO TOLERANCE for Warnings

**The standing rule: no cosmetic mistakes.** Overfull `\hbox`, underfull `\hbox`, overfull `\vbox`, underfull `\vbox`, font warnings, missing references — all must return zero counts before handing the deck over, and must return zero at every intermediate checkpoint. Zero on the final compile is not enough if intermediate compiles had warnings — eliminate them as they appear, do not let them accumulate.

### The compile check — run verbatim after every edit

```bash
pdflatex -interaction=nonstopmode <deck>.tex
```

Then, **in this order**:

1. **Fatal errors.**
   ```bash
   grep "^!" <deck>.log
   ```
   Must return nothing. If anything, fix and recompile before moving on.

2. **Overfull / underfull box warnings.**
   ```bash
   grep -cE "Overfull|Underfull" <deck>.log
   ```
   **Must return exactly `0`.** Not "close to zero." Not "just a few small ones." Exactly zero. If nonzero:
   - Run `grep -nE "Overfull|Underfull" <deck>.log` to see every instance with line numbers
   - Read the line from the log, fix per table below, recompile, re-run count. Repeat until zero.

   | Warning type | Fix |
   |---|---|
   | `Overfull \hbox` | Rephrase shorter; use `\adjustbox{max width=\textwidth}`; add `@{}` to outer `tabular` columns; reduce font size on that line only; break long URL with `\url{}` or `\nolinkurl{}` |
   | `Underfull \hbox` | Rephrase; adjust paragraph breaks; add `\hfill` or `\raggedright`; remove unnecessary line breaks |
   | `Overfull \vbox` | Split slide; reduce `\vspace{}` values; shrink figure with `width=0.9\textwidth`; tighten list spacing; remove unnecessary `\vfill` |
   | `Underfull \vbox` | Add `\vfill` or `\vspace*{\fill}`; adjust `\topsep` / `\itemsep`; merge with another slide if truly underloaded |

   **Even 0.1pt overfull must be fixed.** LaTeX reports warnings for a reason — they indicate layout compromises the compiler made without authorization. Letting "just one small one" through is the broken-windows failure mode.

3. **Font warnings.**
   ```bash
   grep -i "warning" <deck>.log | grep -i "font"
   ```
   Must return nothing. Usually means a required font package is missing — install it and recompile.

4. **Missing references and labels.**
   ```bash
   grep -i "warning" <deck>.log | grep -iE "reference|label|citation"
   ```
   Must return nothing. Resolve every `LaTeX Warning: Reference ... undefined` or `There were undefined references`.

5. **Open the PDF and visually inspect.**
   ```bash
   open <deck>.pdf
   ```
   Scroll through. Any visual glitch not attributable to a specific warning? Those are the silent failures — Steps 6–8 catch them.

### The circuit breaker — do not spiral

**If you have attempted 3 different approaches to fix the same compile error and it is not resolved, STOP.** Do not try a fourth. Instead:

1. **Stop editing the .tex file.**
2. **Quote the log line.**
3. **List the 3 approaches and why each failed.**
4. **Ask the user how to proceed.**

The cost of stopping is 2 minutes. The cost of spiraling is an hour of edits that make the file progressively worse. After 3 attempts, the file is harder to fix than it was before. The user can diagnose the root cause or simplify the slide.

**What counts as "the same error":** any error that persists at the same line (or moves to a nearby line) after your fix. "Illegal parameter number" that moves from 568 to 572 is the same error. An Overfull that appears on a different slide after fixing the first is a new error — reset the counter.

**This rule overrides "recompile until clean."** Zero tolerance for warnings is the goal, but it does not mean infinite attempts. Fix what you can fix; ask for help on what you cannot.

### Zero tolerance at every checkpoint

Multiple compile checkpoints:
- After Step 4 (first draft)
- After Step 6 (post `/tikz`)
- After Step 7 (post rhetoric audit)
- After Step 8 (post graphics audit)
- Step 9 (final)

**At each checkpoint, the full compile check must pass with zero warnings before proceeding.**

### The final-compile gate

Before handing over in Step 10, run the compile check one last time. If anything is nonzero, go back and fix. Do not rationalize, do not explain it away, do not ship with known warnings.

---

## Step 6: Visual Cleanup — Invoke `/tikz`

LaTeX warnings catch box overflow. They do NOT catch:
- TikZ label collisions with arrows, boxes, or other labels
- ggplot2 / matplotlib labels clipped at figure boundaries
- Coordinate misalignment in custom diagrams
- Text bleeding into patches or shapes

Run `/tikz <deck>.tex` to audit every TikZ figure using measurement-based collision prevention. The skill will compute Bézier depths, text-width vs. node-gap, boundary clearances, and report collisions with line numbers. Apply all suggested fixes and go back to Step 5.

---

## Step 7: Rhetoric Audit — Second Agent

Dispatch a sub-agent (via Task) to evaluate the deck. Task prompt:

> You are Referee 2 in rhetoric-review mode. Audit the Beamer deck at `<deck>.tex` and its compiled PDF at `<deck>.pdf`. Check specifically:
>
> 1. **Titles are assertions.** Read titles in sequence. Do they tell a coherent story? List any title that is a label rather than an assertion, with suggested rewrite.
> 2. **One idea per slide.** List any slide with two or more competing ideas.
> 3. **No wall of sentences.** List any slide with more than two prose sentences stacked vertically.
> 4. **MB/MC equivalence.** Rate each slide's density 1–5. Flag outliers.
> 5. **Narrative arc.** Does the deck have a clear Setup / Development / Resolution? Does the opening hook land? Does the deck end on a plain conclusion that restates the results, rather than a slogan or a single-sentence closer?
> 6. **Devil's Advocate.** Is there a slide addressing the strongest objection? Academic or external contexts require this.
> 7. **Audience fit.** Does the rhetorical balance (ethos/pathos/logos) match the audience declared at Step 0?
> 8. **Pedagogical movement (for teaching decks only).** Does each section move Narrative → Application → Picture → Codeblock → Technical, or are technicals arriving before the intuition that motivates them?
>
> Return a structured report with numbered concerns and suggested rewrites. Do NOT modify the deck source — only diagnose. The main agent applies fixes.

Apply every Major concern and as many Minor concerns as feasible, then back to Step 5.

---

## Step 8: Graphics Audit — Third Agent

Dispatch a second sub-agent focused ONLY on graphics. This is the step most often skipped. Graphics errors don't trigger LaTeX warnings and don't show up in rhetoric audits.

> You are a graphics auditor. Audit ONLY the figures, tables, and TikZ diagrams in the compiled PDF at `<deck>.pdf`. Check specifically:
>
> 1. **Numerical accuracy.** For every figure or table, verify the numbers match the script output. Any mismatch is critical.
> 2. **Label positioning.** Are labels where they appear in the source code, or has the coordinate system drifted? For TikZ, verify intended coordinates match rendered. For ggplot2/matplotlib, verify axis labels, tick marks, legends, annotations are not clipped.
> 3. **Axis and tick coherence.** Sensible ranges? Tick marks at meaningful intervals? Readable labels?
> 4. **Color consistency.** Figure colors match the deck palette? Same colors for the same variables across figures?
> 5. **Font sizing.** Readable at the back of the room (18pt equivalent minimum)?
> 6. **Table formatting.** Booktabs rules only? Key coefficients highlighted? Decimals aligned?
> 7. **Figure captions.** Does every caption state what to conclude, not just what the figure is?
>
> Return a structured report with numbered concerns tied to specific file paths and line/coordinates. Do NOT modify any files.

Apply fixes, recompile (Step 5), re-run `/tikz` (Step 6). Typically where the last silent errors get caught.

---

## Step 9: Final Compile

Run the compile loop one last time. Required state:

- Zero compile errors
- Zero Overfull warnings
- Zero Underfull warnings
- Zero font warnings
- `/tikz` returns no collisions
- Rhetoric audit concerns all addressed
- Graphics audit concerns all addressed
- PDF opens and displays correctly

If anything fails, back to the relevant step. Do not hand over an unfinished audit. No cosmetic mistakes.

---

## Step 10: Deliver

Produce:
```
<deck_name>/
├── <deck_name>.tex
├── <deck_name>.pdf
├── <deck_name>_outline.md
├── preamble.tex              # if factored out
├── scripts/
│   ├── figure_1.R
│   └── ...
├── figures/
└── tables/
```

Report to the user:
- Path to compiled PDF
- Slide count
- Figures and tables generated
- Rhetoric audit summary (flagged / fixed)
- Graphics audit summary
- Remaining TODOs

## Reference: The Three Laws

Constants across every audience, every aesthetic, every deck:

1. **Beauty is function.** Beauty in presentation is clarity made visible. Decoration without function is noise. The most beautiful slide may be three words on a blank background.
2. **Cognitive load is the enemy.** One idea per slide. Two max for inseparable contrasts. If you need "also" or "additionally," you need a new slide.
3. **The slide serves the spoken word.** The slide is the visual anchor for what you say — not what you say. If your slides can be understood without you speaking, you have written a document and called it a presentation.

## Reference: The Aristotelian triad

- **Ethos (credibility).** *Why should I trust this person?* Lives in methodology slides, Devil's Advocate slides, honest scorecards, acknowledged limitations. Admitting weakness builds credibility.
- **Pathos (emotion).** *Why should I care?* Lives in opening hooks, stakes, human impact, aspiration. Pathos without logos is demagoguery.
- **Logos (logic).** *Does this make sense?* Lives in data visualizations, comparison tables, causal diagrams, the logical flow from problem to conclusion. Logos without pathos is a lecture.

The rhetorical balance depends on audience — see Q2 table.

---

## Supporting skills

- `/tikz` — the measurement-based visual collision audit. Invoked at Step 6.
- `/referee2` — the full five-audit protocol. Used in Step 7 rhetoric-review mode. Code mode does cross-language replication.
- `/split-pdf` — if source content is a paper being read, split first and work from summaries.
- `/blindspot` — peripheral-vision audit for findings you can't see in your own output. Complements `/referee2`.

## Shared references

- `~/.claude/references/latex_toolkit/tikz_rules.md` — authoritative TikZ collision math. Linked by `/tikz` and `/referee2` as well.
- `~/.claude/references/latex_toolkit/themes/` — the neutral theme.
- `~/.claude/references/rhetoric_of_decks/rhetoric_of_decks.md` — the operational philosophy. Condensed version.
- `~/.claude/references/rhetoric_of_decks/rhetoric_of_decks_full_essay.md` — the long-form genealogy from Aristotle through LLMs.
