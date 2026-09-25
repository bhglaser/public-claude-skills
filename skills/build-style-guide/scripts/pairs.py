#!/usr/bin/env python3
"""
pairs.py -- manage the (author paragraph, blind LLM paragraph) pair corpus.

Stdlib only. Subcommands:

  split   Split chunks/all.jsonl into batch input files for the pair-generation
          subagents (one subagent per batch).
            pairs.py split --chunks WORKDIR/chunks/all.jsonl --size 40 --out WORKDIR/pairs/in

  merge   Merge the subagents' batch outputs into all_pairs.jsonl, check the
          schema, check that `author` is verbatim from the chunks, list missing
          ids, and report author-vs-LLM word similarity.
            pairs.py merge --chunks WORKDIR/chunks/all.jsonl \\
                           --batches 'WORKDIR/pairs/batch_*.jsonl' --out WORKDIR/pairs/all_pairs.jsonl

  filter  Drop degenerate pairs (near-identical, math fragments, acknowledgments,
          too short) and add a `sim` field. Writes all_pairs_filtered.jsonl.
            pairs.py filter --in WORKDIR/pairs/all_pairs.jsonl --out WORKDIR/pairs/all_pairs_filtered.jsonl

  shard   Split the filtered pairs into N contiguous shards for the analyst subagents.
            pairs.py shard --in WORKDIR/pairs/all_pairs_filtered.jsonl --n 4 --out WORKDIR/analysis/in

  viewer  Build a self-contained side-by-side HTML viewer of the pairs.
            pairs.py viewer --in WORKDIR/pairs/all_pairs_filtered.jsonl --out WORKDIR/pairs/viewer.html --name "Jane"

Pair record schema: {id, paper, section, author, bullets: [str], llm, sim?}
"""
import argparse
import glob
import html
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stylemetrics import read_jsonl, toks, word_similarity, write_jsonl  # noqa: E402

REQUIRED = ("id", "paper", "author", "bullets", "llm")


def cmd_split(a):
    recs = read_jsonl(a.chunks)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in range(0, len(recs), a.size):
        n += 1
        write_jsonl(out / f"batch_{n:02d}.jsonl", recs[i:i + a.size])
    print(f"{len(recs)} chunks -> {n} batch input files of <= {a.size} in {out}/")
    print("Launch one pair-generation subagent per file (see references/prompts.md, Prompt A).")


def cmd_merge(a):
    files = sorted(glob.glob(str(Path(a.batches).expanduser())))
    if not files:
        sys.exit(f"no files match {a.batches}")
    src = {r["id"]: r for r in read_jsonl(a.chunks)}
    recs, seen, bad = [], set(), []
    for f in files:
        for r in read_jsonl(f):
            missing = [k for k in REQUIRED if not r.get(k)]
            if missing:
                bad.append((r.get("id", "?"), f"missing {missing}"))
                continue
            if r["id"] in seen:
                bad.append((r["id"], "duplicate"))
                continue
            seen.add(r["id"])
            recs.append(r)
    order = {k: i for i, k in enumerate(src)}
    recs.sort(key=lambda r: order.get(r["id"], 1e9))
    mism = [r["id"] for r in recs if r["id"] in src and src[r["id"]]["text"].strip() != r["author"].strip()]
    for r in recs:  # repair: always carry the verbatim source text
        if r["id"] in src:
            r["author"] = src[r["id"]]["text"]
            r.setdefault("section", src[r["id"]].get("section", ""))
    absent = [i for i in src if i not in seen]
    write_jsonl(a.out, recs)
    print(f"merged {len(recs)} pairs from {len(files)} files -> {a.out}")
    print(f"schema problems: {len(bad)} {bad[:5]}")
    print(f"author-text not verbatim (repaired from chunks): {len(mism)} {mism[:5]}")
    print(f"chunk ids with no pair: {len(absent)} {absent[:10]}")
    sims = sorted((word_similarity(r['author'], r['llm']), r["id"]) for r in recs)
    if sims:
        v = [s for s, _ in sims]
        print(f"\nauthor-vs-LLM word similarity: mean={statistics.mean(v):.2f} median={statistics.median(v):.2f} "
              f"min={min(v):.2f} max={max(v):.2f}")
        print("most similar (check for copying / degenerate chunks):")
        for s, i in sims[-5:][::-1]:
            print(f"  {s:.2f}  {i}")
        print("most divergent (biggest style delta):")
        for s, i in sims[:5]:
            print(f"  {s:.2f}  {i}")
        bl = statistics.mean(len(toks(r["author"])) for r in recs)
        cl = statistics.mean(len(toks(r["llm"])) for r in recs)
        print(f"avg words: author={bl:.0f} llm={cl:.0f} (llm/author={cl / bl:.2f})")
        if statistics.mean(v) > 0.8:
            print("WARNING: mean similarity > 0.8 -- the LLM paragraphs may be paraphrasing the author "
                  "instead of regenerating from bullets. Check the subagent prompt.")


