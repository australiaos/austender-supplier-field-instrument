#!/usr/bin/env python3
"""The filter (P2) and the limited-tender figures, over raw/releases.jsonl.
The filter's terms are read from instrument/filter-terms.json, the file the assessment froze and
cites by hash; nothing is embedded here. Writes filtered-ids.json beside this script. One row per
contract notice: the latest release of each, since amendments carry the cumulative value.
The sweep this script comes from also cross-referenced suppliers against the practice's earlier
cases and wrote an output table with agency contact fields; neither is part of the published
instrument and both are removed here. The limited-tender section is the sweep's own figure and
is not a claim of the assessment, which says so at its Section 8."""
import json, re, collections, os
S = os.path.dirname(os.path.abspath(__file__))
filt = json.load(open(f'{S}/instrument/filter-terms.json'))
catdesc = json.load(open(f'{S}/category-descriptions.json')) if os.path.exists(f'{S}/category-descriptions.json') else {}
releases = [json.loads(l) for l in open(f'{S}/raw/releases.jsonl')]
latest = {}
for r in sorted(releases, key=lambda r: r['date']): latest[r['contracts'][0]['id']] = r
rels = list(latest.values())
originals = [r for r in releases if 'contract' in r['tag'] and 'contractAmendment' not in r['tag']]
print('releases', len(releases), '-> distinct contract notices (latest release each)', len(rels), '; original awards published in window', len(originals))
def con(r): return r['contracts'][0]
def code(r): return con(r)['items'][0]['classification']['id']
def desc(r): return con(r).get('description', '') or ''
def value(r): return float(con(r)['value']['amount'] or 0)

# ---------------- the filter, as terms from instrument/filter-terms.json ----------------
CATEGORY_PREFIXES = filt['category_prefixes']
TITLE_RE = {k: re.compile(v['regex'], 0 if v['case_sensitive'] else re.I) for k, v in filt['title_regexes'].items()}
cat_hits = collections.Counter(); term_hits = collections.Counter(); code_hits = collections.Counter()
filtered = []
for r in rels:
    c = code(r); d = desc(r); hit = False
    for pfx in CATEGORY_PREFIXES:
        if c.startswith(pfx): cat_hits[pfx] += 1; code_hits[c] += 1; hit = True; break
    for k, rx in TITLE_RE.items():
        if rx.search(d): term_hits[k] += 1; hit = True
    if hit: filtered.append(r)
print('=== the filter')
print('population', len(rels), 'filtered (P2)', len(filtered))
print('category prefix contributions (rows in prefix):')
for p, n in cat_hits.items(): print(f'  {p}  {CATEGORY_PREFIXES[p]}  {n}')
print('category codes matched, with AusTender description where fetched:')
for c, n in sorted(code_hits.items()): print(f'  {c}  {n:5d}  {catdesc.get(c, "")}')
print('title term contributions (rows matching term, overlapping):')
for k, n in term_hits.most_common(): print(f'  {n:5d}  {k}  /{filt["title_regexes"][k]["regex"]}/')
only_title = [r for r in filtered if not any(code(r).startswith(p) for p in CATEGORY_PREFIXES)]
print('rows caught by title only (category outside prefixes):', len(only_title))
print('  their categories:', collections.Counter(code(r) for r in only_title).most_common(12))
# what the filter excludes that a reader might expect: the sweep's own word list, not the instrument's
IT_WORDS = re.compile(r'\b(telecom|network|cyber|digital|data|system|technolog|licen[cs]|comput|server|storage|analytics|platform|app)', re.I)
excl = collections.Counter(code(r) for r in rels if r not in filtered and IT_WORDS.search(desc(r)))
print('excluded, for the reader: category codes outside the prefixes whose description mentions IT-shaped words (this word list is the sweep\'s, not the frozen instrument\'s), top 15:')
for c, n in excl.most_common(15): print(f'  {c}  {n}  {catdesc.get(c, "")}')
print('excluded rows in segment 80 (management/business/admin) matching those words:', sum(n for c, n in excl.items() if c.startswith('80')))
json.dump([r['id'] for r in filtered], open(f'{S}/filtered-ids.json', 'w'))

# ---------------- limited tender over the full pull (the sweep's figure; not a claim of the assessment) ----------------
print('\n=== limited tender, full twelve-month pull')
lim = [r for r in originals if r['tender'].get('procurementMethod') == 'limited']
def has(r, k): return bool((r['tender'].get(k) or '').strip())
def band(r):
    v = value(r); d = con(r)['dateSigned'][:10]
    thr = 125000 if d >= '2025-11-17' else 80000
    return 'at/above NCE threshold' if v >= thr else 'below NCE threshold'
print('original awards published in window', len(originals), '; awarded by limited tender', len(lim))
print('limited with limitedTenderReasonCode', sum(has(r, 'limitedTenderReasonCode') for r in lim))
print('limited with exemptionCode', sum(has(r, 'exemptionCode') for r in lim))
print('limited with either reason code or exemption code', sum(has(r, 'limitedTenderReasonCode') or has(r, 'exemptionCode') for r in lim))
print('limited with neither', sum(not (has(r, 'limitedTenderReasonCode') or has(r, 'exemptionCode')) for r in lim))
print('cross-tab limitedTenderExempt x reason x exemption x value band:')
ct = collections.Counter((r['tender'].get('limitedTenderExempt'), has(r, 'limitedTenderReasonCode'), has(r, 'exemptionCode'), band(r)) for r in lim)
for k, n in sorted(ct.items(), key=lambda x: -x[1]): print('  ', k, n)
for thr_label, thr in [('$125,000 (NCE, CPR 9.7.a from 17 Nov 2025; $80,000 before)', None), ('$400,000 (prescribed CCE, CPR 9.7.b)', 400000)]:
    sub = [r for r in lim if band(r) == 'at/above NCE threshold'] if thr is None else [r for r in lim if value(r) >= thr]
    e = sum(has(r, 'limitedTenderReasonCode') or has(r, 'exemptionCode') for r in sub)
    print(f'limited at/above {thr_label}: {len(sub)}; with reason or exemption code {e}; without {len(sub)-e}; proportion with {e/len(sub):.4f}' if sub else 'none')
