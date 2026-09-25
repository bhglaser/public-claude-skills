#!/usr/bin/env python3
"""
validate.py -- blind held-out validation harness for a style guide.

Stdlib only. The test: take real paragraphs from a paper the guide was NOT
built from, reduce each to phrasing-free claim bullets, regenerate each paragraph
twice from the bullets only -- once with no guide (baseline) and once with the
guide (guided) -- then have several blind judges pick which candidate reads more
like the author's real paragraph. Guided should beat baseline well above 50%.

Subcommands (all files live in one validation directory, --dir):

  heldout  Sample N clean prose paragraphs from the held-out paper's chunks.
             validate.py heldout --chunks WORKDIR/chunks/heldout/<Paper>.jsonl --n 24 --dir WORKDIR/validation
  blind    Merge bullets + baseline + guided outputs, print objective tic metrics
           (author vs baseline vs guided), and write the blinded judge file + secret key.
             validate.py blind --dir WORKDIR/validation --tag v1
           expects bullets_*.jsonl, baseline_*.jsonl, guided_<tag>_*.jsonl in --dir
  decode   Decode judge votes against the key: win rate, per-item majority,
           unanimity, one-sided binomial p-value, and the items the guide lost.
             validate.py decode --dir WORKDIR/validation --tag v1
           expects judge_key_<tag>.json and votes_<tag>_*.jsonl in --dir
  viewer   Build a self-contained HTML results viewer across rounds.
             validate.py viewer --dir WORKDIR/validation --tags v1 v2 --name "Jane Doe"

Schemas:
  bullets_*.jsonl   {id, section, author, bullets:[str]}
  baseline_*.jsonl  {id, baseline}
  guided_<tag>_*.jsonl {id, guided}
  judge_items_<tag>.jsonl {id, reference, optionA, optionB}
  votes_<tag>_<j>.jsonl {id, choice:"A"|"B", reason}
"""
import argparse
import glob
import hashlib
import html
import json
import math
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stylemetrics import paragraph_metrics, read_jsonl, write_jsonl  # noqa: E402

MATH = re.compile(r"\\frac|\\mbox|\\begin\{|\\sum|\\int|=\s*&")


def load_field(pattern, field):
    d = {}
    files = sorted(glob.glob(pattern))
    for f in files:
        for r in read_jsonl(f):
            if field in r:
                d[r["id"]] = r[field]
    return d, files


