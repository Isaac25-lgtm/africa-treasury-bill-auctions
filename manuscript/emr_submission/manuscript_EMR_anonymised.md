# When Treasury Bill Auctions Miss Their Targets: Bid Volumes, Allotments and Maturity Shifts in Uganda, Kenya and Ghana

---

## Abstract

Headline Treasury bill auction statistics, such as total accepted against total offered and the
published bid-to-cover ratio, do not show why an auction falls short or whether a filled auction
changes the maturity of new debt. Using 1,210 auction records from official notices of the central
banks of Uganda, Kenya and Ghana (2014–2026), we split each shortfall exactly into a part due to bids
falling short of the offer and a part due to bids not accepted, and compare the accepted maturity mix
with the offered mix. From January 2023 to October 2026, none of Uganda's shortfall volume reflects
insufficient bids: all 34 auctions that fell short had bids at least equal to the offer. In Kenya
81.1% (95% interval 70.8–89.5%) and in Ghana 74.5% (61.0–90.2%) of shortfall volume reflects
insufficient bids. Totals mask maturity-level misses in 85–88% of filled Ugandan and Kenyan auctions,
and filled auctions lengthened new-issue maturity in Uganda (median +26.9 days) but shortened it in
Kenya (−46.4 days). Uganda's published bid-to-cover ratio changed its denominator over time. A
release-aware forecasting evaluation does not support an operational warning rule. We propose
disclosures that let users tell these cases apart.

**Keywords:** Treasury bills; sovereign debt auctions; primary market; debt management; maturity structure; Sub-Saharan Africa

**JEL classification:** H63; E43; G12; D44

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
dependence. Second, evidence on how far the accepted maturity mix departs from the offered mix,
including when the total offer is met. Third, a vintage audit showing that the published
"bid-to-cover" label does not have a fixed denominator in Uganda. Fourth, a release-aware forecasting
evaluation that asks whether public pre-close information improves warnings beyond strong simple
baselines; it largely does not.

We deliberately stop short of causal claims. Aggregate bids include bids at all submitted prices, so
"enough bids to fill the offer" does not imply that enough could have been raised at an acceptable
yield. Without bid books we cannot separate issuer pricing choices from bidder behaviour.

**Relation to closest work.** The nearest study is IMF staff's 2026 analysis of Uganda's yield curve
(Qu 2026). It documents that, before the pandemic, sold amounts tracked offers. Afterwards, in monthly
aggregates, Treasury bonds were undersold (average sold-to-offer ratio about 0.9) and bills oversold
(about 1.1). It reads the divergence as more active allocation management that weakens issuance
predictability. Its core analysis decomposes yields and models the Nelson–Siegel curve, with the bill
sold-to-offer ratio entering only as a control. The divergence and its active-allocation reading are
therefore not new. What we add is not in that chapter: the split of each shortfall into bids short of
the offer and bids not accepted, measured per auction and per maturity; the accepted versus
advertised maturity mix, including when totals are met; a comparison with Kenya and Ghana; an audit of
what the published cover ratio divides by; and a release-aware forecasting test. In Kenya, by
contrast, published machine-learning work targets bill *yields* rather than issuance outcomes
(Njeri et al. 2025). Deep-market studies of the United States, the euro area and Canada analyse cover
ratios, auction tails and bidder behaviour with bidder-level or price data (Beetsma et al. 2020;
Hortaçsu et al. 2018; Tindall and Perez 2021; Gao and Epp 2026; Allen et al. 2026). An early
emerging-market example is an empirical study of Mexico's Treasury bill auction (Umlauf 1993).

Cottarelli and Bartolini (1994) review the design of Treasury bill auctions and describe arrangements
in 42 industrial and developing countries. The OECD (2025) measures
how much auction sizes and intervals vary in African local-currency bond markets in 2024. The OECD
(2026) argues that bid volumes at G7 bond auctions, expressed as bids over allotments, are not a
sufficient indicator of overall demand. None of these splits within-auction shortfalls or examines
bill maturity mixes. Our empirical contribution is the notice-level quantity and maturity
comparison across the three bill markets.

## 2. Institutional setting

All three central banks run regular primary auctions of 91-, 182- and 364-day bills as fiscal agents.
The access rules printed on the notices differ. In Uganda, primary dealer banks and other commercial
banks submit bids through the BoU Central Securities Depository by 10:00 on the auction day, and
results report competitive and non-competitive amounts separately (invitation #1236). In Kenya, bids
close at 14:00 on the Thursday before the Monday value date and are submitted through DhowCSD or
Treasury Mobile Direct. Non-competitive bids are capped per investor and tenor: KSh 20 million in the
2023 notices read, with a KSh 100,000 minimum bid, and KSh 50 million in notices from March 2024, with
minimums of KSh 50,000 (non-competitive) and KSh 2 million (competitive). CBK may allot pro rata at a common rate and states that the amount
realised depends on the National Treasury's liquidity needs (notices of 26 January 2023, 21 March
2024 and 17 April 2025). In Ghana, the weekly wholesale auction is open only to primary dealers, and the public
buys bills in the secondary market through depository participants (tender 1940). These rules are
taken from the notices and are not used as explanatory variables.

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
  91- and 182-day bills. Two-maturity tenders also appear in later years. Ghana enters the auction-wide
  analysis with bids and acceptances summed over the maturities explicitly covered by each target.

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

