# When Treasury Bill Auctions Miss Their Targets

Reproducible, audited measurement of Treasury bill auction shortfalls, allotments and maturity
shifts in **Uganda, Kenya and Ghana**, built only from official public notices of the Bank of Uganda,
the Central Bank of Kenya and the Bank of Ghana. Secondary: an honest, release-aware test of whether
public pre-close information improves warnings about auction execution.

> Working title: *When Treasury Bill Auctions Miss Their Targets: Bid Volumes, Allotments and
> Maturity Shifts in Uganda, Kenya and Ghana.* Authorship, affiliations and submission are for the
> authors to decide; nothing in this repository represents author consent or endorsement.

## What it measures

For offer **O**, gross bids **B** and accepted amount **A** (same face-value basis):

* total shortfall **S = max(O − A, 0)**, split into
* **D = max(O − B, 0)** — bids were short of the offer, and
* **R = S − D = max(min(O, B) − A, 0)** — enough bids were tendered but not accepted.

Shares are ratios of sums within a country (never pooled across currencies), auction-wide (sum the
three maturities first) and by maturity. For Uganda and Kenya the face-value-weighted maturity of the
accepted mix is compared with the advertised mix, including auctions that met the overall offer.

Key results, coverage and caveats: **[`outputs/reports/decision_memo.md`](outputs/reports/decision_memo.md)**.
Manuscript draft: [`manuscript/manuscript_draft.md`](manuscript/manuscript_draft.md).
Policy brief: [`manuscript/policy_brief.md`](manuscript/policy_brief.md).

## Install

Python ≥ 3.11. Verified on Python 3.12.10 / Windows 11 with pandas 2.2.3, NumPy 2.5.4, scikit-learn
1.9.1, PyMuPDF 2.1, pdfplumber 0.11.7 and rapidocr-onnxruntime 1.4.4 (full pins in
`requirements-lock.txt`; the pilot used scikit-learn 1.8.0).

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

OCR uses **RapidOCR** (ONNX; installed by pip, no system binary). On Linux, OpenCV needs
`libgl1 libglib2.0-0` (`sudo apt-get install -y libgl1 libglib2.0-0`). Poppler/Xpdf `pdftotext` is
optional (used only as a fallback second-extraction engine): Windows ships it with Git for Windows
(`mingw64/bin`), Linux `apt-get install poppler-utils`. Thread limits are set automatically
(`OMP_THREAD_LIMIT=1`); set `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1` if you run many workers.

## Run

```sh
# fixture-only integration (no network, no cache) — what CI runs
pytest -q
python -m treasury_auctions fixtures

# full rebuild from the official sources (network; ~1 h on first fetch, cached afterwards)
python -m treasury_auctions inventory          # discover + freeze source inventories
python -m treasury_auctions fetch              # download into data/cache (checksummed, idempotent)
python -m treasury_auctions --offline build    # parse -> audit -> measure -> evaluate -> report
```

Individual stages: `parse`, `audit`, `measure`, `evaluate`, `report`. Options: `--offline` (cache only),
`--cutoff YYYY-MM-DD` (default 2026-11-06), `--source UG KE GH`, `--workers N` (≤ 6), `--seed`,
`--strict` (exit 3 if any source is unavailable), `--lenient-timing` (exploratory date proxies),
`--root` / `TBA_ROOT`, `TBA_CACHE`. Exit codes: 0 ok, 1 stage failure, 2 usage, 3 incomplete sources.

The pilot replay is preserved in [`pilot_reference/`](pilot_reference/REPLAY_README.md) (exploratory
scripts, frozen extracts, 671 URL/hash pairs) and compared cell by cell in `outputs/tables/A6_pilot_comparison.csv`.

## Layout

```text
src/treasury_auctions/   discovery, fetch cache, extraction/OCR, parsers, panel, measures,
                         analysis, figures, audit, forecast, report, CLI
tests/                   unit tests + fixtures (layout excerpts, no PDFs)
data/frozen/             research freeze: inventories, endpoint hashes, fetch manifest
data/review/             reviewed correction ledger (old value, new value, evidence)
data/derived/            normalized tables with provenance (URL, SHA-256, raw source text)
outputs/tables|figures|reports   generated results, exhibits (+ source CSVs), run record
docs/                    protocol (frozen before results), data dictionary, provenance, literature, audit
manuscript/              manuscript draft, references, policy brief
```

Not committed: `data/cache/` (raw bytes, OCR cache), `data/interim/`, the virtual environment and the
private handoff. Source PDFs are not redistributed (see [`docs/data_provenance.md`](docs/data_provenance.md)).

## Licence and citation

Code: MIT ([`LICENSE`](LICENSE)). Source documents belong to their issuers; cite the original notices.
Derived tables are factual extracts with full attribution to the issuing central banks.
