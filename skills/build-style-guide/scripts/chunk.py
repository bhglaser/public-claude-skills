#!/usr/bin/env python3
"""
chunk.py -- extract narrative prose paragraphs from papers into JSONL.

Stdlib only. PDF input shells out to `pdftotext` (poppler) if present, else
tries the `pypdf` package; LaTeX source is strongly preferred because PDF
extraction breaks paragraphs at page boundaries and mangles math.

For LaTeX it: expands \\input/\\include, strips comments, keeps only the
document body, cuts the appendix and bibliography (unless --keep-appendix),
removes display math, floats, and theorem/proof environments, and keeps inline
math ($...$) because it is part of the prose voice. It then drops paragraphs
that are too short, mostly symbols, math fragments leading into an equation,
or acknowledgments.

Usage:
  python3 chunk.py PAPER [PAPER ...] --out WORKDIR/chunks
  PAPER is a path to .tex/.pdf/.txt/.md, optionally prefixed "Name=" to set the
  short paper name used in ids (default: derived from the file or folder name).

  python3 chunk.py Signaling-2017=~/papers/sig/paper.tex \\
                   Capital-2019=~/papers/cap/main.tex  --out ~/style-guide-jane/chunks

Output: <out>/<Name>.jsonl per paper and <out>/all.jsonl (combined, unless
--no-combined). Each record: {id, paper, section, subsection, n_words, text}
with id = "<Name>:<NNN>".
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DROP_ENVS = [
    "equation", "align", "eqnarray", "gather", "multline", "flalign", "alignat",
    "math", "displaymath", "split", "cases", "array", "subequations",
    "table", "figure", "tabular", "tabularx", "longtable", "wraptable", "wrapfigure",
    "sidewaystable", "sidewaysfigure", "threeparttable", "tikzpicture", "verbatim", "lstlisting",
    "theorem", "thm", "lemma", "lem", "proposition", "prop", "corollary", "cor",
    "definition", "defn", "def", "assumption", "ass", "axiom", "claim", "remark",
    "proof", "example", "conjecture", "hypothesis",
    "acknowledgments", "acknowledgements", "acknowledgment", "acknowledgement",
]

NOISE_LINE = re.compile(
    r"^\s*\\(section|subsection|subsubsection|paragraph|label|ref|input|include|"
    r"centering|caption|item|maketitle|title|author|date|thanks|abstract|"
    r"newpage|clearpage|pagebreak|vspace|hspace|noindent|bigskip|medskip|smallskip|"
    r"begin|end|footnotesize|small|normalsize|large|bibliographystyle|setcounter|"
    r"keywords|JEL|jel|tableofcontents|singlespacing|doublespacing|onehalfspacing)"
)

MATH_FRAGMENT = re.compile(r"\\frac|\\mbox|\\begin\{|=\s*&|\\sum|\\int|\\\\\s*$")
ACK = re.compile(
    r"^(we|i) (thank|gratefully|are grateful|am grateful|would like to thank)|"
    r"anonymous referee|seminar participants|financial support from|"
    r"\\(tnotetext|thanks)\{", re.I)


# ----------------------------------------------------------------- LaTeX
def strip_comments(tex):
    return re.sub(r"(?<!\\)%.*", "", tex)


def expand_inputs(tex, base, depth=0):
    if depth > 5:
        return tex

    def repl(m):
        name = m.group(2).strip()
        cand = [base / name, base / (name + ".tex")]
        for c in cand:
            if c.is_file():
                sub = strip_comments(c.read_text(encoding="utf-8", errors="replace"))
                return expand_inputs(sub, c.parent, depth + 1)
        return " "
    return re.sub(r"\\(input|include)\{([^}]*)\}", repl, tex)


def body_only(tex, keep_appendix=False):
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", tex, flags=re.DOTALL)
    body = m.group(1) if m else tex
    markers = [r"\bibliography", r"\begin{thebibliography}", r"\printbibliography"]
    if not keep_appendix:
        markers = [r"\appendix", r"\begin{appendix}", r"\begin{appendices}"] + markers
    cut = min([i for i in (body.find(mk) for mk in markers) if i != -1], default=-1)
    return body[:cut] if cut != -1 else body


def strip_envs(text):
    for env in DROP_ENVS:
        for e in (re.escape(env), re.escape(env + "*")):
            text = re.sub(r"\\begin\{" + e + r"\}.*?\\end\{" + e + r"\}", "\n\n", text, flags=re.DOTALL)
    text = re.sub(r"\\\[.*?\\\]", " ", text, flags=re.DOTALL)
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.DOTALL)
    # drop \thanks{...} / \tnotetext[..]{...} (one level of nested braces)
    text = re.sub(r"\\(thanks|tnotetext(\[[^\]]*\])?)\{(?:[^{}]|\{[^{}]*\})*\}", " ", text)
    return text


def clean_para(p):
    kept = [ln for ln in p.splitlines() if not NOISE_LINE.match(ln)]
    return re.sub(r"\s+", " ", " ".join(kept)).strip()


def _braced(s, i):
    """Return the contents of the balanced {...} group starting at s[i] == '{'."""
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return s[i + 1:j]
    return s[i + 1:]


def section_marks(body):
    marks = []
    for m in re.finditer(r"\\(section|subsection)\*?(\[[^\]]*\])?\{", body):
        title = _braced(body, m.end() - 1)
        title = re.sub(r"\\label\{[^}]*\}", "", title)
        title = re.sub(r"\\[A-Za-z]+\*?", "", title).replace("{", "").replace("}", "")
        marks.append((m.start(), m.group(1), re.sub(r"\s+", " ", title).strip()))
    return marks


def section_at(marks, pos):
    sec = sub = ""
    for p, kind, title in marks:
        if p > pos:
            break
        if kind == "section":
            sec, sub = title, ""
        else:
            sub = title
    return sec, sub


def tex_paragraphs(path, keep_appendix):
    tex = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
    tex = expand_inputs(tex, path.parent)
    body = body_only(tex, keep_appendix)
    marks = section_marks(body)
    cleaned = strip_envs(body)
    out, cursor = [], 0
    for raw in re.split(r"\n\s*\n", cleaned):
        # locate the paragraph by its first prose line (skips \section etc.)
        prose = [ln.strip() for ln in raw.splitlines() if ln.strip() and not NOISE_LINE.match(ln)]
        s = prose[0] if prose else raw.strip()
        pos = body.find(s[:40]) if s else -1
        pos = pos if pos != -1 else cursor
        cursor = max(cursor, pos)
        sec, sub = section_at(marks, pos)
        out.append((clean_para(raw), sec, sub))
    return out


# ----------------------------------------------------------------- PDF / text
def pdf_text(path):
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
    try:
        from pypdf import PdfReader  # optional dependency
        return "\n\n".join((pg.extract_text() or "") for pg in PdfReader(str(path)).pages)
    except ImportError:
        sys.exit("PDF input needs `pdftotext` (brew install poppler) or `pip install pypdf`. "
                 "Better: use the paper's .tex source.")


def plain_paragraphs(text, keep_appendix):
    text = text.replace("\f", "\n\n")
    # cut at References / Appendix headings
    stops = [r"^\s*(References|Bibliography)\s*$"]
    if not keep_appendix:
        stops.append(r"^\s*(Appendix|Appendices|A\s+Appendix|Online Appendix)\b.*$")
    for pat in stops:
        m = re.search(pat, text, flags=re.M | re.I)
        if m and m.start() > len(text) * 0.3:   # ignore TOC-like early hits
            text = text[:m.start()]
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # de-hyphenate line breaks
    paras = []
    for raw in re.split(r"\n\s*\n", text):
        lines = [ln.strip() for ln in raw.splitlines()
                 if ln.strip() and not re.fullmatch(r"\s*\d{1,3}\s*", ln)]
        for block in split_short_lines(lines):
            paras.append((re.sub(r"\s+", " ", " ".join(block)).strip(), "", ""))
    return paras


def split_short_lines(lines):
    """PDF text often runs paragraphs together; a line that ends a sentence and is
    clearly shorter than the typical line is treated as a paragraph end."""
    if len(lines) < 6:
        return [lines]
    typical = sorted(len(ln) for ln in lines)[len(lines) * 3 // 4]
    blocks, cur = [], []
    for ln in lines:
        cur.append(ln)
        if re.search(r"[.?!]['\")]?$", ln) and len(ln) < 0.7 * typical:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


# ----------------------------------------------------------------- filters
def looks_like_prose(p, min_words):
    w = p.split()
    if len(w) < min_words:
        return False
    if sum(c.isalpha() for c in p) < 0.5 * len(p):
        return False
    return sum(1 for x in w if x[:1].islower() and x.isalpha()) >= 10


def keep(p, args):
    if not looks_like_prose(p, args.min_words):
        return False
    if not args.keep_math_fragments and MATH_FRAGMENT.search(p):
        return False
    if ACK.search(p):
        return False
    return True


def default_name(path):
    stem = path.stem
    if stem.lower() in ("paper", "main", "manuscript", "draft", "ms"):
        stem = path.parent.name
    return re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-") or "paper"


def chunk_file(spec, args):
    name, _, p = spec.partition("=") if "=" in spec and not Path(spec).exists() else ("", "", spec)
    path = Path(p).expanduser()
    if not path.is_file():
        sys.exit(f"not found: {path}")
    name = name or default_name(path)
    suf = path.suffix.lower()
    if suf == ".tex":
        paras = tex_paragraphs(path, args.keep_appendix)
    elif suf == ".pdf":
        paras = plain_paragraphs(pdf_text(path), args.keep_appendix)
    else:
        paras = plain_paragraphs(path.read_text(encoding="utf-8", errors="replace"), args.keep_appendix)
    recs = []
    for text, sec, sub in paras:
        if not keep(text, args):
            continue
        recs.append({"id": f"{name}:{len(recs) + 1:03d}", "paper": name, "section": sec,
                     "subsection": sub, "n_words": len(text.split()), "text": text})
    return name, recs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("papers", nargs="+", help="[Name=]path to .tex/.pdf/.txt/.md")
    ap.add_argument("--out", required=True, help="output directory (e.g. WORKDIR/chunks)")
    ap.add_argument("--min-words", type=int, default=30, help="drop paragraphs shorter than this (default 30)")
    ap.add_argument("--keep-appendix", action="store_true", help="do not cut the appendix")
    ap.add_argument("--keep-math-fragments", action="store_true",
                    help="keep paragraphs containing \\frac, \\sum, \\begin{...} etc.")
    ap.add_argument("--no-combined", action="store_true", help="do not write all.jsonl")
    args = ap.parse_args()

    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    all_recs, summary = [], []
    for spec in args.papers:
        name, recs = chunk_file(spec, args)
        with open(out / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        all_recs += recs
        summary.append((name, len(recs), sum(r["n_words"] for r in recs)))
    if not args.no_combined:
        with open(out / "all.jsonl", "w", encoding="utf-8") as f:
            for r in all_recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"{'paper':32s} {'chunks':>6} {'words':>7} {'avg':>5}")
    print("-" * 54)
    for n, c, w in summary:
        print(f"{n:32s} {c:6d} {w:7d} {w // max(c, 1):5d}")
    tn, tw = sum(s[1] for s in summary), sum(s[2] for s in summary)
    print("-" * 54)
    print(f"{'TOTAL':32s} {tn:6d} {tw:7d} {tw // max(tn, 1):5d}")
    print(f"\nwrote one <Name>.jsonl per paper" + ("" if args.no_combined else " + all.jsonl") + f" in {out}/")
    if tn < 150 and not args.no_combined:
        print("note: fewer than ~150 paragraphs -- consider adding papers for a sturdier signal.")


if __name__ == "__main__":
    main()
