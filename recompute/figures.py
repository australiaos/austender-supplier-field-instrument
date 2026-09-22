#!/usr/bin/env python3
"""AOS-SFR-2026-001 v1.1: every figure the document takes from the pull, in one of two modes.

Usage: python3 figures.py <releases.jsonl> latest|award <out.json>

  latest  v1.0's method: the latest-dated release for each contracts[0].id. Must reproduce v1.0.
  award   v1.1's rule (the register entry of 21 September 2026): the release tagged 'contract'
          for each contracts[0].id, held once per id, which carries the value at award.
          Amendment releases are never added to it or to each other. They are counted and
          listed apart (amendments.*), each with its own value as published.

The core is ../measure.py, copied unchanged except for the mode switch, as
general-findings/sovereign-buyers-2026-09/sfr_recompute.py (0e07059) was. The figures
measure.py does not print, and which v1.0 prints, are added below, each marked with
the v1.0 passage it serves. Two come from methods outside the frozen instrument:
  - the 1,422 and the 700 are GF-SCRIPT-4's (archive/inherited/analyze.py) tests,
    its terms copied verbatim; v1.0 says so of the 700.
  - the 220-token scan has no recorded method ("the scan the author actually read",
    SCOPE.md). Four candidate tokenisations are fixed here, before the first run, and
    each is reported; none is chosen by this script.
Every regex of the frozen instrument is read from ../instrument/*.json. Writes <out.json>
and nothing else; reads the case in place and edits nothing.
"""
import json, re, sys, collections, os, hashlib
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
def load(n): p = f'{HERE}/instrument/{n}'; b = open(p, 'rb').read(); print(f'{n} sha256 {hashlib.sha256(b).hexdigest()}'); return json.loads(b)
brand, shape, filt = load('brand-list.json'), load('shape-terms.json'), load('filter-terms.json')
src, MODE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
print('releases sha256', hashlib.sha256(open(src, 'rb').read()).hexdigest())
releases = [json.loads(l) for l in open(src)]
F = {}
latest = {}
if MODE == 'latest':
    for r in sorted(releases, key=lambda r: r['date']): latest[r['contracts'][0]['id']] = r
elif MODE == 'award':
    for r in releases:
        if 'contract' in r['tag']: assert r['contracts'][0]['id'] not in latest; latest[r['contracts'][0]['id']] = r
else: sys.exit('mode must be latest or award')
print('MODE', MODE)
P1 = list(latest.values())
def sup(r): return next(p for p in r['parties'] if 'supplier' in p['roles'])
def abn(p): return next((i['id'] for i in p.get('additionalIdentifiers', []) if i.get('scheme') == 'AU-ABN'), '')
def desc(r): return r['contracts'][0].get('description', '') or ''
def val(r): return float(r['contracts'][0]['value']['amount'] or 0)
def code(r): return r['contracts'][0]['items'][0]['classification']['id']
def cid(r): return r['contracts'][0]['id']
TT = {k: re.compile(v['regex'], 0 if v['case_sensitive'] else re.I) for k, v in filt['title_regexes'].items()}
incat = lambda r: any(code(r).startswith(p) for p in filt['category_prefixes'])
P2 = [r for r in P1 if incat(r) or any(rx.search(desc(r)) for rx in TT.values())]
F['P1'] = len(P1); F['P2'] = len(P2); F['P2_value'] = sum(val(r) for r in P2)
E = [(e['vendor'], re.compile(e['brand_regex'], re.I), re.compile(e['supplier_regex'], re.I), set(e['acns'])) for e in brand['entries']]
F['entries'] = len(E)
RES, SER = re.compile(shape['resale_regex'], re.I), re.compile(shape['service_regex'], re.I)
named, inter, direct = set(), set(), set()
pervendor = collections.defaultdict(lambda: [0, 0.0, 0, 0.0])
inter_rows = []; direct_by = collections.defaultdict(set); inter_by = collections.defaultdict(set)
for r in P2:
    p = sup(r); nm = p['name'].casefold(); acn = abn(p)[-9:] if abn(p) else ''
    for v, brx, srx, acns in E:
        if brx.search(desc(r)):
            named.add(r['id']); isdirect = bool(srx.search(nm)) or (acn and acn in acns)
            t = pervendor[v]
            if isdirect: direct.add(r['id']); t[0] += 1; t[1] += val(r); direct_by[r['id']].add(v)
            else: inter.add(r['id']); t[2] += 1; t[3] += val(r); inter_rows.append((v, r)); inter_by[r['id']].add(v)
