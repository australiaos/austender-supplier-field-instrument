#!/usr/bin/env python3
"""Look up the AusTender category description for one contract notice per UNSPSC code.
Reads codes-to-describe.json (code -> a contract notice id carrying that code) beside this script;
appends to raw/CATEGORY-LOOKUP-LOG.tsv (started_utc, http, bytes, sha256, url, code, description)
and writes category-descriptions.json. The website refused the practice's contact string and was
fetched under a browser string with a From header; pass your own string and address.

Usage: python3 describe.py --user-agent "<string>" --from "<your address>" """
import argparse, json, re, html, time, urllib.request, datetime as dt, hashlib, os
S = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--user-agent', required=True); ap.add_argument('--from', dest='frm', required=True)
a = ap.parse_args()
want = json.load(open(f'{S}/codes-to-describe.json'))
out = json.load(open(f'{S}/category-descriptions.json')) if os.path.exists(f'{S}/category-descriptions.json') else {}
os.makedirs(f'{S}/raw', exist_ok=True)
log = open(f'{S}/raw/CATEGORY-LOOKUP-LOG.tsv', 'a')
for code, cn in sorted(want.items()):
    if code in out: continue
    url = f'https://www.tenders.gov.au/Search/CnAdvancedSearch?CnId={cn}'
    req = urllib.request.Request(url, headers={'User-Agent': a.user_agent, 'From': a.frm})
    t0 = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        with urllib.request.urlopen(req, timeout=60) as r: body = r.read(); st = r.status
    except Exception as e: body = str(e).encode(); st = 0
    s = body.decode('utf-8', 'replace')
    m = re.findall(r'Category:</span>\s*<div class="list-desc-inner">(.*?)</div>', s, re.S)
    d = html.unescape(m[0].strip()) if m else ''
    log.write(f'{t0}\t{st}\t{len(body)}\t{hashlib.sha256(body).hexdigest()}\t{url}\t{code}\t{d}\n'); log.flush()
    out[code] = d; print(code, cn, st, d, flush=True)
    json.dump(out, open(f'{S}/category-descriptions.json', 'w'), indent=0)
    time.sleep(0.7)
print('done', len(out))
