# The instrument of AOS-SFR-2026-001, *Invoiced, Not Supplied*

This repository holds the instrument behind one published assessment: the brand list, the filter, the shape terms, the scripts that pulled twelve months of the AusTender contract notice feed and measured it, the request logs, and the hash list of every page the pull received. The assessment is at <https://australiaos.com.au/verify/AOS-SFR-2026-001>, published 16 September 2026, PDF SHA-256 `08b3f5b37c21f95833ed00075a00e99087b2a0c4564080625f0d3291308b8259`. It states that its instrument is published in full with it. This is that publication.

## What the scripts reproduce, and what they do not

**The scripts reproduce the method, not the pull.** A reader who runs `pull.py` today does not receive the bytes the assessment measured. The feed moves: notices are amended and republished with cumulative values, new releases arrive, and the same window re-pulled later returns a different set. Every figure in the assessment is a function of the 703 response bodies received on 16 September 2026, and those bodies are not in this repository.

**What a reader can verify from this repository alone:**

- that `PAGES-SHA256.txt` names 703 pages and gives each its SHA-256, and that `REQUEST-LOG.tsv` records 703 requests, every one HTTP 200 on its first attempt, between 2026-09-16T02:14:56Z and 2026-09-16T02:28:50Z, in 53 weekly windows;
- that `instrument/brand-list.json`, `instrument/shape-terms.json` and `instrument/filter-terms.json` are exactly the files the assessment cites by hash (`cb032e89…`, `d301fdc4…`, `5b251ebc…`), that each entry of the brand list states where it came from, and that changing any term and re-running gives a different figure, which is what the assessment's Section 3 invites;
- that `measure.py` reads only those three files and a `releases.jsonl`, and prints the assessment's figures from nothing else.

**What a reader can verify holding a copy of the 703 pages**, obtained from the practice (see below): that every page hashes to its line in `PAGES-SHA256.txt`; that `load.py` yields a `releases.jsonl` hashing to `bd42bf2bacda273c3553c008bc2b4283d35060dc59ed272005caaa870cd87a6a`, 62,232 releases; that `analyze.py` over it selects the 9,461 notices the assessment calls P2 and `intermediation.py` and `measure.py` print every figure in the document. That is the determinism claim, and it was tested before the assessment was frozen and again when this repository was assembled: same files, same figures.

**What a reader cannot verify from anything here:** that the 703 bodies are what the feed served on 16 September 2026. That rests on the practice's log and hashes alone; each request was made once, no second fetch was made, and the feed carries no signature. Nor that a fresh pull reproduces any figure, which it will not. Nor that the category descriptions in `category-descriptions.json` are what the website printed, beyond the lookup log's record of each fetch.

## The files

| file | what it is |
|---|---|
| `instrument/brand-list.json` | 132 vendor entries: brand regex over the notice description, supplier regex over the supplier name, ACNs, provenance per entry, and each entry's count of P2 descriptions matched on 16 September 2026. Version 1.0, frozen 16 September 2026. |
| `instrument/shape-terms.json` | the resale and service regexes that sort an intermediated notice's description into resale-shaped, service-shaped, both or neither |
| `instrument/filter-terms.json` | the five UNSPSC prefixes and thirteen title regexes that make P2 |
| `instrument/NO-BRAND-DESCRIPTIONS-2026-09-16.tsv` | the thirty most frequent descriptions among the 8,827 P2 notices naming no brand on the list |
| `measure.py` | recomputes the assessment's figures from the three instrument files and a `releases.jsonl`; `python3 measure.py raw/releases.jsonl` |
| `pull.py` | the pull: contractPublished, weekly windows, cursor pagination, every body written as received, every request logged; requires your own `--user-agent` |
| `load.py` | pages to `raw/releases.jsonl`, the page hash list, the pull's figures, the category code counts |
| `describe.py` | one website lookup per UNSPSC code for its AusTender description; requires your own `--user-agent` and `--from` |
| `analyze.py` | the filter, reading `instrument/filter-terms.json`; writes `filtered-ids.json`; also the sweep's limited-tender figures, which are the sweep's and not a claim of the assessment |
| `intermediation.py` | the intermediation test, reading `instrument/brand-list.json` and `instrument/shape-terms.json`; the fuller per-supplier table over the same terms |
| `PAGES-SHA256.txt` | SHA-256 of each of the 703 response bodies |
| `REQUEST-LOG.tsv` | the 703 requests: started_utc, attempt, http, bytes, sha256, url; no header line |
| `CATEGORY-LOOKUP-LOG.tsv` | the 96 website lookups: started_utc, http, bytes, sha256, url, code, description; no header line |
| `MANIFEST-SHA256-2026-09-16.txt` | SHA-256 of every file in the practice's working copy of the pull, 750 files, including the pages and files not published here |
| `category-descriptions.json`, `category-code-counts.json` | UNSPSC code to AusTender description (96 codes, from the lookups) and releases per code (538 codes, 62,232 releases) |
| `codes-to-describe.json` | code to the contract notice id looked up for it; reconstructed from `CATEGORY-LOOKUP-LOG.tsv`, the file the sweep read having been overwritten in batches |

## What was changed from the scripts as run

The scripts were run once, on 16 September 2026, from a working directory outside any repository. They are published here with these changes and no others: every path resolves beside the script; the practice's User-Agent string and address are removed and the fetching scripts require the reader's own; the filter terms, the brand list and the shape terms are read from the files under `instrument/` instead of being embedded; the sweep's cross-reference of suppliers against the practice's earlier cases, and its output table carrying agency contact fields, are removed, being neither part of the instrument nor claims of the assessment. The assessment's open-items register records that the sweep ran outside version control and that the order in which its terms were built cannot be established from disk (item 175). The figures the assessment publishes are `measure.py`'s.

## Running it

Python 3 standard library only; run on 3.12. `pull.py` and `describe.py` fetch from the network and need your identifying string. Everything else runs offline over `raw/releases.jsonl`.

```
python3 pull.py --user-agent "your-tool/1.0 (you@example.org)"   # a fresh pull; the figures will differ
python3 load.py
python3 analyze.py
python3 intermediation.py
python3 measure.py raw/releases.jsonl
```

To check the assessment's own figures rather than a fresh pull's, obtain the 703 pages from the practice, place them under `raw/pages/`, and run `load.py` onwards; every hash and figure above should come out as stated or the copy is not the one.

## The data and its licence

The contract notice data comes from AusTender's Open Contracting Data Standard feed, `https://api.tenders.gov.au/ocds/`, published by the Department of Finance, Commonwealth of Australia, under [Creative Commons Attribution 3.0 Australia](http://creativecommons.org/licenses/by/3.0/au/). The category descriptions were read from `tenders.gov.au`. Nothing here alters that licence; the logs and hash lists describe the practice's fetches of that data and hold none of it beyond the descriptions of 96 categories.

## Licence

MIT, for the scripts and the instrument files, as `LICENSE` states. The assessment is not under it.

## Contact

AustraliaOS Pty Ltd. The verification page above carries the practice's address for requests, including a request for the 703 pages.