byid = {r['id']: r for r in P2}
F['named'] = len(named); F['inter'] = len(inter); F['inter_value'] = sum(val(byid[i]) for i in inter); F['direct'] = len(direct)
both = sorted(i for i in inter & direct)
F['both'] = len(both); F['both_notices'] = sorted(cid(byid[i]) for i in both)
F['inter_suppliers'] = len({(abn(sup(byid[i])) or sup(byid[i])["name"].upper()) for i in inter})
sh = collections.Counter(); shv = collections.Counter()
for i in inter:
    d = desc(byid[i]); a, b = bool(RES.search(d)), bool(SER.search(d)); k = 'resale' if a and not b else 'service' if b and not a else 'both' if a and b else 'neither'; sh[k] += 1; shv[k] += val(byid[i])
for k in ('resale', 'service', 'both', 'neither'): F[f'shape.{k}'] = sh[k]; F[f'shape.{k}.value'] = shv[k]
sor_rows = {v: [r for r in P2 if srx.search(sup(r)['name']) or ((abn(sup(r))[-9:] in acns) if abn(sup(r)) else False)] for v, brx, srx, acns in E}
sor = {v: len(rs) for v, rs in sor_rows.items()}
c5 = sorted(v for v, t in pervendor.items() if (t[0] + t[2]) >= 3 and sor[v] == 0)
F['c5'] = len(c5); F['c5_list'] = c5
for v in c5: F[f'c5.{v}.named'] = pervendor[v][0] + pervendor[v][2]; F[f'c5.{v}.value'] = pervendor[v][1] + pervendor[v][3]
# v1.0 4.2: "Four vendors that an earlier reading placed on this list are not on it"
F['c5_earlier_four_now_supplier'] = sum(1 for v in ('Cisco', 'NetApp', 'Citrix', 'Palo Alto') if sor[v] > 0)
acns_ms = next(set(e['acns']) for e in brand['entries'] if e['vendor'] == 'Microsoft'); srx_ms = next(re.compile(e['supplier_regex'], re.I) for e in brand['entries'] if e['vendor'] == 'Microsoft')
ms_sor = [r for r in P2 if (abn(sup(r))[-9:] in acns_ms if abn(sup(r)) else False) or srx_ms.search(sup(r)['name'])]
ms = pervendor['Microsoft']; d3 = [r for v, r in inter_rows if v == 'Microsoft' and abn(sup(r)) == '31010545267']
F['ms.sor'] = len(ms_sor); F['ms.sor.value'] = sum(val(r) for r in ms_sor)
F['ms.direct'] = ms[0]; F['ms.direct.value'] = ms[1]; F['ms.inter'] = ms[2]; F['ms.inter.value'] = ms[3]
F['ms.via_31010545267'] = len(d3); F['ms.via_31010545267.value'] = sum(val(r) for r in d3)
F['ms.sor.value_millions_1dp'] = round(F['ms.sor.value'] / 1e6, 1); F['ms.inter.value_millions_1dp'] = round(F['ms.inter.value'] / 1e6, 1)
dom = [r for r in ms_sor if cid(r) == 'CN4188828']; F['ms.sor.CN4188828'] = val(dom[0]) if dom else None
F['ms.sor.CN4188828_supplier'] = sup(dom[0])['name'].strip() if dom else None
F['ms.sor.has_CN4202251'] = any(cid(r) == 'CN4202251' for r in ms_sor)
nob = [r for r in P2 if r['id'] not in named]
F['nobrand'] = len(nob); F['nobrand_value'] = sum(val(r) for r in nob)
# ---- C3 (v1.0 section 2)
byabn = collections.defaultdict(lambda: [0, set()])
for r in P1:
    a = abn(sup(r))
    if a: byabn[a][0] += 1; byabn[a][1].add(sup(r)['name'].strip())