A second text-extraction pass uses pdfminer.six for text-layer PDFs and the text layer or a new
300 dpi OCR pass for OCR-derived notices. It reuses the project parsers and records expected,
compared and agreeing cells, including Ghana's combined targets, plus a separate date check.
It measures agreement between extraction passes. The underlying source reconciliation also records
conflicting totals across successive Ghana notices. Where a result notice's own table and the
following notice's summary disagree, we use the result notice's table; substituting the summaries
for all six same-scope amount discrepancies leaves Ghana's shares unchanged at reported precision.
Two values printed with misplaced separators (#1878, #2006) are corrected in a reviewed ledger that
keeps the reported and corrected tokens. Of comparable offer rows, 617 of 618 Uganda rows and 1,485 of 1,486 Kenya rows agree.
In Ghana, 424 offers agree, three differ in amount, two differ in maturity scope, and one announced
amount cannot be parsed (replication package, audit notes).

### 3.3 Coverage

The full-period result-side auction-wide samples contain 227 Ugandan, 495 Kenyan and 447 Ghanaian
auctions (replication package, Table A8). Of 536 Kenyan event records, 40 lack a full set of three
maturities and one has conflicting result notices. Kenya's 2014–2016 archive is sparse. Seven Ghana
attachments returned HTTP 404 and seven fetched notices were blocked on target scope. Uganda's
2019 archive gap includes auction numbers 1047–1059. The common window has two Uganda invitations
with no matching results.

### 3.4 Offer versions

Two offer definitions are kept. The *result* offer is printed with the results and has the widest
coverage. The *announced* offer is the pre-close version: the BoU invitation to tender, section C of
the preceding CBK notice, or section 3 of the preceding BoG notice. We select the latest version
dated on or before the auction date. Undated invitations may contribute to measurement only.
Ghana's announced target must cover the same maturities as the result. We list numeric and scope
discrepancies and re-estimate the headline after excluding the affected auctions.

## 4. Estimands

For offer O, gross bids B and accepted amount A on the same face-value basis:

* total positive shortfall S = max(O − A, 0);
* volume-driven shortfall D = max(O − B, 0);
* unaccepted-bid remainder R = S − D = max(min(O, B) − A, 0).

S = D + R holds whenever A ≤ B. The remainder can be positive when B < O and A < B. The *volume
share* is Σ D / Σ S over the missed auctions of one
country in one window — a ratio of sums, not a mean of ratios; it is undefined when there is no
shortfall, and currencies are never pooled. **Auction-wide** measures sum O, B and A over the three
maturities first, using the notice-specific target scope for Ghana. **Maturity-level** measures
compute S, D and R per maturity and then sum. The two
differ because an over-allotted long bill can offset a short bill's miss in the auction-wide total.
A three-way class (met; missed with B < O; missed with B ≥ O) is used for frequencies. Materiality
thresholds of 5% and 10% classify a miss as A < (1 − τ)O while keeping the B ≥ O split.

The **maturity shift** is Σ A_j d_j / Σ A_j − Σ O_j d_j / Σ O_j with nominal d ∈ {91, 182, 364},
with a settlement-to-maturity-days sensitivity. It describes the maturity of that auction's bill
issuance only — not the portfolio's average maturity and not refinancing cost.

Inference uses a moving-block bootstrap over time-ordered auctions with blocks of 4, 8 and 13
auctions. The headline uses eight auctions per block, which spans more calendar time in Uganda than
in the weekly markets. Maturity rows stay together when resampling. These intervals describe
resampling variation conditional on the observed data. The versioned protocol and its dated
revisions are in the replication package.

## 5. Results

### 5.1 Why auctions fall short

**Table 1. Shortfall decomposition, common window 13 Jan 2023 – 30 Oct 2026, result-side offer, exact threshold.**

| Country | Level | Auctions | Shortfalls | of which B ≥ O | Share of shortfall volume from insufficient bids (95% CI) |
|---|---|---:|---:|---:|---|
| Uganda | auction-wide | 91 | 34 | 34 | 0.0% (degenerate: Σ D = 0) |
| Uganda | by maturity | 91 | 163 maturity rows | 161 | 0.3% (0.0–0.7%) |
| Kenya | auction-wide | 198 | 70 | 12 | 81.1% (70.8–89.5%) |
| Kenya | by maturity | 198 | 313 maturity rows | 27 | 93.6% (90.5–96.1%) |
| Ghana | auction-wide | 199 | 81 | 8 | 74.5% (61.0–90.2%) |

Source: authors' calculations from BoU, CBK and BoG notices (replication package, Table T1); Figure 1.

Uganda's shortfalls are essentially all of the unaccepted-bid type: in every one of the 34 auctions
whose accepted total fell short of the offer, gross bids were at least as large as the offer. Over
the full 2017–2026 series, Uganda had only two auction-wide shortfalls with insufficient aggregate bids
(2018 and 2019) and a volume share of 1.0% (0.0–3.6%). Kenya and Ghana are the opposite: most
shortfall volume arose because bids did not reach the offer.

The contrast is stable. At 5% and 10% materiality, Uganda's share stays 0.0% (30 and 25 material
misses), Kenya's 82.2% and 82.4%, Ghana's 74.4% and 74.7%. Using the pre-close announced offer on the
matched subset gives 0.0% (Uganda, 90 auctions), 80.9% (Kenya, 197) and 74.5% (Ghana, 198).
Excluding OCR rows, excluding events with offer discrepancies, or leaving out any single year leaves
Uganda at 0.0% and Kenya and Ghana between roughly 67% and 84% (replication package, Table T5). The two
missing Uganda invitations total UGX 645 billion. Assuming those announced targets and zero bids
for both auctions would lift the volume share to 21.7%. This conditional stress test supplements
the scenario in which roughly 32 typical fully volume-driven misses would be needed to reach 50%
(replication package, Table T6).

