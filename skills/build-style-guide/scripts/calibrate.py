#!/usr/bin/env python3
"""
calibrate.py -- measure the author's real style frequencies so the guide can
state calibrated tendencies ("~0.7 per 1k words") instead of absolutes ("never").

Stdlib only. Reads the filtered pair file (compares the `author` column to the
`llm` column) or a plain chunks file (author only, `text` column).

  python3 calibrate.py WORKDIR/pairs/all_pairs_filtered.jsonl
  python3 calibrate.py WORKDIR/pairs/all_pairs_filtered.jsonl --by-paper --md WORKDIR/calibration.md
  python3 calibrate.py WORKDIR/chunks/all.jsonl --author-field text
  python3 calibrate.py FILE --patterns my_patterns.json   # extra/replacement constructions

--patterns: JSON list of [label, regex] or [label, regex, "i"] (case-insensitive).
It REPLACES the default set; copy DEFAULT_PATTERNS from stylemetrics.py to extend.

Reading the output:
  * Sentence-length distribution: mean/median/stdev and short (<15) / mid (15-35) /
    long (>35) shares. This is the most important calibration target; state it
    in the guide with numbers.
  * Construction rates per 1,000 words, author vs LLM, with a verdict:
      AVOID      author ~never uses it (< 0.1/1k) but the LLM does -> safe blacklist item
      LLM-TIC    LLM uses it >= 2x as often -> "use less / sparingly (author: X/1k)"
      AUTHOR     author uses it >= 2x as often -> "keep / use more (author: X/1k)"
      similar    not a discriminator -> do not write a rule about it
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stylemetrics import load_patterns, rate_per_1k, read_jsonl, sentence_lengths, words  # noqa: E402


def dist(texts):
    L = [n for t in texts for n in sentence_lengths(t)]
    if not L:
        return None
    s = sorted(L)
    n = len(L)
    return {
        "n_sentences": n,
        "n_words": sum(len(words(t)) for t in texts),
        "mean": round(statistics.mean(L), 1),
        "median": statistics.median(L),
        "stdev": round(statistics.pstdev(L), 1),
        "p10": s[n // 10],
        "p90": s[n * 9 // 10],
        "max": s[-1],
        "short_lt15": round(sum(x < 15 for x in L) / n, 3),
        "mid_15_35": round(sum(15 <= x <= 35 for x in L) / n, 3),
        "long_gt35": round(sum(x > 35 for x in L) / n, 3),
    }


def fmt_dist(label, d):
    return (f"{label:10s} n={d['n_sentences']:5d} sents  mean={d['mean']:5.1f}  median={d['median']:>4}  "
            f"stdev={d['stdev']:4.1f}  p10={d['p10']:2d}  p90={d['p90']:2d}  max={d['max']:3d}  |  "
            f"short {d['short_lt15']:.0%}  mid {d['mid_15_35']:.0%}  long {d['long_gt35']:.0%}")


def verdict(ra, rl):
    if ra < 0.1 and rl >= 0.15 and rl >= 3 * max(ra, 0.03):
        return "AVOID"
    if rl >= 2 * max(ra, 0.05) and rl - ra >= 0.2:
        return "LLM-TIC"
    if ra >= 2 * max(rl, 0.05) and ra - rl >= 0.2:
        return "AUTHOR"
    return "similar"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="all_pairs_filtered.jsonl or chunks jsonl")
    ap.add_argument("--author-field", default="author", help="default 'author' (use 'text' for chunks)")
    ap.add_argument("--llm-field", default="llm", help="default 'llm'; ignored if absent")
    ap.add_argument("--patterns", help="JSON pattern file (replaces defaults)")
    ap.add_argument("--by-paper", action="store_true", help="also report sentence length per paper")
    ap.add_argument("--md", help="also write a markdown report here")
    ap.add_argument("--json", help="also write machine-readable results here")
    a = ap.parse_args()

    recs = read_jsonl(a.file)
    if not recs:
        sys.exit("empty input")
    if a.author_field not in recs[0] and "text" in recs[0]:
        a.author_field = "text"
    A = [r[a.author_field] for r in recs if r.get(a.author_field)]
    has_llm = a.llm_field in recs[0]
    Lm = [r[a.llm_field] for r in recs if r.get(a.llm_field)] if has_llm else []

    out = []
    da = dist(A)
    out.append(f"# Calibration report ({len(A)} paragraphs, {da['n_words']:,} author words)\n")
    out.append("## Sentence length (words per sentence, pooled)\n")
    out.append("```")
    out.append(fmt_dist("author", da))
    dl = dist(Lm) if Lm else None
    if dl:
        out.append(fmt_dist("llm", dl))
    if a.by_paper:
        per = defaultdict(list)
        for r in recs:
            per[r.get("paper", "?")].append(r[a.author_field])
        for p, ts in per.items():
            out.append(fmt_dist(p[:10], dist(ts)) + f"   [{p}]")
    out.append("```\n")

    pats = load_patterns(a.patterns)
    out.append("## Construction frequency (per 1,000 words)\n")
    hdr = f"{'construction':62s} {'author':>7} {'/1k':>6}"
    if Lm:
        hdr += f" {'llm':>6} {'/1k':>6}  verdict"
    out.append("```")
    out.append(hdr)
    out.append("-" * len(hdr))
    rows = []
    for label, rx in pats:
        ca, ra = rate_per_1k(A, rx)
        line = f"{label[:62]:62s} {ca:7d} {ra:6.2f}"
        row = {"label": label, "author_count": ca, "author_per_1k": round(ra, 3)}
        if Lm:
            cl, rl = rate_per_1k(Lm, rx)
            v = verdict(ra, rl)
            line += f" {cl:6d} {rl:6.2f}  {v}"
            row.update(llm_count=cl, llm_per_1k=round(rl, 3), verdict=v)
        out.append(line)
        rows.append(row)
    out.append("```\n")
    if Lm:
        out.append("Verdict key: AVOID = author near-zero, LLM uses it (safe blacklist); "
                   "LLM-TIC = use sparingly, cite the author's rate; AUTHOR = the author's habit, keep it; "
                   "similar = not a discriminator, write no rule.")
        if dl and da:
            gap = dl["mean"] - da["mean"]
            out.append(f"\nMean sentence length gap (llm - author): {gap:+.1f} words. "
                       "Encode the author's distribution in the guide; do NOT tell the writer to "
                       "'shorten' or 'lengthen' uniformly.")

    text = "\n".join(out)
    print(text)
    if a.md:
        Path(a.md).write_text(text + "\n", encoding="utf-8")
        print(f"\nwrote {a.md}")
    if a.json:
        Path(a.json).write_text(json.dumps({"author_dist": da, "llm_dist": dl, "constructions": rows},
                                           indent=2), encoding="utf-8")
        print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
