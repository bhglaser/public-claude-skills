#!/usr/bin/env python3
"""Shared helpers for the build-style-guide scripts (stdlib only).

Imported by calibrate.py, pairs.py, and validate.py. Not meant to be run
directly, but `python3 stylemetrics.py "some text"` prints the metrics for a
string, which is handy for spot checks.
"""
import json
import re
import sys
from pathlib import Path

WORD = re.compile(r"[A-Za-z]+")

# Abbreviations whose trailing period should not end a sentence.
_ABBREV = re.compile(
    r"\b(i\.e|e\.g|cf|et al|etc|vs|Fig|Figs|Eq|Eqs|Sec|Secs|Tab|App|No|Prop|Thm|Def|Dr|Mr|Ms|Mrs|Prof|St)\.",
    re.I,
)
_PLACEHOLDER = "⁣"  # invisible separator, never appears in real text


def sentences(text):
    """Split a paragraph into sentences, protecting common abbreviations."""
    t = _ABBREV.sub(lambda m: m.group(0)[:-1] + _PLACEHOLDER, text.strip())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\\$(\[`\"'])", t)
    return [p.replace(_PLACEHOLDER, ".") for p in parts if p.strip()]


def words(text):
    return WORD.findall(text)


def sentence_lengths(text):
    out = []
    for s in sentences(text):
        n = len(words(s))
        if n:
            out.append(n)
    return out


def toks(text):
    return [w.lower() for w in words(text)]


def word_similarity(a, b):
    """Word-level SequenceMatcher ratio (0 = totally different, 1 = identical)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, toks(a), toks(b)).ratio()


SENT_START = r"(?:^|(?<=[.!?]\s))"
DRAMA = r"\b(Importantly|Crucially|Notably|In short|Strikingly|Remarkably),"
PSEUDOCLEFT = r"\b(the key (to|is)|what matters|is what \w+|this is why|it is \w+ that)\b"
ESCALATED = r"\b(collaps\w*|underscor\w*|pinned down|widen\w*|corroborat\w*|amplif\w*)\b"

# Default construction patterns. Each: (label, regex, flags).
# These are *general* academic-prose features plus common default-LLM tics.
# Extend or override with --patterns FILE (JSON list of [label, regex, flags_str]).
DEFAULT_PATTERNS = [
    # openings
    ("sentence-initial 'We'", SENT_START + r"We\b", 0),
    ("sentence-initial 'I'", SENT_START + r"I\b", 0),
    ("sentence-initial 'This/These'", SENT_START + r"(This|These)\b", 0),
    ("sentence-initial 'Because'", SENT_START + r"Because\b", 0),
    ("sentence-initial 'If'", SENT_START + r"If\b", 0),
    ("'Suppose'", r"\bSuppose\b", 0),
    ("'Consider' opening", SENT_START + r"Consider\b", 0),
    ("'Note that'", r"\bNote that\b", re.I),
    # connectives (plain)
    ("'Thus,'", r"\bThus,", 0),
    ("'However,'", r"\bHowever,", 0),
    ("'Therefore,'", r"\bTherefore,", 0),
    ("'As a result,'", r"\bAs a result,", 0),
    ("'In particular,'", r"\bIn particular,", 0),
    ("'In other words,'", r"\bIn other words,", 0),
    ("'For example,'", r"\bFor example,", 0),
    ("'i.e.'", r"\bi\.e\.", 0),
    ("'e.g.'", r"\be\.g\.", 0),
    # connectives (upgraded / LLM-leaning)
    ("'Hence'", r"\bHence\b", 0),
    ("'Consequently'", r"\bConsequently\b", 0),
    ("'Moreover,'/'Furthermore,'", r"\b(Moreover|Furthermore),", 0),
    ("'that is,'", r"\bthat is,", re.I),
    ("'for instance'", r"\bfor instance\b", re.I),
    ("'To illustrate'", r"\bTo illustrate\b", 0),
    ("dramatizers (Importantly/Crucially/Notably/In short)",
     DRAMA, 0),
    ("pseudo-cleft (the key/what matters/is what/this is why)",
     PSEUDOCLEFT, re.I),
    ("escalated verbs (collapse/underscore/pinned down/widen/corroborate)",
     ESCALATED, re.I),
    # flowing connectors
    ("'so that'", r"\bso that\b", re.I),
    ("'whereas'", r"\bwhereas\b", re.I),
    ("'because' (anywhere)", r"\bbecause\b", re.I),
    ("'since' (anywhere)", r"\bsince\b", re.I),
    ("'although'", r"\balthough\b", re.I),
    # punctuation
    ("payoff colon (word: lowercase)", r"[a-z]:\s+[a-z]", 0),
    ("em-dash (--- or —)", r"---|—", 0),
    ("semicolon", r";", 0),
    ("parenthetical '('", r"\((?![^)]*\\)", 0),
    # surface
    ("'United States/Kingdom'", r"United States|United Kingdom", 0),
    ("'US'/'UK'", r"\bU\.?S\.?\b|\bU\.?K\.?\b", 0),
]


def load_patterns(path=None):
    if not path:
        return [(l, re.compile(p, f)) for l, p, f in DEFAULT_PATTERNS]
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for item in raw:
        label, pat = item[0], item[1]
        flags = re.I if (len(item) > 2 and "i" in str(item[2]).lower()) else 0
        out.append((label, re.compile(pat, flags)))
    return out


def rate_per_1k(texts, rx):
    hits = sum(len(rx.findall(t)) for t in texts)
    n = sum(len(words(t)) for t in texts)
    return hits, (hits / n * 1000 if n else 0.0)


def paragraph_metrics(t):
    """Per-paragraph tic metrics used by validate.py."""
    ss = sentences(t)
    ns = len(ss) or 1
    L = sentence_lengths(t)
    return {
        "mean_sent_len": round(sum(L) / len(L), 1) if L else 0.0,
        "frac_we_open": round(sum(bool(re.match(r"\s*We\b", s)) for s in ss) / ns, 2),
        "suppose": len(re.findall(r"\bSuppose\b", t)),
        "because_initial": sum(bool(re.match(r"\s*Because\b", s)) for s in ss),
        "payoff_colon": len(re.findall(r"[a-z]:\s+[a-z]", t)),
        "pseudocleft": len(re.findall(PSEUDOCLEFT, t, re.I)),
        "dramatizers": len(re.findall(DRAMA, t)),
        "escalated_verbs": len(re.findall(ESCALATED, t, re.I)),
        "em_dash": t.count("---") + t.count("—"),
        "semicolon": t.count(";"),
    }


def read_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"{path}:{n}: invalid JSON ({e}). Fix or regenerate this file.")
    return out


def write_jsonl(path, recs):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("usage: stylemetrics.py \"paragraph text\"   (prints per-paragraph metrics)")
        sys.exit(0)
    txt = " ".join(sys.argv[1:])
    print(json.dumps({"sentence_lengths": sentence_lengths(txt), **paragraph_metrics(txt)}, indent=2))
