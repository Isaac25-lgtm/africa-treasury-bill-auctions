# Data dictionary

All derived tables live in `data/derived/` and are rebuilt by `python -m treasury_auctions parse`.
Quantities are face (nominal) amounts in the issuer's reporting unit: **UGX bn** (Uganda, converted
from shillings printed in full), **KES m** (Kenya), **GHS m** (Ghana). Currencies are never summed
across countries. Missing values are empty, never zero.

## `source_documents.csv` — one row per inventory URL

| column | meaning |
|---|---|
| asset_id | 16-hex SHA-1 of the URL (stable id) |
| country, listed_kind | issuer country; archive category (result / invitation) |
| url, title, folder_year, folder_month | as listed by the official archive |
| posted_local, posted_utc | Ghana only: WordPress post time (local Accra = UTC) |
| sha256, bytes, media_kind, retrieved_utc | content hash of the bytes parsed; sniffed type (pdf/zip/ole/html) |
| method, tool | `pymupdf` text layer, `docx-xml`, `xlsx-cells`, `ocr-rapidocr` (page 1) |
| ocr_mean_conf, ocr_min_conf | OCR confidence when OCR was used |
| doc_type | content class, e.g. `ug_bill_result`, `ug_bond_result`, `ug_matrix`, `ke_bill_result`, `gh_bill_result` |
| status | `parsed`, `blocked` (target family but failed validation), `not_target_family`, `extract_error`, `fetch_failed`, `not_fetched` |
| blocking, flags | reasons that keep a document out / non-blocking warnings |
| key_no, key_date | auction/tender/issue number and the event date found in the content |

## `auction_events.csv` — one row per country × event

| column | meaning |
|---|---|
| event_id | `UG-<auction no>`, `KE-<value date>`, `GH-<tender no>` |
| held_date | bid/auction date (UG: "held on"/"auction date"; KE: bid-closure date announced in the preceding notice, else signature date — see `held_date_basis`; GH: section-1 "held on") |
| settlement_date | settlement/issue/value date |
| release_date, release_basis | date-only proxy for first publication of results |
| available_from | next weekday after `release_date`, used as a proxy for when the result was public |
| deadline_date, deadline_time_text | bid submission deadline when stated (UG invitation; KE announcement) |
| result_url, result_sha256, method | provenance of the result used |
| conflict | true if repeated result documents disagree (excluded from estimands) |
| n_tenors | maturities present |
| currency, unit, timezone | ISO currency, reporting unit, IANA zone (Africa/Kampala, Africa/Nairobi, Africa/Accra) |
| UG: auction_no, price_basis, yield_label, invitation_url | price/yield convention as printed (WAP vs cut-off), invitation link |
| KE: value_date, signed_date, issues_json, printed_totals_json, reported_redemptions_total, announced_redemptions_total, announcement_url | |
| GH: tender_no, notice_no, posted_utc, target_scope, target_tenors | `target_tenors` gives the validated maturity scope as a semicolon-separated list |

## `auction_outcomes.csv` — one row per event × maturity (Ghana also a `total` row)

| column | meaning |
|---|---|
| tenor | 91 / 182 / 364; Ghana `total` row carries the combined target |
| O_result | offer printed with the results (Ghana: combined target on the `total` row only; maturity rows empty) |
| B, A | gross bids tendered and accepted amount. Ghana's total row sums the maturities actually covered by its target |
| B_comp, B_noncomp, A_comp, A_noncomp | competitive / non-competitive components where printed |
| yield_pct, yield_label, price_basis | effective yield (UG) or weighted average rate of accepted bids (KE) as printed; not harmonized |
| cover_published, cover_formula | printed "bid to cover" and the formula or formulas it matches at quoted precision |
| perf_published | KE "performance rate" (B/O × 100) as printed |
| maturity_date, days_to_maturity | printed maturity; settlement-to-maturity days |
| redemptions | KE rollover/redemptions for the current batch (post-auction; never a predictor) |
| url, sha256, method, raw | provenance and JSON of the parsed lines. Ledger-applied rows use corrected text, with original tokens in the correction ledger |

## `offer_versions.csv` — announced (pre-close) offers, all versions kept

| column | meaning |
|---|---|
| event_id, tenor, O_announced, version | version numbering by first-public date per event |
| first_public_date, first_public_basis | date-only proxy (UG invitation date, KE signature date of preceding notice, GH release proxy of preceding notice) |
| GH: target_tenors, raw | validated announced target scope where available and parsed section-3 text |
| deadline_date, deadline_time_text, source_url, sha256 | |

## Other

* `duplicates.csv` — events with several result documents; whether copies agree.
* `ghana_cross_notice.csv` — compares tenor sums with the following notice's section-2 totals. Scope mismatches, unavailable totals and numeric mismatches have separate statuses.
* `data/frozen/inventory_*.csv`, `ghana_posts.csv`, `inventory_meta.json`, `fetch_manifest.csv` — the
  research freeze: every discovered asset, scope decision, endpoint hashes, retrieval times.
