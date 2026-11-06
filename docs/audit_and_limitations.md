# Source audit and limitations

This audit uses the 6 November 2026 frozen manifest. Tables A1–A8 and
`outputs/reports/audit_summary.json` contain the detailed counts.

## Coverage and analytical samples

| Stage | Uganda | Kenya | Ghana |
|---|---:|---:|---:|
| In-scope source URLs | 774 | 1,596 | 461 |
| Fetched in frozen manifest | 771 | 1,596 | 454 |
| Result documents parsed | 229 | 1,591 | 447 |
| Event records | 227 | 536 | 447 |
| Full-period auction-wide result-offer sample | 227 | 495 | 447 |
| Full-period maturity result-offer sample | 227 | 535 | — |

Uganda's 2019 archive gap includes auction numbers 1047–1059. Two releases reuse printed numbers
and are kept as distinct dated events. For the two common-window invitations without results
(#1162 and #1221), the announced totals sum to UGX 645bn. If both had attracted zero bids at their
announced targets, the common-window volume share would reach 21.7%. The typical-size scenario
requires about 32 additional fully volume-driven misses to reach 50% (T6). Both are conditional
stress tests.

Kenya has 51–53 event records per full year from 2017. The 182-day issue-number screen flags 103
gaps. Forty records have fewer than three reported maturities. One event has conflicting releases
and is excluded from both analyses. A separate issue dated 1 February 2021 is blocked because
acceptances exceed bids beyond the rounding allowance.

Ghana has seven unavailable attachments and seven blocked notices with inconsistent result
target scope. Of the 447 included tenders, 151 cover two maturities. The total row sums all and
only the maturities covered by each validated result target.

## Second text extraction (A5)

The check applies the same project parsers after a second extraction. It uses pdfminer.six for
text-layer PDFs and the text layer or a fresh 300 dpi OCR pass for OCR-derived notices. The sample
includes three result documents per country-year where available and additional flagged and OCR
notices.

Of 115 selected documents and 946 expected quantity cells, the second pass compared 869 cells
in 102 documents. All compared quantities and dates agreed. The remaining 13 documents account
for 77 unverified cells. This includes Ghana's combined target among expected quantities. Ledger
corrections can be applied in both passes. Agreement measures consistency between extraction
passes and leaves human verification and source conflicts open.

## Visual spot-check against the source page

Twenty common-window result notices were drawn at random (seed 20261106: seven Ugandan, seven
Kenyan, six Ghanaian, including one OCR-derived Ugandan notice). Each first page was rendered as an
image and read against the parsed values, without the project parsers. All 168 compared cells
(offers, bids and accepted amounts by maturity, and Ghana's combined targets) and all 20 held dates
agreed (`data/review/visual_spot_check.csv`). The reading was done by the AI assistant used to build
the pipeline, not by the authors, so it is not a substitute for author verification. The file lists
each source URL and hash so that any row can be re-checked by hand.

## Announced and result-side offers (A3)

| | Agree | Amount mismatch | Scope mismatch | Unparseable offer | Result only |
|---|---:|---:|---:|---:|---:|
| Uganda maturity rows | 617 | 1 | 0 | 0 | 63 |
| Kenya maturity rows | 1,485 | 1 | 0 | 0 | 75 |
| Ghana tenders | 424 | 3 | 2 | 1 | 17 |

Joining BoU invitations by scheduled auction date recovered invitations for four auctions
(12 maturity rows) whose printed numbers disagreed (#997, #1079, the second #1086 and the second
#1171). The Uganda mismatch is auction #1235 (182 days, UGX 50bn announced and 35bn in the result). The
Kenya mismatch is the issue dated 13 July 2026 (91 days, KES 4,000m announced and 8,000m in the
result). Ghana's amount mismatches are #1582, #1710 and #1860. In #1724 and #1792 the amounts agree
and the maturity scopes differ. The malformed #1842 announcement amount remains unparsed.
The Kenya event with conflicting documents is omitted from A3. T5 removes the events with any
amount or scope mismatch. The common-window result-side shares are unchanged at reported
precision.

## Cross-notice checks and cover ratios

Ghana's cross-notice table records six same-scope numeric discrepancies, eight scope
discrepancies and one unavailable following total. For #1984, the original tenor rows sum to
GH¢8,019.32m in bids, while #1985 prints GH¢7,209.32m. The accepted total agrees. A 91-day bid
of GH¢4,095.60m, a transposition of the printed 4,905.60, would reconcile the two; no other single
row can, because accepted would then exceed bids. Accepted exceeded the offer under either reading.

**Decisions (lead author, 2026-11-06).** The primary series retains each result notice's section-1
rows for all fourteen discrepancy rows (`data/review/ghana_source_decisions.csv`, one rationale per
row). In #1671 the following summary prints accepted above bids, which is impossible. In #1633 and
#1635 the following summary omits the 364-day bill that section 1 and its target include. The other
scope rows differ only in the tenor label. Substituting the following-notice totals for all six
same-scope amount discrepancies leaves Ghana's insufficient-bid volume share unchanged at 74.5%
(common window) and 79.7% (full period); see `outputs/tables/T5b_ghana_source_sensitivity.csv`.
The two ledger corrections (#1878 182-day bids, comma as decimal point; #2006 364-day accepted,
full stop as thousands separator) were signed off on the recorded cross-notice arithmetic. The
reported and corrected tokens both remain in `data/review/corrections.csv`.

In Uganda, the published ratio generally matches B/O in 2020 and B/A from 2021 onward.
The formulas coincide when accepted equals offered, and rounding can also prevent
identification. All identifiable Kenyan ratios match B/A. Kenya also publishes a performance
rate generally corresponding to B/O expressed as a percentage.

## Timing and interpretation

Publication dates are proxies. Uganda uses a printed release date where plausible, otherwise
the held date. Kenya usually uses the results notice signature. Ghana uses a timely archive post
or the signature where the post appears to be a back-fill. A7 lists recorded deadline
disagreements. Forecast origins and delays use weekdays, which do not encode market holidays.
The delayed-publication forecast files add one weekday to both publication proxies.

The holiday screen (A9, statutory calendars from python-holidays 0.108) checks that proxy. In no
auction of any country does a holiday let a result count as public at the next forecast origin
before the true next business day; consecutive auctions are about a week or more apart. Some
origins fall on holidays, and some results' weekday availability date is a holiday (A9b lists them).
These shift dates by a day without changing any information set. Islamic holiday dates in the
library are estimates, and ad hoc declared holidays may be missing.

The accounting split does not identify bidder or issuer motives. The maturity measure describes
the face value of each auction's issuance. Result-side offers and pre-close offers are reported
separately. The observed windows and archive coverage limit external validity.
