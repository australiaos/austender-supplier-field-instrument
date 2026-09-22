#!/usr/bin/env python3
"""AOS-SFR-2026-001 v1.1: the no-brand descriptions table, the generator v1.0 never committed.

Usage: python3 nobrand.py <releases.jsonl> latest|award <out.tsv>

P2 and 'names no brand' exactly as ../measure.py defines them, from the frozen instrument,
under the same two modes as figures.py. The thirty most frequent description strings among
the no-brand P2 notices, with notices and summed value.

WHY CANDIDATES. v1.0's NO-BRAND-DESCRIPTIONS-2026-09-16.tsv says only "Derived by
measure.py's method". How description strings were normalised before grouping is on no
record, and sfr_nobrand.py's `.strip()` differs from the published table by one notice on two
rows and by four distinct strings (register entry of 21 September 2026). Five candidate
keys are fixed here, before the first run:
  N0  strip                                   (sfr_nobrand.py's)
  N1  as typed, no normalisation
  N2  strip, internal whitespace collapsed
  N3  casefold, strip
  N4  casefold, strip, internal whitespace collapsed
For keys that fold case, the row's printed string is the most frequent original spelling in
the group (ties: the lexically first).

SELECTION RULE, fixed before the first run. In latest mode every candidate is compared with
the published TSV: all thirty rows by printed string, rank, notices and value to the cent, and
the distinct-string count. A candidate REPRODUCES if every one matches. Award mode uses the
single reproducing candidate. If none reproduces, or more than one, it writes nothing and
exits 4, and the choice goes to the director.

AMENDED AFTER THE FIRST RUN, 22 September 2026, on the director's ruling (commit 7a43792 is
the run it answers). The first run returned no reproducing candidate: N2 matched every printed
string, notice count and value to the cent and the distinct count 3,487, and differed only in
the order of the one tie, rows 28 and 29 at 35 notices each, which v1.0 orders "IT Hardware",
"Hardware" and the lexical tie-break orders the other way. The ruling: the tie-break stays
lexical, and it is v1.1's stated rule; the order WITHIN a tie is outside the reproduction
test; every other criterion stands. Under the amended test N2 is the single reproducing
candidate and is selected. The rank difference at rows 28 and 29 is printed on every run.
"""
import json, re, sys, collections, os, csv, hashlib
C = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
L = lambda n: json.load(open(f'{C}/instrument/{n}'))
brand, filt = L('brand-list.json'), L('filter-terms.json')
TT = [re.compile(v['regex'], 0 if v['case_sensitive'] else re.I) for v in filt['title_regexes'].values()]
BR = [re.compile(e['brand_regex'], re.I) for e in brand['entries']]
src, MODE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
rels = [json.loads(l) for l in open(src)]
def pick(mode):
    d = {}
    if mode == 'latest':
        for r in sorted(rels, key=lambda r: r['date']): d[r['contracts'][0]['id']] = r
    elif mode == 'award':
        for r in rels:
            if 'contract' in r['tag']: assert r['contracts'][0]['id'] not in d; d[r['contracts'][0]['id']] = r
    else: sys.exit('mode must be latest or award')
    return list(d.values())
desc = lambda r: r['contracts'][0].get('description', '') or ''
code = lambda r: r['contracts'][0]['items'][0]['classification']['id']
val = lambda r: float(r['contracts'][0]['value']['amount'] or 0)
ws = lambda s: re.sub(r'\s+', ' ', s)
KEYS = {'N0': lambda s: s.strip(), 'N1': lambda s: s, 'N2': lambda s: ws(s).strip(),
        'N3': lambda s: s.casefold().strip(), 'N4': lambda s: ws(s).casefold().strip()}
PUBF = f'{C}/instrument/NO-BRAND-DESCRIPTIONS-2026-09-16.tsv'
pub = [row for row in csv.DictReader((l for l in open(PUBF) if not l.startswith('#')), delimiter='\t')]
PUB_DISTINCT = 3487

def table(mode, kname):
    P2 = [r for r in pick(mode) if any(code(r).startswith(p) for p in filt['category_prefixes']) or any(rx.search(desc(r)) for rx in TT)]
    nob = [r for r in P2 if not any(b.search(desc(r)) for b in BR)]
    k = KEYS[kname]; g = collections.defaultdict(lambda: [0, 0.0, collections.Counter()])
    for r in nob:
        d = desc(r); e = g[k(d)]; e[0] += 1; e[1] += val(r); e[2][d.strip()] += 1
    rows = []
    for key, (n, v, spell) in g.items():
        shown = sorted(spell.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        rows.append((shown, n, round(v, 2)))
    rows.sort(key=lambda x: (-x[1], x[0]))
    return len(nob), len(g), rows[:30]

def check(kname):
    n, distinct, top = table('latest', kname); bad = []
    # compared as a set of (string, notices, value) and, rank by rank, for the notice count
    # only, so that the order within a tie is outside the test (ruling of 22 September 2026)
    P = {(p['description'], int(p['notices']), round(float(p['value_aud']), 2)) for p in pub}
    T = {(t[0], t[1], t[2]) for t in top}
    for x in sorted(P - T): bad.append(('published row not produced', x))
    for x in sorted(T - P): bad.append(('produced row not published', x))
    for i, (p, t) in enumerate(zip(pub, top), 1):
        if int(p['notices']) != t[1]: bad.append((i, 'notice count at this rank', p['notices'], t[1]))
        elif p['description'] != t[0]: print(f'    {kname} tie order at rank {i}: published {p["description"]!r}, lexical {t[0]!r} ({t[1]} notices)')
    if distinct != PUB_DISTINCT: bad.append(('distinct', PUB_DISTINCT, distinct))
    return n, distinct, bad

if MODE == 'latest':
    ok = []
    for kn in KEYS:
        n, distinct, bad = check(kn)
        print(f'{kn}: no-brand {n}, distinct {distinct}, mismatches {len(bad)}'); [print('   ', b) for b in bad]
        if not bad: ok.append(kn)
    print('REPRODUCING:', ok)
    if len(ok) != 1: print('selection rule: not exactly one reproducing candidate; nothing written'); sys.exit(4)
    kname = ok[0]
else:
    ok = [kn for kn in KEYS if not check(kn)[2]]
    if len(ok) != 1: print('selection rule: not exactly one reproducing candidate:', ok, '; nothing written'); sys.exit(4)
    kname = ok[0]
n, distinct, top = table(MODE, kname)
with open(OUT, 'w') as f:
    f.write(f'# AOS-SFR-2026-001, mode {MODE}, key {kname}: the thirty most frequent description strings among the P2 notices matching no brand regex in brand-list.json v1.0. {n:,} notices, {distinct:,} distinct strings. Generated by recompute/nobrand.py; not a source.\n')
    f.write('rank\tdescription\tnotices\tvalue_aud\n')
    for i, (s, c, v) in enumerate(top, 1): f.write(f'{i}\t{s}\t{c}\t{v:.2f}\n')
print(f'mode {MODE} key {kname}: no-brand {n}, distinct {distinct}; wrote {OUT}', hashlib.sha256(open(OUT, 'rb').read()).hexdigest())
