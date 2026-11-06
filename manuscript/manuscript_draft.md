# When Treasury Bill Auctions Miss Their Targets: Bid Volumes, Allotments and Maturity Shifts in Uganda, Kenya and Ghana

**Draft for author review — not for circulation.** Generated 6 November 2026 from the tables in
`outputs/tables/` (run record: `outputs/reports/run_record.json`). Every number below is traceable to
`outputs/reports/key_numbers.json`.

**Authors:** [AUTHOR LIST, ORDER AND AFFILIATIONS TO BE AGREED BY THE AUTHORS]
**Correspondence:** [TO BE ADDED]

---

## Structured abstract

**Purpose.** Headline auction statistics — total accepted versus total offered, and the published
"bid-to-cover" ratio — do not say *why* a Treasury bill auction falls short of its target, nor whether
an auction that meets its overall target still departs from the advertised maturity mix. We separate
these questions using only official public notices.

**Data.** An audited panel of 1,210 Treasury bill auctions built from every result and invitation
notice published by the Bank of Uganda (227 auctions, January 2017 – November 2026), the Central Bank
of Kenya (536, September 2014 – November 2026; weekly and essentially complete from 2017) and the Bank
of Ghana (447 tenders, January 2018 – October 2026). Each value is linked to the source URL, the
SHA-256 hash of the parsed bytes and the raw text of the line it came from.

**Method.** Each nominal shortfall S = max(O − A, 0) is split exactly into a part attributable to gross
bids falling short of the offer, D = max(O − B, 0), and a remainder in which enough bids were tendered
but not accepted, R = S − D. Shares are ratios of sums within a country. We also compare the
face-value-weighted maturity of accepted and offered amounts, and run a pre-registered, release-aware
walk-forward test of whether public pre-close information improves warnings.

**Findings.** In the common window 13 January 2023 – 30 October 2026, *none* of Uganda's auction-wide
shortfall volume is attributable to insufficient bids: all 34 auctions that fell short (of 91) had gross
bids at least equal to the offer. In Kenya 81.1% (95% block-bootstrap interval 70.8–89.5%) of shortfall
volume reflected insufficient bids (70 shortfalls in 198 auctions), and in Ghana 74.4% (60.1–89.9%;
79 in 189). The contrast is robust to 5% and 10% materiality thresholds, to using pre-close
announced offers instead of result-side offers, to excluding OCR-derived rows, and to dropping any
single year. Totals mask maturity-level misses: 88% of Ugandan and 85% of Kenyan auctions that met
the overall offer still missed at least one maturity. Among those fully funded auctions, the accepted
mix was longer than advertised in Uganda (median +26.9 days; 364-day share +13.6 percentage points)
and shorter in Kenya (median −46.4 days; −13.7 points). Predictively, no model passed the
pre-registered gate in a way that replicated: logistic models improved maturity-level Kenyan warnings
in the locked 2023–24 holdout, but the gain disappeared in 2025–26.

**Implications.** Two auctions with the same overall headline can differ in whether bids were missing
or not accepted, and in the maturity of new debt. Publishing offer, bids and acceptances per maturity
together with the realised versus advertised maturity of the issue, and defining the "bid-to-cover"
denominator, would let users tell them apart. The evidence is accounting, not a causal account of
issuer or bidder behaviour.

**Keywords:** Treasury bills; primary market; auction shortfall; debt management; maturity
structure; Uganda; Kenya; Ghana. **JEL:** H63, E43, G12, D44.

---

## 1. Introduction

Debt managers in many emerging and frontier markets publish, for each Treasury bill auction, an
amount offered by maturity and, after the auction, the amounts tendered and accepted. Market
commentary often reduces this to one headline: the auction was "undersubscribed" or "oversubscribed",
or its bid-to-cover ratio was high or low. Yet a shortfall of accepted against offered amounts can
arise for two mechanically distinct reasons. Bids may simply have been insufficient to fill the offer.
Or bids were sufficient in volume but were not accepted, for example because they were priced at
yields the issuer did not take. A third issue is hidden by totals: an auction can fill its overall
target while under-allotting some maturities and over-allotting others, changing *when* the new debt
falls due.

