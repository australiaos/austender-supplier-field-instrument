#!/usr/bin/env python3
"""Twelve-month AusTender OCDS pull, contractPublished, weekly windows, cursor pagination.
Every page body is written to disk exactly as received. Every request is logged.

Usage: python3 pull.py --user-agent "<your identifying string>" [--start 2025-09-16] [--end 2026-09-17]
The User-Agent is required and is yours: the feed's operator should be able to see who is pulling.
The window defaults to the one the assessment used (start inclusive, end exclusive, UTC midnights).
Writes raw/REQUEST-LOG.tsv (started_utc, attempt, http, bytes, sha256, url) and raw/pages/NNNNN.json.
A pull made today does not return the bytes the assessment measured: the feed republishes amended
notices and adds new ones. See README.md."""
import argparse, hashlib, json, sys, time, datetime as dt, urllib.request, urllib.error, os
S = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--user-agent', required=True, help='an identifying string with a way to reach you')
ap.add_argument('--start', default='2025-09-16', help='first day, UTC, inclusive')
ap.add_argument('--end', default='2026-09-17', help='end day, UTC, exclusive')
a = ap.parse_args()
UA = a.user_agent
BASE = 'https://api.tenders.gov.au/ocds/findByDates/contractPublished/{}/{}'
START = dt.datetime.fromisoformat(a.start).replace(tzinfo=dt.timezone.utc)
END = dt.datetime.fromisoformat(a.end).replace(tzinfo=dt.timezone.utc)
os.makedirs(f'{S}/raw/pages', exist_ok=True)
log = open(f'{S}/raw/REQUEST-LOG.tsv', 'a')
def fetch(url):
    for attempt in range(1, 4):
        t0 = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read(); code = r.status
        except urllib.error.HTTPError as e:
            body = e.read(); code = e.code
        except Exception as e:
            body = str(e).encode(); code = 0
        log.write(f'{t0}\t{attempt}\t{code}\t{len(body)}\t{hashlib.sha256(body).hexdigest()}\t{url}\n'); log.flush()
        if code == 200:
            return body
        time.sleep(5 * attempt)
    print('HALT: three failures on', url, code, body[:300]); sys.exit(2)
page = 0
w = START
while w < END:
    we = min(w + dt.timedelta(days=7), END)
    url = BASE.format(w.strftime('%Y-%m-%dT%H:%M:%SZ'), we.strftime('%Y-%m-%dT%H:%M:%SZ'))
    wp = 0
    while url:
        body = fetch(url)
        page += 1; wp += 1
        with open(f'{S}/raw/pages/{page:05d}.json', 'wb') as f: f.write(body)
        d = json.loads(body)
        n = len(d.get('releases', []))
        print(f'{w.date()} page {wp} (#{page}) releases={n}', flush=True)
        url = d.get('links', {}).get('next') if n > 0 else None
        time.sleep(0.5)
    w = we
print('DONE pages', page)