# ------------------------------------------------------------------ heldout
def cmd_heldout(a):
    recs = read_jsonl(a.chunks)
    good = [r for r in recs if a.min_words <= r["n_words"] <= a.max_words and not MATH.search(r["text"])]
    if len(good) < a.n:
        print(f"warning: only {len(good)} usable paragraphs (wanted {a.n}); using all of them.")
    step = max(1, len(good) // a.n)
    sample = good[::step][:a.n]
    d = Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    write_jsonl(d / "heldout_chunks.jsonl", sample)
    print(f"held-out chunks: {len(recs)} total, {len(good)} usable, {len(sample)} sampled evenly "
          f"-> {d / 'heldout_chunks.jsonl'}")
    if sample:
        print(f"word range: {min(r['n_words'] for r in sample)}-{max(r['n_words'] for r in sample)}; "
              f"sections: {sorted(set(r['section'] for r in sample if r['section']))[:8]}")


# ------------------------------------------------------------------ blind
FIELDS = [("mean_sent_len", "mean words/sentence"), ("frac_we_open", "frac sentences opening 'We'"),
          ("suppose", "'Suppose'"), ("because_initial", "sentence-initial 'Because'"),
          ("payoff_colon", "payoff colons"), ("pseudocleft", "pseudo-cleft markers"),
          ("dramatizers", "dramatizers"), ("escalated_verbs", "escalated verbs"),
          ("em_dash", "em-dashes"), ("semicolon", "semicolons")]


def cmd_blind(a):
    d = Path(a.dir)
    bul = {}
    bfiles = sorted(glob.glob(str(d / "bullets_*.jsonl")))
    for f in bfiles:
        for r in read_jsonl(f):
            bul[r["id"]] = r
    base, _ = load_field(str(d / "baseline_*.jsonl"), "baseline")
    guid, gfiles = load_field(str(d / f"guided_{a.tag}_*.jsonl"), "guided")
    if not bul or not base or not guid:
        sys.exit(f"need bullets_*.jsonl ({len(bfiles)} found), baseline_*.jsonl ({len(base)} ids), "
                 f"guided_{a.tag}_*.jsonl ({len(gfiles)} files) in {d}")
    ids = [i for i in bul if i in base and i in guid]
    missing = [i for i in bul if i not in ids]
    cand = [{"id": i, "section": bul[i].get("section", ""), "author": bul[i]["author"],
             "bullets": bul[i]["bullets"], "baseline": base[i], "guided": guid[i]} for i in ids]
    write_jsonl(d / f"candidates_{a.tag}.jsonl", cand)
    print(f"merged {len(cand)} complete triples -> candidates_{a.tag}.jsonl"
          + (f"  (incomplete, skipped: {missing})" if missing else ""))

    print(f"\n{'metric (mean per paragraph)':32s} {'author':>8} {'baseline':>9} {'guided':>8}  guided closer?")
    print("-" * 74)
    for key, label in FIELDS:
        vals = {c: statistics.mean(paragraph_metrics(r[c])[key] for r in cand)
                for c in ("author", "baseline", "guided")}
        b, bl, g = vals["author"], vals["baseline"], vals["guided"]
        mark = "=" if abs(abs(g - b) - abs(bl - b)) < 1e-9 else ("YES" if abs(g - b) < abs(bl - b) else "no")
        print(f"{label:32s} {b:8.2f} {bl:9.2f} {g:8.2f}  {mark}")
    print("Watch mean words/sentence: if guided is far BELOW the author, the guide is over-chopping.")

    key, items = {}, []
    for r in cand:
        h = int(hashlib.sha256(f"{a.tag}:{r['id']}".encode()).hexdigest(), 16)
        A, B = ("baseline", "guided") if h % 2 == 0 else ("guided", "baseline")
        key[r["id"]] = {"A": A, "B": B}
        items.append({"id": r["id"], "reference": r["author"], "optionA": r[A], "optionB": r[B]})
    write_jsonl(d / f"judge_items_{a.tag}.jsonl", items)
    (d / f"judge_key_{a.tag}.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    nA = sum(1 for v in key.values() if v["A"] == "guided")
    print(f"\nwrote judge_items_{a.tag}.jsonl ({len(items)} items; guided is option A in {nA}) "
          f"and judge_key_{a.tag}.json. Never give the key to a judge.")


# ------------------------------------------------------------------ decode
def binom_tail(k, n):
    """P(X >= k) for X ~ Binomial(n, 0.5)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


def decode_round(d, tag):
    key = json.loads((d / f"judge_key_{tag}.json").read_text(encoding="utf-8"))
    vfiles = sorted(glob.glob(str(d / f"votes_{tag}_*.jsonl")))
    if not vfiles:
        sys.exit(f"no votes_{tag}_*.jsonl in {d}")
    per = {i: [] for i in key}
    judges = []
    for jn, f in enumerate(vfiles, 1):
        c = Counter()
        for r in read_jsonl(f):
            i, ch = r.get("id"), str(r.get("choice", "")).strip().upper()
            if i not in key or ch not in ("A", "B"):
                continue
            pick = key[i][ch]
            c[pick] += 1
            per[i].append({"judge": jn, "pick": pick, "reason": r.get("reason", "")})
        judges.append((Path(f).name, c))
    return key, per, judges


def cmd_decode(a):
    d = Path(a.dir)
    key, per, judges = decode_round(d, a.tag)
    nj = len(judges)
    print(f"round {a.tag}: {len(key)} items x {nj} judges\n")
    for name, c in judges:
        print(f"  {name:28s} guided={c['guided']:3d}  baseline={c['baseline']:3d}")
    g = sum(c["guided"] for _, c in judges)
    b = sum(c["baseline"] for _, c in judges)
    tot = g + b
    print(f"\nOVERALL: guided {g} / {tot} judgments = {g / max(tot, 1):.0%} guided win rate")
    gcount = {i: sum(v["pick"] == "guided" for v in per[i]) for i in key}
    need = nj // 2 + 1
    maj = sum(1 for i in key if gcount[i] >= need)
    n = len(key)
    print(f"per-item majority: guided wins {maj} / {n} "
          f"(one-sided binomial p = {binom_tail(maj, n):.3f} vs a coin-flip guide)")
    una_g = sum(1 for i in key if gcount[i] == nj)
    una_b = sum(1 for i in key if gcount[i] == 0)
    print(f"unanimous guided: {una_g} | unanimous baseline: {una_b} | split: {n - una_g - una_b}")
    if una_g + una_b < n * 0.6:
        print("note: judges disagree a lot -- the style difference is weak or the judge prompt is unclear.")
    lost = [i for i in key if gcount[i] < need]
    print(f"\nitems where baseline beat guided ({len(lost)}): inspect these to refine the guide")
    for i in lost:
        reasons = "; ".join(v["reason"] for v in per[i] if v["pick"] == "baseline")[:160]
        print(f"  {i}  ({gcount[i]}/{nj} guided)  {reasons}")
    write_jsonl(d / f"decoded_{a.tag}.jsonl",
                [{"id": i, "guided_votes": gcount[i], "n_judges": nj, "votes": per[i]} for i in key])
    print(f"\nwrote decoded_{a.tag}.jsonl")


# ------------------------------------------------------------------ viewer
VIEWER = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Style validation results</title><style>
:root{--bg:#faf9f7;--fg:#1a1a1a;--card:#fff;--line:#e3e0da;--accent:#8a5a2b;--muted:#6f6a62;--win:#2f7d4f;--winbg:#e7f4ec;--lose:#a23c3c;--losebg:#f7e9e9;--ref:#3a4a6b;--refbg:#eef1f7}
@media(prefers-color-scheme:dark){:root{--bg:#1a1917;--fg:#ece9e3;--card:#232220;--line:#3a3733;--accent:#d6a56a;--muted:#a39d92;--win:#7fd6a0;--winbg:#1e2f24;--lose:#e79a9a;--losebg:#2f2020;--ref:#a8bde6;--refbg:#20242e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 Georgia,serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;z-index:5}
h1{font:600 18px system-ui,sans-serif;margin:0 0 10px}.stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px;font:12px system-ui,sans-serif;color:var(--muted)}
.stat b{display:block;font:700 24px system-ui,sans-serif;color:var(--fg)}
.controls{display:flex;gap:8px;flex-wrap:wrap;font:13px system-ui,sans-serif;align-items:center}
select{font:13px system-ui,sans-serif;padding:5px 8px;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px}
.wrap{max-width:1180px;margin:0 auto;padding:16px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:0 0 16px;overflow:hidden}
.chead{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;padding:8px 14px;border-bottom:1px solid var(--line);font:12px system-ui,sans-serif;color:var(--muted)}
.badge{font:600 11px system-ui,sans-serif;padding:2px 8px;border-radius:20px;margin-left:4px}.w{background:var(--winbg);color:var(--win)}.l{background:var(--losebg);color:var(--lose)}
.ref{background:var(--refbg);border-left:3px solid var(--ref);padding:12px 16px}
.lbl{font:700 11px system-ui,sans-serif;letter-spacing:.05em;text-transform:uppercase;margin-bottom:5px;color:var(--accent)}
.len{font:400 10px system-ui,sans-serif;color:var(--muted);text-transform:none}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}.col{padding:12px 16px;border-top:1px solid var(--line)}
.notes{border-top:1px dashed var(--line);padding:10px 16px;font:12px/1.4 system-ui,sans-serif;color:var(--muted)}
</style></head><body><header><h1>%%NAME%% &mdash; blind held-out validation</h1><div class=stats id=stats></div>
<div class=controls>Round <select id=round></select> Filter <select id=filter><option value=all>all</option><option value=win>guided won</option><option value=lose>baseline won</option></select></div></header>
<div class=wrap id=list></div><script>
const D=%%DATA%%;const $=s=>document.querySelector(s);const esc=s=>(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
$('#stats').innerHTML=D.rounds.map(r=>`<div class=stat><b>${r.rate}%</b>${esc(r.tag)} guided win rate<br>${r.maj}/${r.n} items &middot; ${r.len} w/sent</div>`).join('')+`<div class=stat><b>${D.len_author}</b>author w/sent<br>baseline ${D.len_base}</div>`;
D.rounds.forEach(r=>{const o=document.createElement('option');o.value=o.textContent=r.tag;$('#round').appendChild(o)});$('#round').value=D.rounds[D.rounds.length-1].tag;
function render(){const t=$('#round').value,f=$('#filter').value;let rows=D.items.filter(x=>x.r[t]);
rows=rows.filter(x=>{const w=x.r[t].g>x.r[t].nj/2;return f=='all'||(f=='win'?w:!w)});
$('#list').innerHTML=rows.map(x=>{const R=x.r[t];const w=R.g>R.nj/2;
const others=D.rounds.filter(r=>r.tag!=t&&x.r[r.tag]).map(r=>`<span class="badge ${x.r[r.tag].g>x.r[r.tag].nj/2?'w':'l'}">${esc(r.tag)}: ${x.r[r.tag].g}/${x.r[r.tag].nj}</span>`).join('');
return `<div class=card><div class=chead><span><b>${esc(x.id)}</b> ${esc(x.section)}</span><span><span class="badge ${w?'w':'l'}">${esc(t)}: guided ${R.g}/${R.nj}</span>${others}</span></div>
<div class=ref><div class=lbl>Author (reference) <span class=len>${x.len} w/sent</span></div>${esc(x.author)}</div>
<div class=cols><div class=col><div class=lbl>Baseline <span class=len>${x.len_base} w/sent</span></div>${esc(x.baseline)}</div>
<div class=col><div class=lbl>Guided ${esc(t)} <span class=len>${R.len} w/sent</span></div>${esc(R.guided)}</div></div>
<div class=notes>${R.votes.map(v=>`J${v.judge} &rarr; ${v.pick}: ${esc(v.reason)}`).join('<br>')}</div></div>`}).join('')}
['#round','#filter'].forEach(s=>$(s).addEventListener('change',render));render();
</script></body></html>"""


def cmd_viewer(a):
    d = Path(a.dir)
    items, rounds = {}, []
    for tag in a.tags:
        cand = {r["id"]: r for r in read_jsonl(d / f"candidates_{tag}.jsonl")}
        dec = {r["id"]: r for r in read_jsonl(d / f"decoded_{tag}.jsonl")}
        for i, c in cand.items():
            it = items.setdefault(i, {"id": i, "section": c.get("section", ""), "author": c["author"],
                                      "baseline": c["baseline"], "r": {}})
            dr = dec.get(i, {"guided_votes": 0, "n_judges": 0, "votes": []})
            it["r"][tag] = {"guided": c["guided"], "g": dr["guided_votes"], "nj": dr["n_judges"],
                            "votes": dr["votes"], "len": paragraph_metrics(c["guided"])["mean_sent_len"]}
        tot = sum(r["guided_votes"] for r in dec.values())
        den = sum(r["n_judges"] for r in dec.values()) or 1
        rounds.append({"tag": tag, "rate": round(100 * tot / den), "n": len(dec),
                       "maj": sum(1 for r in dec.values() if r["guided_votes"] > r["n_judges"] / 2),
                       "len": round(statistics.mean(paragraph_metrics(c["guided"])["mean_sent_len"]
                                                    for c in cand.values()), 1)})
    for it in items.values():
        it["len"] = paragraph_metrics(it["author"])["mean_sent_len"]
        it["len_base"] = paragraph_metrics(it["baseline"])["mean_sent_len"]
    vals = list(items.values())
    data = {"rounds": rounds, "items": vals,
            "len_author": round(statistics.mean(v["len"] for v in vals), 1),
            "len_base": round(statistics.mean(v["len_base"] for v in vals), 1)}
    page = VIEWER.replace("%%DATA%%", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")) \
                 .replace("%%NAME%%", html.escape(a.name))
    out = d / "results_viewer.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}: " + ", ".join(f"{r['tag']} {r['rate']}%" for r in rounds))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("heldout", help="sample held-out paragraphs")
    p.add_argument("--chunks", required=True, help="chunks jsonl of the held-out paper")
    p.add_argument("--dir", required=True)
    p.add_argument("--n", type=int, default=24)
    p.add_argument("--min-words", type=int, default=60)
    p.add_argument("--max-words", type=int, default=220)
    p.set_defaults(fn=cmd_heldout)
    for name, fn, h in (("blind", cmd_blind, "build blinded judge items for a round"),
                        ("decode", cmd_decode, "decode votes for a round")):
        p = sp.add_parser(name, help=h)
        p.add_argument("--dir", required=True)
        p.add_argument("--tag", required=True, help="round label, e.g. v1, v2")
        p.set_defaults(fn=fn)
    p = sp.add_parser("viewer", help="HTML results viewer across rounds")
    p.add_argument("--dir", required=True)
    p.add_argument("--tags", nargs="+", required=True)
    p.add_argument("--name", default="Author")
    p.set_defaults(fn=cmd_viewer)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