This paper measures these three things for Uganda, Kenya and Ghana from official public notices,
with an audit trail designed for reuse by debt offices and researchers. We make four contributions.
First, an exact accounting decomposition of every shortfall into a volume-driven part and an
unaccepted-bid part, at auction and maturity level, with interval estimates that respect time
dependence. Second, evidence on how far the accepted maturity mix departs from the advertised mix,
including when the total offer is met. Third, a vintage audit showing that the published
"bid-to-cover" label does not have a fixed denominator in Uganda. Fourth, a release-aware forecasting
evaluation that asks whether public pre-close information improves warnings beyond strong simple
baselines; it largely does not.

We deliberately stop short of causal claims. Aggregate bids include bids at all submitted prices, so
"enough bids to fill the offer" does not imply that enough could have been raised at an acceptable
yield. Without bid books we cannot separate issuer pricing choices from bidder behaviour.

## 2. Institutional setting

All three central banks run regular primary auctions of 91-, 182- and 364-day bills as fiscal agents.
[INSTITUTIONAL DETAIL TO BE REVIEWED BY A MARKET-PRACTICE CO-AUTHOR: primary-dealer systems, non-competitive
limits, auction calendars, reopening practice.]

* **Uganda.** Bank of Uganda (BoU) invitations to tender list an offer by maturity, the auction and
  settlement dates, and state that BoU "reserves the right to increase or reduce the amount offered
  in the auction and accept or reject any or all applications in part or in whole" (invitation #1236).
  Results notices report offered, tendered (competitive and non-competitive), accepted (competitive
  and non-competitive), price and yield fields, and a "bid to cover ratio". Bill auctions were broadly
  fortnightly in the period studied.
* **Kenya.** The Central Bank of Kenya (CBK) publishes a weekly notice that reports the outcome of the
  current issue (section A) and announces the next issue's offer by maturity, bid-closure date,
  results date and redemptions (section C). It states that CBK "reserves the right to accept/reject
  bids in part or in full".
* **Ghana.** Bank of Ghana (BoG) weekly tender notices report bids tendered and accepted by maturity
  but a single **combined** target for all bills (section 1), the previous tender's totals (section 2)
  and the next tender's combined target (section 3). Before April 2019 the weekly bill tender covered
  91- and 182-day bills only. Because maturity-level targets are not published, Ghana enters only the
  auction-wide analysis; we never apportion its target across maturities.

## 3. Data

### 3.1 Sources and freeze

Discovery and download took place on 6 November 2026 (snapshot cutoff), from the BoU auction
information API, the CBK Treasury bills results index and the BoG WordPress archive (461 posts). All
discovered assets, their scope decisions, endpoint hashes, retrieval times and the SHA-256 of every
downloaded document are committed in the repository; source PDFs are not redistributed. Documents
were classified from their *content*, not their archive title: the BoU "results" folder also contains
bond releases, bond switch/conversion results and price matrices, which are excluded.

### 3.2 Extraction and validation

Text was extracted from the PDF text layer (PyMuPDF), from DOCX table XML, and — when the text layer
lacked the table (2026 BoU releases rendered as images) or was corrupt (one release whose bill text
overlays a bond template) — by OCR of the rendered page (RapidOCR). Parsers record the raw line text of
every field and refuse to guess: malformed numbers block a document until a reviewed correction exists.
Two Ghanaian values were corrected in a committed ledger after cross-notice reconciliation (tender
1878, 182-day bids printed "377,05"; tender 2006, 364-day acceptances printed "1.141.12"); in both
cases the following notice's section-2 totals confirm the corrected value. Validation rules include
accepted ≤ tendered (within two-decimal rounding), competitive + non-competitive = total, Kenyan tenor
sums equal printed totals, and plausibility ranges. One Kenyan issue (value date 1 February 2021)
prints acceptances above bids for the 182-day bill beyond rounding and is quarantined.

