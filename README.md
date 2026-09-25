# Claude Code skills for finance academics

Skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that I (Barney Hartman-Glaser) use for writing papers, preparing conference discussions, and building slide decks. Colleagues asked for them, so here they are.

Several of these build on Scott Cunningham's [MixtapeTools](https://github.com/scunning1975/MixtapeTools). See [ATTRIBUTION.md](ATTRIBUTION.md) for what came from where.

## What's here

| Skill | What it does |
|---|---|
| `/discussion-init` | Sets up a folder for writing a conference discussion. Drop in the paper PDF and the invitation email (as a PDF) and run it. It pulls out the session logistics, reads the paper in depth, writes a `PAPER_GUIDE.md` (argument, contribution, notation key, discussion hooks), creates an empty `discussion_notes.md` for you, and builds a Beamer deck that teaches the paper back to you. The deck's TikZ diagrams are saved as separate files you can reuse in your actual discussion. |
| `/beautiful_deck` | Builds a Beamer deck end to end: audience-specific structure, assertion titles, figures generated from code, a zero-warning compile, TikZ collision checks, and separate audit passes for rhetoric and graphics. |
| `/build-style-guide` | Builds a calibrated style guide from **your own** papers and installs it as a `write-like-<you>` skill that drafts and edits prose in your voice. It pairs your real paragraphs with blind LLM versions of the same claims, measures the differences, and tests the guide on a paper it hasn't seen. Expect an hour or two and a lot of tokens. |
| `/split-pdf` | Reads long PDFs in 4-page chunks so Claude doesn't choke on a full paper. Used by `/discussion-init`. |
| `/tikz` | Finds and fixes overlapping labels and arrows in TikZ figures. Used by `/beautiful_deck`. |
| `/referee2` | Audit protocol for decks and for empirical code. Used by `/beautiful_deck`. |
| `/blindspot` | Looks for what you're not seeing in a figure or table. |

How they depend on each other:

```
discussion-init ──> split-pdf
       └──────────> beautiful_deck ──> tikz, referee2
build-style-guide ──> produces write-like-<you>
```

## Install

You need Claude Code, plus LaTeX (MacTeX on a Mac) for the deck skills.

```bash
git clone https://github.com/bhglaser/public-claude-skills.git
cd public-claude-skills
./install.sh
```

This copies the skills into `~/.claude/skills/` and the shared files (the Beamer theme, TikZ rules, and voice guide) into `~/.claude/references/`. Anything you already have with the same name is skipped. Use `./install.sh --force` to replace it (the old copy is kept as `*.bak-<date>`), or `./install.sh --list` to see what would happen. At the end the script checks for `pdftotext`, `pdflatex`, and `PyPDF2` and tells you how to install anything missing.

Then start a new Claude Code session and type `/discussion-init` (or any of the others).

To update later: `git pull && ./install.sh --force`.

## Using /discussion-init

1. Make a folder for the discussion.
2. Save the paper PDF and the invitation email (print it to PDF) into it.
3. Open Claude Code in that folder and run `/discussion-init`.

It asks you to confirm which PDF is which, then does the rest. Nothing you dropped in is renamed or deleted.

## Slide voice (optional)

`/beautiful_deck` checks its slide text against `~/.claude/references/voice/register-check.md`, a list of six habits that make LLM-written slides sound like LLM-written slides. When it flags a line, it asks **you** to rewrite it rather than rewriting it for you.

**The voice guide updates as you go.** Your rewrites are logged to `~/.claude/references/voice/captured.jsonl` on your machine. After each deck, `/beautiful_deck` offers to add the ones you choose to `register-check.md` as examples. The file starts with generic, invented examples; after a few decks it reflects how *you* fix slop.

If you also want to describe how you write slides, copy `voice-profile.template.md` in the same folder to `voice-profile.md` and fill it in. `/beautiful_deck` reads it when it exists.

## Caveats

- These reflect how I work. Take what's useful.
- The `write-like-<you>` skill that `/build-style-guide` produces is calibrated on journal prose, not emails or slides.
- The skills run a lot of subagents, and `/build-style-guide` and `/discussion-init` in particular use many tokens.