top10 = sorted(byabn.items(), key=lambda kv: -kv[1][0])[:10]
F['c3.top10'] = [(a, n, len(nm)) for a, (n, nm) in top10]
F['c3.top10_min_spellings'] = min(len(nm) for _, (n, nm) in top10); F['c3.top10_max_spellings'] = max(len(nm) for _, (n, nm) in top10)
F['c3.top_abn_notices'] = top10[0][1][0]; F['c3.top_abn_spellings'] = len(top10[0][1][1])
mx = max(top10, key=lambda kv: len(kv[1][1])); F['c3.most_spellings_notices'] = mx[1][0]; F['c3.most_spellings'] = len(mx[1][1])
ora = byabn.get('80003074468', [0, set()])
F['c3.oracle.P1_notices'] = ora[0]; F['c3.oracle.P1_spellings'] = len(ora[1])
F['c3.oracle.P2_notices'] = sum(1 for r in P2 if abn(sup(r)) == '80003074468')
F['c3.oracle.P2_spellings'] = len({sup(r)['name'].strip() for r in P2 if abn(sup(r)) == '80003074468'})
dis = [(v, sup(r)['name'], cid(r)) for v, brx, srx, acns in E if acns for r in P2 if abn(sup(r)) and abn(sup(r))[-9:] in acns and not srx.search(sup(r)['name'])]
F['c3.disagreements'] = len(dis); F['c3.disagreement_rows'] = dis
# ---- 4.1 closing paragraph and the per-vendor table
tbl = []
for v, brx, srx, acns in E:
    t = pervendor.get(v)
    if not t: continue
    tbl.append((v, t[0] + t[2], t[0], t[1], t[2], t[3], sor[v], sum(map(val, sor_rows[v]))))
F['entries_named_ge1'] = len(tbl); F['entries_named_ge3'] = sum(1 for r in tbl if r[1] >= 3)
F['entries_named_none'] = len(E) - len(tbl)
F['pairs_all'] = sum(r[1] for r in tbl); F['pairs_ge3'] = sum(r[1] for r in tbl if r[1] >= 3)
F['notices_naming_two_or_more'] = sum(1 for r in P2 if sum(1 for v, brx, s, a in E if brx.search(desc(r))) >= 2)
cnt = collections.Counter(r['id'] for v in sor_rows for r in sor_rows[v])
F['sor_notices_in_more_than_one_column'] = sum(1 for i, n in cnt.items() if n > 1)
F['sor_multi_notices'] = sorted(cid(byid[i]) for i, n in cnt.items() if n > 1)
F['pervendor'] = {r[0]: {'named': r[1], 'direct': r[2], 'direct.value': r[3], 'inter': r[4], 'inter.value': r[5], 'sor': r[6], 'sor.value': r[7]} for r in tbl}
# ---- section 7, VMware
vm = F['pervendor'].get('VMware/Broadcom', {})
F['vmware.sor'] = vm.get('sor'); F['vmware.sor.value'] = vm.get('sor.value'); F['vmware.inter'] = vm.get('inter'); F['vmware.inter.value'] = vm.get('inter.value')
F['vmware.inter_over_sor_pct'] = round(100 * vm['inter.value'] / vm['sor.value']) if vm.get('sor.value') else None
# ---- C11 and 4.4 (these read the whole pull, not the selection)
am = [r for r in releases if 'contractAmendment' in r['tag']]
F['releases'] = len(releases); F['amendments'] = len(am); F['amended_notices'] = len({cid(r) for r in am})
F['release_date_min'] = min(r['date'] for r in releases); F['release_date_max'] = max(r['date'] for r in releases)
# ---- the rule's listing of amendments apart: over P2, each amended notice with its award value and each amendment's own value
awardof = {}
for r in releases:
    if 'contract' in r['tag']: awardof[cid(r)] = r