The degree of separation changes over time (replication package, Table T2). Ghana's volume share was
above 90% in each year from 2019 to 2024 but fell to 70% in 2025 and 49% in 2026, when 8 of 19
shortfalls occurred despite sufficient bids. In January 2025 – October 2026 the shares were 0.0%
(Uganda), 91.2% (Kenya) and 64.2% (Ghana). Kenya had sizeable unaccepted-bid shortfalls in 2019–2021
(shares 60–78%).

### 5.2 Totals hide maturity-level misses

Of the auctions that met the overall offer in the common window, 50 of 57 in Uganda (88%) and 109 of
128 in Kenya (85%) missed the offer on at least one maturity (replication package, Table T3). The BoU auction #1237
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

Source: authors' calculations from BoU, CBK and BoG notices (replication package, Table T4) and Figure 2. Settlement-to-maturity day counts give
+27.7 (Uganda) and −46.4 days (Kenya) for the common window. Using the matched announced offers and
requiring the announced total to be met gives +28.5 days for Uganda (55 auctions) and −46.4 for
Kenya (128) in the common window (replication package, Table T4c).

In Uganda, accepted amounts tilted towards the 364-day bill relative to the offered mix, and the
tilt grew in 2025–26 (Figure 3). In Kenya, fully funded auctions typically accepted a shorter mix than
offered in 2023–24 — consistent with the maturity-level misses being concentrated in the longer
bills — but less so in 2025–26. Over the full series the shifts are smaller (Uganda +5.7 days, Kenya
−11.7 days), so the common-window pattern reflects the recent era. These are statements about the
face-value maturity of each auction's issuance; we do not infer portfolio maturity, cash proceeds or
refinancing costs.

### 5.4 What the published "bid-to-cover" means

Comparing the printed ratio with B/O and B/A at quoted precision, Uganda's label matched B/O in most
2020 releases and usually matched B/A from 2021 onwards. The two ratios coincide when the offered
and accepted amounts are equal (A = O), as in 152 of Uganda's 153 ambiguous maturity rows in
2017–2019. Rounding can also prevent identification (replication package, Table A4). Kenya's
identifiable printed ratios match B/A. Its separate "performance rate" generally equals B/O
expressed as a percentage. A high published ratio can therefore coexist with a
low fill, and cross-country comparisons of the label are not like for like.

### 5.5 Can shortfalls be anticipated from public pre-close information?

The revised evaluation uses the preceding weekday before the earlier of the recorded bid deadline
and held date, where both are available. Past results enter the information set on the weekday after
their date-only release proxy. Offers enter if their publication proxy is on or before the origin.
Models are refitted monthly, and models and simple rules can use newly available history at each
origin. The development period is 2020–22, the historical holdout is 2023–24, and the previously
inspected comparison is 2025–26. The versioned protocol records the post-evaluation revisions.

The original gate combines a log-loss improvement of at least 0.02 nats with an eight-auction block
interval below zero and volume capture at least as high as the development-selected baseline. The
historical threshold targets a nominal 25% alert rate. We also report realised rates, comparison with
the baseline with the highest volume capture, and an ex-post ranking at an equal 25% rate.

