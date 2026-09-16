#!/usr/bin/env python3
"""AOS-SFR-2026-001: recompute C4 to C7 from releases.jsonl using the frozen instrument files and
nothing inline. Usage: python3 measure.py <releases.jsonl>. Every regex comes from instrument/*.json."""
import json, re, sys, collections, os, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
def load(n): p = f'{HERE}/instrument/{n}'; b = open(p, 'rb').read(); print(f'{n} sha256 {hashlib.sha256(b).hexdigest()}'); return json.loads(b)
brand, shape, filt = load('brand-list.json'), load('shape-terms.json'), load('filter-terms.json')
releases = [json.loads(l) for l in open(sys.argv[1])]
latest = {}
for r in sorted(releases, key=lambda r: r['date']): latest[r['contracts'][0]['id']] = r
P1 = list(latest.values())
def sup(r): return next(p for p in r['parties'] if 'supplier' in p['roles'])
def abn(p): return next((i['id'] for i in p.get('additionalIdentifiers', []) if i.get('scheme') == 'AU-ABN'), '')
def desc(r): return r['contracts'][0].get('description', '') or ''
def val(r): return float(r['contracts'][0]['value']['amount'] or 0)
def code(r): return r['contracts'][0]['items'][0]['classification']['id']
TT = {k: re.compile(v['regex'], 0 if v['case_sensitive'] else re.I) for k, v in filt['title_regexes'].items()}
P2 = [r for r in P1 if any(code(r).startswith(p) for p in filt['category_prefixes']) or any(rx.search(desc(r)) for rx in TT.values())]
print(f'P1 {len(P1)}  P2 {len(P2)}  P2 value ${sum(val(r) for r in P2):,.0f}')
E = [(e['vendor'], re.compile(e['brand_regex'], re.I), re.compile(e['supplier_regex'], re.I), set(e['acns'])) for e in brand['entries']]
RES, SER = re.compile(shape['resale_regex'], re.I), re.compile(shape['service_regex'], re.I)
named, inter, direct = set(), set(), set()
pervendor = collections.defaultdict(lambda: [0, 0.0, 0, 0.0])
inter_rows = []
for r in P2:
    p = sup(r); nm = p['name'].casefold(); acn = abn(p)[-9:] if abn(p) else ''
    for v, brx, srx, acns in E:
        if brx.search(desc(r)):
            named.add(r['id']); isdirect = bool(srx.search(nm)) or (acn and acn in acns)
            t = pervendor[v]
            if isdirect: direct.add(r['id']); t[0] += 1; t[1] += val(r)
            else: inter.add(r['id']); t[2] += 1; t[3] += val(r); inter_rows.append((v, r))
inter -= set()  # a notice can be direct for one vendor and intermediated for another; C4 counts notices intermediated for any vendor
byid = {r['id']: r for r in P2}
iv = sum(val(byid[i]) for i in inter)
print(f'C4: named {len(named)}; intermediated notices {len(inter)} ${iv:,.0f}; direct notices {len(direct)}')
resellers = {(abn(sup(byid[i])) or sup(byid[i])["name"].upper()) for i in inter}
print(f'C4: distinct suppliers with an intermediated notice {len(resellers)}')
sh = collections.Counter(); shv = collections.Counter()
for i in inter:
    d = desc(byid[i]); a, b = bool(RES.search(d)), bool(SER.search(d)); k = 'resale' if a and not b else 'service' if b and not a else 'both' if a and b else 'neither'; sh[k] += 1; shv[k] += val(byid[i])