p2ids = {cid(r) for r in P2}
amp2 = collections.defaultdict(list)
for r in am:
    if cid(r) in p2ids: amp2[cid(r)].append((r['date'], val(r)))
F['amendments.P2_notices'] = len(amp2); F['amendments.P2_releases'] = sum(len(v) for v in amp2.values())
F['amendments.P2_listing'] = {k: {'award': val(awardof[k]), 'amendments': sorted(v)} for k, v in sorted(amp2.items())}
# ---- scope and Limitations: GF-SCRIPT-4's tests, terms copied verbatim from archive/inherited/analyze.py
F['title_only'] = sum(1 for r in P2 if not incat(r))
EXCL = re.compile(r'\b(telecom|network|cyber|digital|data|system|technolog|licen[cs]|comput|server|storage|analytics|platform|app)', re.I)
p2set = {r['id'] for r in P2}
F['excluded_segment80'] = sum(1 for r in P1 if r['id'] not in p2set and EXCL.search(desc(r)) and code(r).startswith('80'))
# ---- the 220-token scan (section 3); no recorded method, four candidates fixed before the first run
TOK = {'A': re.compile(r'\b[A-Z][A-Za-z0-9]+\b'), 'B': re.compile(r'\b[A-Z][A-Za-z0-9#&+.\-]*')}
for tk, rx in TOK.items():
    for unit in ('occurrences', 'notices'):
        c = collections.Counter()
        for r in P2:
            toks = rx.findall(desc(r)); c.update(set(toks) if unit == 'notices' else toks)
        top = [t for t, _ in c.most_common(220)]
        tm = sum(1 for t in top if any(brx.search(t) for _, brx, _, _ in E))
        em = sum(1 for _, brx, _, _ in E if any(brx.search(t) for t in top))
        F[f'tokens.{tk}.{unit}'] = {'top': len(top), 'matched_tokens': tm, 'unmatched_tokens': len(top) - tm, 'entries_matching': em}
# ---- section 3's provenance counts (added 22 September 2026, Act 2, on the director's ruling that v1.1 states
# the committed method's test A figure; committed before it runs). As the file records them: the entries whose
# provenance carries an 'A:', 'B:' or 'C:' tag, and those carrying none. Under the committed method: test A is
# candidate A, occurrences (a brand regex matches one of the 220 tokens); B and C stay as the file records them.
tag = lambda e, t: any(str(x).startswith(t + ':') for x in e.get('provenance', []))
ents = brand['entries']
for t in 'ABC': F[f'prov.file.{t}'] = sum(1 for e in ents if tag(e, t))
F['prov.file.none'] = sum(1 for e in ents if not any(tag(e, t) for t in 'ABC'))
c = collections.Counter()
for r in P2: c.update(TOK['A'].findall(desc(r)))
top = [t for t, _ in c.most_common(220)]
amet = [bool(any(re.compile(e['brand_regex'], re.I).search(t) for t in top)) for e in ents]
F['prov.method.A'] = sum(amet)
F['prov.method.none'] = sum(1 for e, a in zip(ents, amet) if not a and not tag(e, 'B') and not tag(e, 'C'))
# exclusive partition in the order A, B, C, none (added 22 September 2026, Act 2, committed before it runs):
# v1.0's 16/12/11/93 sum to 132 while the file's overlapping tags do not, which suggests a partition; tested here
def part(isA):
    out = collections.Counter()
    for e, a in zip(ents, isA):
        out['A' if a else 'B' if tag(e, 'B') else 'C' if tag(e, 'C') else 'none'] += 1
    return dict(out)
F['prov.partition.file'] = part([tag(e, 'A') for e in ents]); F['prov.partition.method'] = part(amet)
F['prov.A_tagged_not_met'] = sorted(e['vendor'] for e, a in zip(ents, amet) if tag(e, 'A') and not a)
F['prov.A_met_not_tagged'] = sorted(e['vendor'] for e, a in zip(ents, amet) if a and not tag(e, 'A'))
json.dump(F, open(OUT, 'w'), indent=1, sort_keys=True, default=str)
print('wrote', OUT, hashlib.sha256(open(OUT, 'rb').read()).hexdigest())
