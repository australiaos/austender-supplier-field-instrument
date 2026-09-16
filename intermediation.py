#!/usr/bin/env python3
"""The intermediation test over the filtered set (P2). The test, as terms:
A notice NAMES vendor V when its contracts[].description matches V's brand regex. It is DIRECT for V
when the supplier on the notice matches V's supplier regex (name, case-insensitive) or V's ACNs (the
last nine digits of the AU-ABN), and INTERMEDIATED for V when it names V and is not direct.
The vendor entries are read from instrument/brand-list.json and the resale and service shapes from
instrument/shape-terms.json, the files the assessment froze and cites by hash; nothing is embedded.
Reads filtered-ids.json (written by analyze.py) and raw/releases.jsonl beside this script; writes
INTERMEDIATION-by-supplier.tsv. The figures the assessment publishes are measure.py's; this script
is the sweep's fuller table over the same terms."""
import json, re, collections, csv, os
S = os.path.dirname(os.path.abspath(__file__))
brand = json.load(open(f'{S}/instrument/brand-list.json')); shape = json.load(open(f'{S}/instrument/shape-terms.json'))
ids = set(json.load(open(f'{S}/filtered-ids.json')))
rels = [json.loads(l) for l in open(f'{S}/raw/releases.jsonl')]
latest = {}
for r in sorted(rels, key=lambda r: r['date']): latest[r['contracts'][0]['id']] = r
F = [r for r in latest.values() if r['id'] in ids]
byid = {r['id']: r for r in F}
def sup(r): return next(p for p in r['parties'] if 'supplier' in p['roles'])
def abn(p): return next((i['id'] for i in p.get('additionalIdentifiers', []) if i.get('scheme') == 'AU-ABN'), '')
def val(r): return float(r['contracts'][0]['value']['amount'] or 0)
def desc(r): return r['contracts'][0].get('description', '') or ''
VR = {e['vendor']: (re.compile(e['brand_regex'], re.I), re.compile(e['supplier_regex'], re.I), set(e['acns'])) for e in brand['entries']}
rows = []
for r in F:
    p = sup(r); nm = p['name'].casefold(); acn = abn(p)[-9:] if abn(p) else ''
    d = desc(r)
    for v, (brx, srx, acns) in VR.items():
        if brx.search(d):
            direct = bool(srx.search(nm)) or (acn and acn in acns)
            rows.append((v, 'direct' if direct else 'intermediated', r))
inter = [(v, r) for v, kind, r in rows if kind == 'intermediated']
key = lambda r: (abn(sup(r)) or sup(r)['name'].upper())
by_sup = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0, set()]))
for v, r in inter:
    b = by_sup[key(r)][v]; b[0] += 1; b[1] += val(r); b[2].add(sup(r)['name'])
tot_f = sum(val(r) for r in F)
named = {r['id'] for v, k, r in rows}
inter_notices = {r['id'] for v, r in inter}
inter_value = sum(val(byid[i]) for i in inter_notices)
print('=== intermediation over the filtered set')
print('filtered notices', len(F), 'value', f'${tot_f:,.0f}')
print('notices naming any listed vendor brand in the description:', len(named), 'value', f'${sum(val(byid[i]) for i in named):,.0f}')
print('of which DIRECT (supplier is that vendor):', len({r["id"] for v, k, r in rows if k == "direct"}))
print('of which INTERMEDIATED (supplier is not that vendor):', len(inter_notices), 'value', f'${inter_value:,.0f}', f'share of filtered value {inter_value/tot_f:.4f}')
print('distinct suppliers carrying at least one intermediated notice:', len(by_sup))
print('notices with NO listed brand in description:', len(F) - len(named), 'value', f'${tot_f - sum(val(byid[i]) for i in named):,.0f}')
print('\n--- suppliers by intermediated value (top 40): supplier | vendors named (count, value)')
sup_tot = {k: sum(b[1] for b in d.values()) for k, d in by_sup.items()}
sup_cnt = {k: len({r['id'] for v, r in inter if key(r) == k}) for k in by_sup}
with open(f'{S}/INTERMEDIATION-by-supplier.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(['supplier_key', 'supplier_names_as_published', 'vendor_named', 'notices', 'value_aud'])
    for k in sorted(by_sup, key=lambda k: -sup_tot[k]):
        for v, (n, val_, names) in sorted(by_sup[k].items(), key=lambda x: -x[1][1]): w.writerow([k, ' / '.join(sorted(names)), v, n, f'{val_:.2f}'])
for k in sorted(by_sup, key=lambda k: -sup_tot[k])[:40]:
    names = sorted({n for b in by_sup[k].values() for n in b[2]})[0]
    vs = ', '.join(f'{v} ({b[0]}, ${b[1]:,.0f})' for v, b in sorted(by_sup[k].items(), key=lambda x: -x[1][1])[:6])
    print(f'  {names[:38]:38s} | {sup_cnt[k]:4d} notices ${sup_tot[k]:>14,.0f} | {vs}')
print('\n--- vendors named on three or more notices: vendor | direct (n, $) | intermediated (n, $) | intermediated share of that brand')
vt = collections.defaultdict(lambda: [0, 0.0, 0, 0.0]); seen = set()
for v, k, r in rows:
    if (v, r['id']) in seen: continue
    seen.add((v, r['id'])); t = vt[v]
    if k == 'direct': t[0] += 1; t[1] += val(r)
    else: t[2] += 1; t[3] += val(r)
for v, t in sorted(vt.items(), key=lambda x: -(x[1][3])):
    if t[2] + t[0] >= 3: print(f'  {v:22s} direct {t[0]:4d} ${t[1]:>14,.0f} | intermediated {t[2]:4d} ${t[3]:>14,.0f} | {t[3]/(t[1]+t[3]) if t[1]+t[3] else 0:.2f}')
# ---- shape of the intermediated notices, by the frozen shape terms
RESALE = re.compile(shape['resale_regex'], re.I); SERVICE = re.compile(shape['service_regex'], re.I)
def shp(r):
    d = desc(r); a = bool(RESALE.search(d)); b = bool(SERVICE.search(d))
    return 'resale-shaped' if a and not b else 'service-shaped' if b and not a else 'both' if a and b else 'neither'
print('\n--- shape of intermediated notices (all vendors):')
sh = collections.Counter(); shv = collections.Counter()
for i in inter_notices: r = byid[i]; sh[shp(r)] += 1; shv[shp(r)] += val(r)
for k in ['resale-shaped', 'service-shaped', 'both', 'neither']: print(f'  {k:15s} {sh[k]:4d} notices ${shv[k]:>16,.0f}')
print('--- Microsoft-brand intermediated, by shape:')
sh = collections.Counter(); shv = collections.Counter()
for v, k, r in rows:
    if v == 'Microsoft' and k == 'intermediated': sh[shp(r)] += 1; shv[shp(r)] += val(r)
for k in ['resale-shaped', 'service-shaped', 'both', 'neither']: print(f'  {k:15s} {sh[k]:4d} notices ${shv[k]:>16,.0f}')
print('--- Microsoft-brand intermediated via ABN 31 010 545 267 vs others:')
d3 = {r['id']: r for v, k, r in rows if v == 'Microsoft' and k == 'intermediated' and abn(sup(r)) == '31010545267'}
ot = {r['id']: r for v, k, r in rows if v == 'Microsoft' and k == 'intermediated' and abn(sup(r)) != '31010545267'}
print(f'  ABN 31 010 545 267: {len(d3)} notices ${sum(val(r) for r in d3.values()):,.0f}; others: {len(ot)} notices ${sum(val(r) for r in ot.values()):,.0f}')