MATH = re.compile(r"\\frac|\\mbox|\\begin\{|=\s*&|\\sum|\\int")
ACK = re.compile(r"^(we|i) (thank|gratefully)|anonymous referee|seminar participants", re.I)


def degenerate(r, a):
    sim = r["sim"]
    if sim >= a.max_sim:
        return f"near-identical (sim>={a.max_sim})"
    if MATH.search(r["author"]):
        return "math fragment"
    if ACK.search(r["author"]):
        return "acknowledgments"
    if len(toks(r["author"])) < a.min_words:
        return f"too short (<{a.min_words} words)"
    return ""


def cmd_filter(a):
    recs = read_jsonl(a.inp)
    kept, why = [], Counter()
    for r in recs:
        r["sim"] = round(word_similarity(r["author"], r["llm"]), 3)
        w = degenerate(r, a)
        if w:
            why[w] += 1
        else:
            kept.append(r)
    write_jsonl(a.out, kept)
    print(f"kept {len(kept)} / {len(recs)} -> {a.out}")
    for w, n in why.most_common():
        print(f"  filtered {n:3d}  {w}")
    per = Counter(r["paper"] for r in kept)
    print("kept per paper: " + ", ".join(f"{p}={n}" for p, n in per.items()))


def cmd_shard(a):
    recs = read_jsonl(a.inp)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    k = -(-len(recs) // a.n)
    for i in range(a.n):
        part = recs[i * k:(i + 1) * k]
        if not part:
            continue
        write_jsonl(out / f"shard_{i + 1}.jsonl", part)
        papers = Counter(r["paper"] for r in part)
        print(f"shard_{i + 1}.jsonl: {len(part)} pairs ({part[0]['id']} .. {part[-1]['id']}) "
              + ", ".join(f"{p}={n}" for p, n in papers.items()))
    print("Launch one analyst subagent per shard (references/prompts.md, Prompt B).")


VIEWER = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Style pairs</title><style>
:root{--bg:#faf9f7;--fg:#1a1a1a;--card:#fff;--line:#e3e0da;--accent:#8a5a2b;--muted:#6f6a62}
@media(prefers-color-scheme:dark){:root{--bg:#1a1917;--fg:#ece9e3;--card:#232220;--line:#3a3733;--accent:#d6a56a;--muted:#a39d92}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 Georgia,serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px;z-index:5}
h1{font:600 17px system-ui,sans-serif;margin:0 0 8px}.controls{display:flex;gap:8px;flex-wrap:wrap;font:13px system-ui,sans-serif;align-items:center}
select,input{font:13px system-ui,sans-serif;padding:5px 8px;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px}
.wrap{max-width:1200px;margin:0 auto;padding:16px}.pair{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:0 0 14px;overflow:hidden}
.meta{font:12px system-ui,sans-serif;color:var(--muted);padding:8px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.cols{display:grid;grid-template-columns:1fr 1fr}.col{padding:12px 16px}.col:first-child{border-right:1px solid var(--line)}
.lbl{font:600 11px system-ui,sans-serif;letter-spacing:.05em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
.bul{font:12px/1.4 system-ui,sans-serif;color:var(--muted);padding:10px 16px;border-top:1px dashed var(--line);display:none}
body.showbul .bul{display:block}
@media(max-width:800px){.cols{grid-template-columns:1fr}.col:first-child{border-right:0;border-bottom:1px solid var(--line)}}
</style></head><body><header><h1>%%NAME%% vs default LLM &mdash; <span id=n></span> paired paragraphs</h1>
<div class=controls>Paper <select id=paper><option value=all>all</option></select>
Sort <select id=sort><option value=asc>most divergent first</option><option value=desc>most similar first</option><option value=id>by id</option></select>
<input id=q placeholder="search" size=18><label><input type=checkbox id=bul> show claim bullets</label></div></header>
<div class=wrap id=list></div><script>
const D=%%DATA%%;const $=s=>document.querySelector(s);const esc=s=>(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
[...new Set(D.map(r=>r.paper))].forEach(p=>{const o=document.createElement('option');o.value=o.textContent=p;$('#paper').appendChild(o)});
function render(){let r=D.slice();const p=$('#paper').value,q=$('#q').value.toLowerCase(),s=$('#sort').value;
if(p!='all')r=r.filter(x=>x.paper==p);if(q)r=r.filter(x=>(x.author+x.llm).toLowerCase().includes(q));
if(s=='asc')r.sort((a,b)=>a.sim-b.sim);else if(s=='desc')r.sort((a,b)=>b.sim-a.sim);else r.sort((a,b)=>a.id<b.id?-1:1);
$('#n').textContent=r.length;
$('#list').innerHTML=r.map(x=>`<div class=pair><div class=meta><b>${esc(x.id)}</b><span>${esc(x.section||'')}</span><span>sim ${x.sim}</span></div>
<div class=cols><div class=col><div class=lbl>%%NAME%%</div>${esc(x.author)}</div><div class=col><div class=lbl>LLM (blind, from bullets)</div>${esc(x.llm)}</div></div>
<div class=bul><ul>${(x.bullets||[]).map(b=>'<li>'+esc(b)+'</li>').join('')}</ul></div></div>`).join('')}
['#paper','#sort'].forEach(s=>$(s).addEventListener('change',render));$('#q').addEventListener('input',render);
$('#bul').addEventListener('change',e=>document.body.classList.toggle('showbul',e.target.checked));render();
</script></body></html>"""


def cmd_viewer(a):
    recs = read_jsonl(a.inp)
    for r in recs:
        r.setdefault("sim", round(word_similarity(r["author"], r["llm"]), 3))
    data = json.dumps(recs, ensure_ascii=False).replace("</", "<\\/")
    page = VIEWER.replace("%%DATA%%", data).replace("%%NAME%%", html.escape(a.name))
    Path(a.out).write_text(page, encoding="utf-8")
    print(f"wrote {a.out} ({len(recs)} pairs). Open it in a browser.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("split", help="split chunks into batch input files")
    p.add_argument("--chunks", required=True)
    p.add_argument("--size", type=int, default=40)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_split)
    p = sp.add_parser("merge", help="merge and check batch outputs")
    p.add_argument("--chunks", required=True, help="chunks/all.jsonl (source of verbatim author text)")
    p.add_argument("--batches", required=True, help="quoted glob, e.g. 'pairs/batch_*.jsonl'")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_merge)
    p = sp.add_parser("filter", help="drop degenerate pairs, add sim")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-sim", type=float, default=0.90)
    p.add_argument("--min-words", type=int, default=35)
    p.set_defaults(fn=cmd_filter)
    p = sp.add_parser("shard", help="split filtered pairs into N analyst shards")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--n", type=int, default=4)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_shard)
    p = sp.add_parser("viewer", help="build HTML side-by-side viewer")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--name", default="Author", help="author's display name")
    p.set_defaults(fn=cmd_viewer)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