print('C4 shapes:', {k: (sh[k], round(shv[k])) for k in ('resale', 'service', 'both', 'neither')})
# C5's test: zero P2 notices whose SUPPLIER matches the vendor (regex or ACN), whatever the description says; among vendors named on >= 3 notices
sor = {v: sum(1 for r in P2 if srx.search(sup(r)['name']) or ((abn(sup(r))[-9:] in acns) if abn(sup(r)) else False)) for v, brx, srx, acns in E}
c5 = sorted(v for v, t in pervendor.items() if (t[0] + t[2]) >= 3 and sor[v] == 0)
print(f'C5 never supplier of record over all P2 (named >=3): {len(c5)} {c5}')
print('C5 check, the seven the scope names, supplier-of-record counts:', {v: sor[v] for v in ('Cisco','Citrix','Fortinet','Palo Alto','NetApp','Zscaler','Salesforce')})
acns_ms = next(set(e['acns']) for e in brand['entries'] if e['vendor'] == 'Microsoft'); srx_ms = next(re.compile(e['supplier_regex'], re.I) for e in brand['entries'] if e['vendor'] == 'Microsoft')
ms_direct_all = [r for r in P2 if (abn(sup(r))[-9:] in acns_ms if abn(sup(r)) else False) or srx_ms.search(sup(r)['name'])]
ms = pervendor['Microsoft']; d3 = [r for v, r in inter_rows if v == 'Microsoft' and abn(sup(r)) == '31010545267']
print(f'C6: Microsoft supplier-of-record over P2 (supplier regex or ACN, any description) {len(ms_direct_all)} ${sum(val(r) for r in ms_direct_all):,.0f}; brand-named direct {ms[0]} ${ms[1]:,.0f}; intermediated {ms[2]} ${ms[3]:,.0f}; via ABN 31 010 545 267 {len(d3)} ${sum(val(r) for r in d3):,.0f}')
nob = [r for r in P2 if r['id'] not in named]
print(f'C7: no brand {len(nob)} ${sum(val(r) for r in nob):,.0f} of ${sum(val(r) for r in P2):,.0f}')
# ---- C3 and C11 (added 16 September 2026, evening)
byabn = collections.defaultdict(lambda: [0, set()])
for r in P1:
    a = abn(sup(r))
    if a: byabn[a][0] += 1; byabn[a][1].add(sup(r)['name'].strip())
top10 = sorted(byabn.items(), key=lambda kv: -kv[1][0])[:10]
print('C3 spellings per ABN, ten most frequent ABNs over P1:', [(a, n, len(names)) for a, (n, names) in top10])
ora = byabn.get('80003074468'); print('C3 Oracle ABN 80 003 074 468 over P1:', ora[0] if ora else 0, 'notices,', len(ora[1]) if ora else 0, 'spellings; over P2:', len({sup(r)["name"] for r in P2 if abn(sup(r)) == "80003074468"}))
dis = [(v, sup(r)['name'], r['contracts'][0]['id']) for v, brx, srx, acns in E if acns for r in P2 if abn(sup(r)) and abn(sup(r))[-9:] in acns and not srx.search(sup(r)['name'])]
print('C3 name/ABN disagreements over P2 (ACN in the instrument, supplier regex does not match):', len(dis), dis)
am = [r for r in releases if 'contractAmendment' in r['tag']]
print(f'C11 amendment releases {len(am)} across {len({r["contracts"][0]["id"] for r in am})} notices; releases {len(releases)}; notices {len(P1)}; release dates {min(r["date"] for r in releases)} to {max(r["date"] for r in releases)}')
# ---- the per-vendor table for the document (added for the draft, 16 September 2026)
print('\nPER-VENDOR TABLE (vendors named on >= 1 P2 notice): vendor | named | direct n $ | intermediated n $ | supplier-of-record over all P2 n $')
tbl = []
for v, brx, srx, acns in E:
    t = pervendor.get(v)
    if not t: continue
    s_rows = [r for r in P2 if srx.search(sup(r)['name']) or ((abn(sup(r))[-9:] in acns) if abn(sup(r)) else False)]
    tbl.append((v, t[0] + t[2], t[0], t[1], t[2], t[3], len(s_rows), sum(map(val, s_rows))))
for row in sorted(tbl, key=lambda x: -x[5]):
    print(f'  {row[0]:22s} | {row[1]:4d} | {row[2]:4d} ${row[3]:>14,.0f} | {row[4]:4d} ${row[5]:>14,.0f} | {row[6]:4d} ${row[7]:>14,.0f}')
print('\nC5 nine, notices naming the brand (count, value):', {v: (pervendor[v][0] + pervendor[v][2], round(pervendor[v][1] + pervendor[v][3])) for v in c5})
print('vendors named on >=1 P2 notice:', len(tbl), '; named on >=3:', sum(1 for r in tbl if r[1] >= 3))
