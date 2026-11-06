# Source audit and limitations

Generated from `outputs/tables/A1`–`A7` and `outputs/reports/audit_summary.json` (run of 6 November
2026). Gate 1 of the handoff (provenance and coverage) is assessed here.

## 1. Inventory waterfall (A1)

| | Bank of Uganda | Central Bank of Kenya | Bank of Ghana |
|---|---:|---:|---:|
| Assets listed by the official archive | 1,159 (results + invitations + other) | 1,596 URLs (one notice is listed under up to three tenor sections) | 461 posts / 461 PDFs |
| In scope | 774 (all result-folder items; invitations 2016+) | 1,596 | 461 |
| Fetched and hash-verified | 771 (+1 `.xls` holding a PDF) | 1,596 | 454 (7 HTTP 404) |
| Classified as Treasury **bill** result (content) | 229 | 1,594 | 454 |
| Parsed, validated | 229 | 1,591 | 447 (7 blocked) |
| Distinct auctions in the panel | **227** | **536** | **447** |

Uganda's result folder also contains 117 bond results, 22 other bond items and bond switch/conversion
releases, 3 price matrices and 6 legacy `.xls` bond matrices; 42 XML tender forms in the invitation
folder are bond forms. None is a bill result (inspected). Invitation #1002 is a 0-byte file on the
server; invitation #996 is a legacy `.doc` (not read).

## 2. Expected versus observed auctions (A2)

* **Uganda** (bill auction numbers are consecutive): of numbers 989–1237, 25 are not observed as
  results. 13 of them (1047–1059) fall in 2019, an archive gap (only 1047 has an invitation); overall
  12 numbers have an invitation but no result in the archive and 13 have neither. Two of these (1087, 1172) are in fact present under a reused printed
  number (1086 on 18 Nov 2020; 1171 on a file named "Issue Number 1172"), so the effective gap is 23.
  In the 2023–26 common window (auctions 1144–1236) the missing numbers are 1162 and 1221 (2 of 93).
* **Kenya**: weekly series complete from March 2017 (51–53 auctions per year); 103 182-day issue numbers
  between 2014 and 2016 are not in the archive (only 1 notice in 2014 and 22 in 2016).
* **Ghana**: tenders 1573–2031 (2018–2026); 7 unavailable (HTTP 404: 1697–1700, 1768–1770) and 7
  blocked because the combined target's stated scope does not match the maturities reported in
  section 1 (1624, 1626, 1690, 1692, 1733, 1743, 1812); the target is never apportioned or guessed.

The missingness bound (`T6_missingness_bound.csv`) shows ≈32 additional fully volume-driven
auctions of typical size would be needed to lift Uganda's common-window volume share to 50%; two are
missing. The Uganda/Kenya contrast cannot be an archive artefact in that window.

## 3. Independent re-extraction (A5)

A stratified sample of three result documents per country-year plus every row with a validation flag
or OCR origin (117 documents) was re-extracted with a second engine and re-parsed:

* text-layer PDFs: **pdfminer.six (pdfplumber 0.11.7)**, a different PDF parser from the primary PyMuPDF;
* OCR-derived Uganda rows: the text layer or a fresh OCR at 300 dpi.

**882 of 882 compared cells (O, B, A by maturity) agree exactly**, across 105 documents; 12 could not
be parsed by the second engine (11 older BoG notices where pdfminer omits the section-1 target line, 1
CBK 2016 notice). This is a software re-extraction, not human double entry. Two observations led to the
final engine choice and are kept as findings: `pdftotext -layout` (Xpdf 4.00) shifted table rows on
some CBK and BoU layouts, and CBK PDFs embed a literal space after the leading digit of many amounts
(handled for the audit engine only; the primary engine is unaffected). The OCR value for BoU #1233
(182-day bids 75,611.1 m) was additionally checked against the rendered image and the component sum
(73,981.0 + 1,630.1); the pilot's 75,641.1 was an OCR misread.

## 4. Announced versus result-side offers (A3)

| | agree | mismatch | result only (no pre-close notice) |
|---|---:|---:|---:|
| Uganda (event × maturity) | 605 | 1 | 75 |
| Kenya (event × maturity) | 1,494 | 1 | 75 |
| Ghana (combined target) | 426 | 4 | 17 |

* Uganda #1235 (30 Sep 2026): 182-day offer 50 bn in the invitation, 35 bn in the result (as in the
  pilot audit).
* Kenya, issue dated 13 Jul 2026: 91-day offer 4,000 m announced, 8,000 m in the result (as in the pilot).
* Ghana #1582 (782 announced vs 582), #1710 (1,410 vs 1,041), #1860 (2,664 vs 2,654); #1842's
  announcement prints "2775,.00" and is left unparsed.

No discrepancy is corrected. The headline is re-estimated without these events (T5) and on the
matched announced-offer subset (T1, `offer_version = announced`); conclusions are unchanged.

## 5. What the published ratio means (A4)

| | B/A | B/O | ambiguous (A = B) | inconsistent |
|---|---:|---:|---:|---:|
| Uganda (maturity rows) | 392 | 83 | 197 | 6 |
| Kenya (maturity rows) | 1,443 | 0 | 39 | 0 |

Uganda: B/O dominates in 2020 releases, B/A from 2021; most 2017–19 auctions were exactly filled so the
formula cannot be identified. Kenya's printed ratio is B/A; its "performance rate" equals B/O × 100 in
99.9% of rows.

## 6. Timing (A7)

Release proxies are date-only: BoU — the date printed on the release (median 1 day after the auction);
CBK — the signature date of the results notice (same day as bid closure in the median); BoG — the
WordPress post date when within 7 days of the signature date, else the signature date (2019 archive
back-fills). Five printed dates precede the auction (wrong year on BoG 1789/1790; three CBK template
dates) and are raised to the held date. CBK value dates are never used as release dates. For
forecasting, a result is usable only from the next business day after its release proxy.

## 7. Comparison with the pilot replay (A6)

| | match | value difference | pilot only | rebuild only |
|---|---:|---:|---:|---:|
| Uganda (maturity rows) | 524 | 1 | 0 | 156 |
| Kenya (maturity rows) | 735 | 0 | 0 | 835 |
| Ghana (tender totals) | 185 | 2 | 0 | 259 |

Every pilot cell is found. The three differences are pilot errors: Uganda #1233 (OCR digit), Ghana
tender 1878 (pilot read "377,05" as 37,705) and Ghana 1891/1892 (pilot assigned 1892's values to 1891's
date). The rebuild adds Kenya 2014–2022, Ghana 2018–2022 and further Uganda auctions.

## 8. Limitations

* **Accounting, not behaviour.** Without bid books we cannot say whether unaccepted bids were "too
  expensive"; aggregate B includes all submitted prices.
* **Coverage.** Uganda 2019 gap; Kenya pre-2017 sparse; seven Ghana PDFs unavailable; Ghana tenor
  offers unpublished (aggregate only).
* **Timing.** Date-only release proxies; intraday publication times unknown.
* **OCR.** 42 Uganda maturity rows (14 auctions) come from OCR; they pass all validation rules and
  re-extraction checks, and the headline is unchanged without them.
* **Definitions change.** Price/yield conventions (WAP vs cut-off) and the cover-ratio denominator
  change over time; yields are not used in the confirmatory analysis.
* **External validity.** Three markets, particular years; no claim about Africa-wide prevalence.
* **Corrections.** Two Ghana values corrected via the ledger after cross-notice reconciliation; the
  reviewer field records an automated check pending human review.