Repeated documents are collapsed only when their values agree. Two BoU releases reuse an auction
number already used two weeks earlier (18 November 2020 prints 1086; a February 2024 release prints
1171); we key such events by held date rather than guess the intended number.

An independent re-extraction with a different PDF parser (pdfminer.six) — and, for OCR-derived rows, the
text layer or a fresh OCR — of a stratified sample of three documents per country-year plus every
flagged or OCR-derived document reproduced **all 882 compared cells** (offer, bids and acceptances by
maturity) in 105 documents; this is a software re-extraction, not human double entry. Every cell of
the earlier pilot extraction was recovered; the three cells that differ are pilot errors (an OCR digit
in BoU #1233 checked against the rendered image, a misread decimal comma in BoG tender 1878, and the
pilot's assignment of tender 1892's values to tender 1891's date). Pre-close and result-side offers
agree for 605 of 606 matched Ugandan maturity rows, 1,494 of 1,495 Kenyan rows and 426 of 430 Ghanaian
tenders; the exceptions (Uganda #1235, Kenya 13 July 2026, Ghana 1582, 1710 and 1860) are reported,
not corrected (`docs/audit_and_limitations.md`).

### 3.3 Coverage

The panel contains 227 Ugandan, 536 Kenyan and 447 Ghanaian auctions. Kenya's weekly series is
essentially complete from 2017 (51–53 auctions per year); 2014–2016 notices are sparse in the archive.
Ghana's coverage is 47–52 tenders per year from 2018; seven 2020–2021 attachments return HTTP 404.
Uganda's archive lacks results for auctions 1047–1059 (2019) and a handful of other numbers; in the
2023–2026 common window only a few auction numbers are missing.

### 3.4 Offer versions

Two offer definitions are kept. The *result* offer is printed with the results and has the widest
coverage. The *announced* offer is the pre-close version: the BoU invitation to tender, section C of
the preceding CBK notice, or section 3 of the preceding BoG notice. The latest version first public on
or before the auction date is used. Disagreements are never silently corrected; they are listed and the
headline is re-estimated without them.

## 4. Estimands

For offer O, gross bids B and accepted amount A on the same face-value basis:

* total positive shortfall S = max(O − A, 0);
* volume-driven shortfall D = max(O − B, 0);
* unaccepted-bid remainder R = S − D = max(min(O, B) − A, 0).

S = D + R holds whenever A ≤ B. The *volume share* is Σ D / Σ S over the missed auctions of one
country in one window — a ratio of sums, not a mean of ratios; it is undefined when there is no
shortfall, and currencies are never pooled. **Auction-wide** measures sum O, B and A over the three
maturities first; **maturity-level** measures compute S, D and R per maturity and then sum. The two
differ because an over-allotted long bill can offset a short bill's miss in the auction-wide total.
A three-way class (met; missed with B < O; missed with B ≥ O) is used for frequencies. Materiality
thresholds of 5% and 10% classify a miss as A < (1 − τ)O while keeping the B ≥ O split.

The **maturity shift** is Σ A_j d_j / Σ A_j − Σ O_j d_j / Σ O_j with nominal d ∈ {91, 182, 364},
with a settlement-to-maturity-days sensitivity. It describes the maturity of that auction's bill
issuance only — not the portfolio's average maturity and not refinancing cost.

Inference uses a moving-block bootstrap over time-ordered auctions (blocks of 4, 8 and 13 auctions;
8 reported), keeping the maturity rows of an auction together. The protocol was frozen before results
were computed (`docs/protocol.md`); deviations are logged there.

## 5. Results

### 5.1 Why auctions fall short

**Table 1. Shortfall decomposition, common window 13 Jan 2023 – 30 Oct 2026, result-side offer, exact threshold.**

| Country | Level | Auctions | Shortfalls | of which B ≥ O | Share of shortfall volume from insufficient bids (95% CI) |
|---|---|---:|---:|---:|---|
| Uganda | auction-wide | 91 | 34 | 34 | 0.0% (degenerate: Σ D = 0) |
| Uganda | by maturity | 91 | 163 maturity rows | 161 | 0.3% (0.0–0.7%) |
| Kenya | auction-wide | 198 | 70 | 12 | 81.1% (70.8–89.5%) |
| Kenya | by maturity | 198 | 313 maturity rows | 27 | 93.6% (90.5–96.1%) |
| Ghana | auction-wide | 189 | 79 | 8 | 74.4% (60.1–89.9%) |

Source: `outputs/tables/T1_decomposition.csv`; Figure 1.

Uganda's shortfalls are essentially all of the unaccepted-bid type: in every one of the 34 auctions
whose accepted total fell short of the offer, gross bids were at least as large as the offer. Over
the full 2017–2026 series, Uganda had only two auction-wide shortfalls with insufficient aggregate bids
(2018 and 2019) and a volume share of 1.0% (0.0–3.6%). Kenya and Ghana are the opposite: most
shortfall volume arose because bids did not reach the offer.

The contrast is stable. At 5% and 10% materiality, Uganda's share stays 0.0% (30 and 25 material
misses), Kenya's 82.2% and 82.4%, Ghana's 74.3% and 74.5%. Using the pre-close announced offer on the
matched subset gives 0.0% (Uganda, 89 auctions), 80.9% (Kenya, 197) and 74.4% (Ghana, 189).
Excluding OCR rows, excluding events with offer discrepancies, or leaving out any single year leaves
Uganda at 0.0% and Kenya and Ghana between roughly 67% and 84% (`T5_robustness.csv`). It is not an
artefact of coverage: to raise Uganda's common-window share to 50%, roughly 32 additional, unobserved,
fully volume-driven auctions of typical size would be needed, against only a few missing auction
numbers in that window (`T6_missingness_bound.csv`).

The degree of separation changes over time (`T2_decomposition_by_year.csv`). Ghana's volume share was
above 90% in each year from 2019 to 2024 but fell to 70% in 2025 and 49% in 2026, when 8 of 19
shortfalls occurred despite sufficient bids. In January 2025 – October 2026 the shares were 0.0%
(Uganda), 91.2% (Kenya) and 64.2% (Ghana). Kenya had sizeable unaccepted-bid shortfalls in 2019–2021
(shares 60–78%).

### 5.2 Totals hide maturity-level misses

Of the auctions that met the overall offer in the common window, 50 of 57 in Uganda (88%) and 109 of
128 in Kenya (85%) missed the offer on at least one maturity (`T3_masking.csv`). The BoU auction #1237
of 4 November 2026 is typical: an overall offer of UGX 350 bn was more than filled (UGX 439.0 bn
accepted from UGX 1,075.7 bn of bids), but the 91-day bill accepted UGX 4.2 bn of a UGX 15 bn offer and
the 182-day bill UGX 10.3 bn of UGX 35 bn, while the 364-day bill accepted UGX 424.5 bn against UGX
300 bn. Bids exceeded the offer at every maturity. CBK's issue of 26 October 2026 shows the Kenyan
pattern: the combined offer was filled, but the 182- and 364-day bills received fewer bids than offered.

### 5.3 The maturity of new issuance

**Table 2. Accepted minus offered weighted maturity (days) in auctions that met the overall offer.**

| Country | Window | Auctions | Median (IQR) | ≥ 30 days longer | ≥ 30 days shorter | Median change in 364-day share |
|---|---|---:|---|---:|---:|---:|
| Uganda | 13 Jan 2023 – 30 Oct 2026 | 57 | +26.9 (+8.4 to +40.4) | 26 | 3 | +13.6 pp |
| Kenya | 13 Jan 2023 – 30 Oct 2026 | 128 | −46.4 (−82.7 to +5.5) | 22 | 77 | −13.7 pp |
| Uganda | 1 Jan 2025 – 30 Oct 2026 | 28 | +40.1 (+28.0 to +44.1) | 21 | 0 | +19.1 pp |
| Kenya | 1 Jan 2025 – 30 Oct 2026 | 70 | −17.0 (−50.3 to +36.1) | 21 | 33 | −3.2 pp |

Source: `outputs/tables/T4_maturity_shift.csv`; Figure 2. Settlement-to-maturity day counts give
+27.7 (Uganda) and −46.4 days (Kenya) for the common window.

In Uganda, accepted amounts tilted towards the 364-day bill relative to the advertised mix, and the
tilt grew in 2025–26 (Figure 3). In Kenya, fully funded auctions typically accepted a shorter mix than
advertised in 2023–24 — consistent with the maturity-level misses being concentrated in the longer
bills — but less so in 2025–26. Over the full series the shifts are smaller (Uganda +5.7 days, Kenya
−11.7 days), so the common-window pattern reflects the recent era. These are statements about the
face-value maturity of each auction's issuance; we do not infer portfolio maturity, cash proceeds or
refinancing costs.

### 5.4 What the published "bid-to-cover" means

Comparing the printed ratio with B/O and B/A at quoted precision, Uganda's label matched B/O in most
2020 releases and B/A from 2021 onwards; in 2017–2019 most auctions filled exactly (A = B), so the two
cannot be told apart (`A4_ratio_definitions.csv`). Kenya's printed ratio matches B/A throughout;
Kenya's separate "performance rate" equals B/O. A high published ratio can therefore coexist with a
low fill, and cross-country comparisons of the label are not like for like.

### 5.5 Can shortfalls be anticipated from public pre-close information?

The forecasting test was pre-registered (`docs/protocol.md`): forecast origin at the close of the
business day before bidding; a past result is used only from the business day after its release
proxy; announced offers only if first public by the origin; walk-forward monthly refits; development
period 2020–22 (to choose the strongest baseline), locked holdout 2023–24 (never examined by the
pilot) and a replication period 2025–26 (examined by the pilot, so labelled previously inspected).
Candidates were L2 logistic regressions (history-only and with announced-offer and calendar
features), shallow gradient boosting, a pooled model with country terms, zero-shot cross-country
transfer and locally recalibrated transfer. The gate required a log-loss improvement of at least 0.02
nats per row with a block-bootstrap interval below zero and at least the baseline's captured shortfall
volume at a 25% alert budget.

The strongest baselines were simple: a blend of trailing frequency and previous-state transition
(Uganda; Kenya by maturity) or the transition rule (Kenya and Ghana auction-wide). In the locked
holdout, logistic models improved Kenyan maturity-level probability forecasts by 0.11–0.14 nats per
row (intervals entirely below zero) and, at the fixed alert budget, captured 73–75% of shortfall volume
against 63% for the baseline — partly because they alerted more often (38–40% of rows versus 32%); on a
retrospective top-quartile ranking the difference is small (52% versus 49%). **The improvement did not
replicate in 2025–26** (differences +0.017 to +0.034 nats, intervals including zero). Two Kenyan
auction-wide models formally pass in 2025–26, but at realised alert rates of 0–1%, which carries no
monitoring value; Uganda's pooled maturity-level model passes the pre-registered rule in 2025–26 but not
the stricter volume comparison. No model improved
on the baseline for Uganda in the holdout; the pilot's exploratory 2025–26 Ugandan gain is not
reproduced under strict release timing. Ghana's pooled model passed only the pre-registered rule
because its comparator issued almost no alerts; it fails a stricter comparison with the best baseline.
Direct cross-country transfer was very poorly calibrated. For the size of the maturity shift, a rolling
median of the last six shifts performed as well as ridge regression or boosting (holdout MAE 15.7 vs
14.5 days in Uganda, 23.6 vs 23.9 in Kenya), and far better than assuming no shift.

We conclude that, with these public data, a recent-history baseline is the appropriate monitoring
benchmark, and that the evidence does not support a deployable prediction product.

## 6. Discussion

**What the decomposition says, and does not.** In Uganda, auctions that fall short do so with bids
on the table; in Kenya and, until recently, Ghana, they fall short mainly because bids did not reach
the offer. This is consistent with BoU exercising the right it states in every invitation to reject or
reduce bids, but the notices do not record why bids were not accepted, so we do not attribute the
pattern to a pricing policy. Gross bids include all submitted prices; enough volume does not mean enough
volume at an acceptable yield.

**Why maturity reporting matters.** The same headline fill can describe very different issuance:
Uganda's filled auctions lengthened the face-value maturity of new bills, Kenya's shortened it. For
rollover planning, the realised maturity of each issue is the quantity of interest, and it is
recoverable only from maturity-level offers and acceptances.

**For a public monitoring report**, the evidence supports showing, per auction: offer, bids and
acceptance per maturity; the split of any shortfall into D and R; the realised versus advertised
weighted maturity; any revision between the announced and result-side offer; and an explicit
definition of the cover ratio. Two auctions with the same overall headline can then be recognised as
different.

**External validity.** Three markets over particular years cannot establish prevalence across Africa.
The contrast is between observed institutions in these windows, and Ghana's 2025–26 drift shows that it
can change.

## 7. Limitations

* Accounting decomposition only; no bid books, bidder identities or price schedules.
* Date-only release proxies; same-day intraday timing cannot be verified, so forecasts use the
  conservative previous-business-day origin.
* Archive gaps (Uganda 2019; Kenya before 2017; seven Ghana attachments) and two numbering typos in
  BoU releases; coverage tables and a missingness bound are reported.
* OCR is used for a minority of Uganda documents (image tables); their values pass the same validation
  rules, and one OCR digit was checked against the rendered image (#1233).
* Face values only: no cash proceeds, cost or fiscal simulations.
* The forecasting holdout was locked against the pilot but not against the authors' knowledge of the
  general market; a prospectively frozen runner is provided for genuinely unseen auctions.

## 8. Reproducibility

Code, frozen inventories, hashes, a correction ledger and derived tables are in the project repository
([REPOSITORY URL AND COMMIT TO BE INSERTED AT RELEASE]). `python -m treasury_auctions --offline build`
regenerates every table and figure from cached official documents; `python -m treasury_auctions fixtures`
runs a network-free integration test. Original notices remain the citable sources.

## Declarations

* Funding: [TO BE COMPLETED]. Competing interests: [TO BE COMPLETED]. Data availability: official
  notices at the issuers' websites; derived tables and code in the repository.
* Author contributions (provisional, for discussion): data engineering, statistical evaluation and
  reproducibility — [ISAAC OMODING]; institutional interpretation and market context — [MARKET-PRACTICE CO-AUTHOR,
  subject to agreement]. Not final.

## Figures

* Figure 1 — `outputs/figures/fig1_decomposition.(png|pdf)`: share of shortfall volume from bids short
  of the offer (D) versus bids not accepted (R), by country and level, common and recent windows.
* Figure 2 — `outputs/figures/fig2_maturity_shift.(png|pdf)`: distribution of accepted-minus-offered
  weighted maturity in auctions that met the overall offer.
* Figure 3 — `outputs/figures/fig3_uganda_timeline.(png|pdf)`: Uganda, overall fill and maturity shift
  per auction since 2022, with #1237 marked.

## References

See `manuscript/references.bib` (verified entries only) and `docs/literature_matrix.md` for the
closest-work comparison and items still pending verification (notably the IMF 2026 Uganda Selected
Issues chapter).
