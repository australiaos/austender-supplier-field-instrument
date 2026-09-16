#!/usr/bin/env python3
"""Load raw pages -> raw/releases.jsonl, the page hash list, pull figures, distinct category codes.
Reads raw/pages/*.json written by pull.py (or a copy of the assessment's pages obtained from the
practice). Writes raw/PAGES-SHA256.txt, raw/releases.jsonl and category-code-counts.json, all
beside this script. Compare raw/PAGES-SHA256.txt with the published PAGES-SHA256.txt: identical
pages give an identical list and an identical releases.jsonl."""
import json, glob, hashlib, collections, os, sys
S = os.path.dirname(os.path.abspath(__file__))
pages = sorted(glob.glob(f'{S}/raw/pages/*.json'))
if not pages: sys.exit('no pages under raw/pages/; run pull.py or place the pages there')
man = open(f'{S}/raw/PAGES-SHA256.txt', 'w')
rels = []; seen = {}; dups = 0
for p in pages:
    b = open(p, 'rb').read()
    man.write(f'{hashlib.sha256(b).hexdigest()}  {os.path.basename(p)}\n')
    for r in json.loads(b)['releases']:
        if r['id'] in seen:
            dups += 1; continue
        seen[r['id']] = 1; rels.append(r)
man.close()
with open(f'{S}/raw/releases.jsonl', 'w') as f:
    for r in rels: f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
print('pages', len(pages), 'PAGES-SHA256.txt sha256', sha(f'{S}/raw/PAGES-SHA256.txt'))
print('releases (deduped)', len(rels), 'duplicates dropped', dups, 'releases.jsonl sha256', sha(f'{S}/raw/releases.jsonl'))
print('release date range', min(r['date'] for r in rels), '->', max(r['date'] for r in rels))
print('tag:', collections.Counter(t for r in rels for t in r['tag']))
print('contracts per release:', collections.Counter(len(r['contracts']) for r in rels))
print('amendment ids (contains -A):', sum(1 for r in rels if '-A' in r['contracts'][0]['id']))
print('procurementMethod:', collections.Counter(r['tender'].get('procurementMethod') for r in rels))
codes = collections.Counter(r['contracts'][0]['items'][0]['classification']['id'] for r in rels)
print('distinct category codes', len(codes))
json.dump(codes, open(f'{S}/category-code-counts.json', 'w'), indent=0)