In the historical holdout, the full logistic model reduced log loss by 0.137 nats at the Kenyan
maturity level and by 0.127 nats at the Ghana auction level. At their historical thresholds, the
models captured 73.9% and 43.0% of shortfall volume and alerted on 38.5% and 15.4% of rows, respectively.
At the equal-rate retrospective ranking, Kenya's model captured 52.2% versus 49.9% for the best simple
rule, and Ghana's captured 57.4% versus 55.6%. In 2025–26, Kenya's difference was +0.023 nats and
Ghana's was −0.083, with both intervals crossing zero. Delaying result availability and offer
publicity by one further weekday leaves that pattern intact. Some Kenyan auction-wide specifications
meet the original gate in 2025–26 with few alerts and minimal volume captured. These are unadjusted
comparisons across several candidates and markets (replication package, Tables F1–F6 and the delayed-publication tables).

For maturity-shift magnitude, a rolling six-auction median gave holdout mean absolute errors of
15.7 days in Uganda and 23.6 days in Kenya, close to ridge regression and better than assuming zero shift.

We conclude that, with these public data, a recent-history baseline is the appropriate monitoring
benchmark, and that the evidence does not support a deployable prediction product.

## 6. Discussion

**What the decomposition says, and does not.** In Uganda, auctions that fall short do so with bids
on the table; in Kenya and, until recently, Ghana, they fall short mainly because bids did not reach
the offer. This is consistent with BoU exercising the right it states in every invitation to reject or
reduce bids. It is also consistent with IMF staff's reading of post-pandemic sold-to-offer divergence as
more active allocation management (Qu 2026). But the notices do not record why bids were not accepted,
so we do not attribute the pattern to a pricing policy. Gross bids include all submitted prices; enough
volume does not mean enough volume at an acceptable yield.

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
* Date-only release proxies and weekday-based forecast origins. A statutory-holiday screen finds no
  case in which a holiday lets a result count as public at a forecast origin early (A9). Verified
  historical publication timestamps would still improve the timing reconstruction.
* Archive gaps (Uganda 2019; Kenya before 2017; seven Ghana attachments) and numbering typos in BoU
  releases and invitations. Invitations are joined to results by scheduled auction date, and every
  join where number and date disagree is flagged. Coverage tables and conditional missing-auction scenarios are reported.
* OCR is used for a minority of Uganda documents (image tables); their values pass the same validation
  rules, and one OCR digit was checked against the rendered image (#1233).
* Face values only: no cash proceeds, cost or fiscal simulations.
* The 2023–24 forecasting holdout was outside the pilot's scored period. The revised design and
  previously inspected 2025–26 evaluation remain retrospective.

## 8. Conclusion and further research

Official notices from three African bill markets show that the same headline auction outcome can
describe different events. Uganda's shortfalls occurred with bids in hand. Kenya's and Ghana's arose
mainly because bids did not reach the offer, although Ghana's pattern weakened in 2025–26. Totals
masked maturity-level misses, and filled auctions moved the maturity of new issuance in opposite
directions in Uganda and Kenya. Publishing offer, bids and acceptances per maturity, the split of any
shortfall, the realised versus advertised maturity and a defined cover ratio would make these
differences visible to investors, analysts and debt managers.

Several extensions follow. First, bid-level or price-schedule data, where debt offices can share them,
would show whether unaccepted bids were priced above the yields the issuer accepted, turning the
accounting split into evidence on pricing decisions. Second, the framework applies directly to
Treasury bond auctions and to other markets that publish maturity-level auction notices, which would
give a wider view of how common each pattern is. Third, linking the maturity shift to redemption
profiles would show whether filled auctions ease or concentrate rollover pressure. Finally, an
operational warning claim requires a prospective record of forecasts written down before outcomes are
known; a protocol for such a record is registered in the replication package.

## Declarations

**Declaration of competing interest.** The authors declare that they have no known competing financial
interests or personal relationships that could have appeared to influence the work reported in this
paper.

**Funding.** This research did not receive any specific grant from funding agencies in the public,
commercial, or not-for-profit sectors.

**Data availability.** The official notices are public on the websites of the Bank of Uganda, the Central Bank of Kenya and the Bank of Ghana. Source URLs, SHA-256 hashes, the correction ledger, derived tables and all code are in a public replication package (link withheld for anonymised review). Source PDFs are not redistributed.

**Declaration of generative AI and AI-assisted technologies in the writing process.** During the preparation of this work the authors used Claude (Anthropic), an AI assistant, to write and test data-processing code, check extracted values against source documents and draft and edit text. After using this tool, the authors reviewed and edited the content as needed and take full responsibility for the content of the publication.
[Authors: confirm or edit this statement so that it matches how you used the tool.]


## Figures

Figure 1. Share of shortfall volume from bids short of the offer (D) versus bids not accepted (R).

## References
