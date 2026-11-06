# Data provenance and rights

## Sources (all official, public, no login)

| Issuer | Discovery endpoint | Document families used | Retrieved (UTC) |
|---|---|---|---|
| Bank of Uganda | `https://bou.or.ug/api/financial-market-auction-information` (Strapi JSON; `items[].file[].file` and `items[].file[].fileWithMonth[].file`) | "Auction results" folder (bill results; bonds, matrices and other items classified from content and excluded), "Invitation to tender" folder 2016+ | 2026-11-06 10:31 |
| Central Bank of Kenya | `https://www.centralbank.go.ke/bills-bonds/treasury-bills/` (91/182/364-day historical results sections) | weekly results notices (sections A and C) | 2026-11-06 10:31 |
| Bank of Ghana | `https://www.bog.gov.gh/wp-json/wp/v2/gog_auction_results` (461 posts, 5 pages) → each post page → attached PDF | weekly tender result notices (sections 1–3) | 2026-11-06 10:31–10:50 |

Endpoint hashes, counts and retrieval times: `data/frozen/inventory_meta.json`. Every discovered asset
with its scope decision: `data/frozen/inventory_{UG,KE,GH}.csv`. Every fetched document's SHA-256,
size, media type and retrieval time: `data/frozen/fetch_manifest.csv`. The parsed values in
`data/derived/` carry the source URL and SHA-256 of the exact bytes they came from, plus the raw source
line text (`raw` column) for each extracted field.

The client identified itself as `treasury-auctions-research/0.1 (public-document research client)`,
used at most 4 concurrent connections with a minimum spacing between requests, and contacted only the
three official hosts. No paywall, login or bot check was bypassed. Documents that could not be read
are listed, not guessed.

## Snapshot and vintage

Use `python -m treasury_auctions --frozen build` for a replay from the committed inventory and
manifest. It fetches only missing bytes from previously successful sources and checks each
against the frozen hash. Add `--offline` to use an existing cache. The ten frozen failures remain
excluded even if their URLs later start working. The source archive itself remains with the
central banks.

* Research freeze: discovery and fetch on **6 November 2026**; snapshot cutoff 6 November 2026 (no
  event after it enters the analysis).
* Official archives change. A rerun of `inventory`/`fetch` on a later date produces a new vintage; the
  committed inventories, manifest and hashes let a reviewer see exactly which bytes underlie each
  number. `pilot_reference/source_inventory.json` preserves the pilot's 671 URL/hash pairs.
* Archive back-fills are recorded: e.g. Bank of Ghana posts dated July 2019 carry 2018 tenders; their
  post date is not used as a release date (signature date used instead).

## Known source defects (preserved, not silently corrected)

| Item | Treatment |
|---|---|
| BoU 18 Nov 2020 release prints auction no. 1086 (also used on 4 Nov 2020); "Issue Number 1172" file prints 1171 | separate events keyed by held date, flagged |
| BoU invitation #1236 prints the total as "350,000,000/=" while tenor lines sum to 350 bn | tenor lines used; flag kept |
| BoU 6 May 2026 release has overlapping template text layers (bond text under bill text) | rendered page OCR used |
| BoU invitation #1002 is a 0-byte file on the server; invitation #996 is legacy `.doc` | listed as unavailable |
| BoU invitations printed #996 (file "Issue No 997", 10 May 2017) and #1078 (file "Issue No 1079", 29 Jul 2020) invite the next auction; invitations #1087 and #1172 belong to the results printed #1086 (18 Nov 2020) and #1171 (14 Feb 2024) | joined by scheduled auction date, flagged in `offer_versions.csv` |
| BoU invitations #1102, #1103, #1110 and #1176 give an auction date one or two days from the held date on the results (10 April 2024 was the Eid al-Fitr holiday; #1176 was held on 11 April) | joined by printed number, flagged |
| CBK issue dated 1 Feb 2021: 182-day accepted 1,969.97 > bids 1,969.87 | quarantined (accepted exceeds tendered beyond rounding) |
| BoG tender 1878 "377,05"; tender 2006 "1.141.12" | corrected via `data/review/corrections.csv` using the following notice's section-2 totals; raw value retained |
| BoG tender 1655 section 3 announces "tender 1655" (its own number) | excluded from announced offers |
| BoG tender 1582: preceding notice announced 782 m, result notice target 582 m | reported as an offer mismatch |
| BoG tenders 1697–1700, 1768–1770: attachment URLs return HTTP 404 | listed as unavailable |

## Rights

The notices are public documents of the Bank of Uganda, Central Bank of Kenya and Bank of Ghana.
Being publicly viewable does not by itself grant redistribution rights, so **source PDFs are not
committed or redistributed**; the repository holds URLs, hashes and a download/parse workflow.
The derived tables in `data/derived/` are compact factual extracts (amounts, dates) with full
attribution to the issuing institution and are provided to make the analysis checkable; re-users
should cite the original notices. Code is MIT-licensed (`LICENSE`); this licence does not extend to
the source documents.
