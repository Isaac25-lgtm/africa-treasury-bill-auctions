# Closest work and evidence review

**Search date (UTC):** 2026-11-06. **Databases used in this run:** Crossref REST API (metadata and
keyword search; full log in `docs/literature_raw/crossref_search_log.json`), publisher / institution
landing pages and full texts where public. The IMF chapter (item 1) was read from a PDF the user
obtained after completing the eLibrary human-verification step. **Not reached in this run:** Google
Scholar, RePEc/IDEAS, SSRN and NBER search interfaces, OECD chapters (HTTP 403), Cooperative University
of Kenya repository (connection refused). These are
listed as pending checks; no claim of an exhaustive search is made.

Verification key: **V-full** full text read; **V-page** official landing page read; **V-meta**
bibliographic metadata verified via Crossref only; **U** not verified in this run (content as
summarised in the project handoff's pilot review; treat as a lead).

| # | Work | Status | Market / period | Target & design | What it establishes for us | Incremental claim of this project |
|---|---|---|---|---|---|---|
| 1 | Qu, H. (2026). "Uganda's Government Bond Yield Curve: Structure, Drivers, and Policy Implications." In IMF African Dept., *Uganda: Selected Issues*, IMF Country Report 26/216, pp. 4–16. DOI 10.5089/9798229057196.002.A001 | **V-full** (chapter PDF read 6 Nov 2026, supplied by the user; marked "Not for Redistribution", so not stored in the repository) | Uganda; BoU primary-market data 2015–2025 (monthly sold-to-offer ratios, bills and bonds separately); yields 2011–2025 | Fisher-style yield decomposition (US real yield, US inflation swap, inflation and credit risk premia) and Nelson–Siegel factors, each regressed on macro, fiscal, election and market-condition controls; the monthly T-bill sold-to-offer ratio enters only as a control (credit-premium regressions: insignificant; NS level: −0.378, p < 0.01) | Documents that, before the pandemic, sold amounts tracked offers, and that afterwards bonds were undersold (average ratio ≈ 0.9) and bills oversold (≈ 1.1). Interprets the divergence as more active allocation to manage borrowing costs, and argues that it weakens issuance predictability and auction credibility. **The existence of the divergence and the active-allocation reading are therefore not novel.** | It does **not** split shortfalls into bids short of the offer versus bids not accepted, has no auction-level or 91/182/364-day maturity-level measures, no accepted-versus-advertised maturity mix, no Kenya/Ghana comparison, no cover-ratio definition audit and no pre-auction forecasting. Our Uganda result (all 34 common-window shortfalls had B ≥ O) is consistent with its reading but is reported as accounting, without attributing motive. |
| 2 | Njeri, K. M., Anyika, E., Hadullo, K. (2025). Machine learning model for treasury bill yields prediction in Kenya. *Global Journal of Engineering and Technology Advances* 24(3), 12–20. DOI 10.30574/gjeta.2025.24.3.0259. Received 25 Jul 2025, accepted 1 Sep 2025 | V-full | Kenya, CBK 364-day yields, Jul 2022 – Jun 2024 (weekly), plus monthly inflation and CBR | ARIMA, SVM, Prophet and a Gaussian-copula ensemble; 12 target lags; macro lagged 4 weeks with forward fill; single chronological 80/20 split; MAE 0.1187 ensemble vs 0.1806 SVM | Kenyan ML forecasting of *yields* exists | Different target (issuance execution, not price). Our own reading of their Table 2: the ensemble's MASE is reported as 1.1488, i.e. above 1 — larger error than the scaled naive benchmark — which supports our emphasis on strong recent-history baselines and release-aware folds. Their macro alignment does not document release vintages. The CUK repository record could not be opened (pending). |
| 3 | Beetsma, R., Giuliodori, M., Hanson, J., de Jong, F. (2020). Determinants of the bid-to-cover ratio in Eurozone sovereign debt auctions. *Journal of Empirical Finance* 58, 96–120. DOI 10.1016/j.jempfin.2020.05.005 | V-meta | Eurozone sovereign auctions | Econometric determinants of bid-to-cover (per handoff: secondary yields, lagged domestic/foreign cover) | Bid-to-cover determinants studied in deep markets | We separate bid volume from acceptance and from the offer; test portability across markets with local recalibration. Full text pending. |
| 4 | Tindall, M. L., Perez, M. A. (31 Aug 2021). *Treasury auctions during the pandemic: stresses but few surprises*. Federal Reserve Bank of Dallas | V-page | US 10-year note auctions | "Surprise indicator" from models of bid-to-cover and a synthetic tail (high yield minus prior close); ML used to select scenarios. Defines bid-to-cover as bids ÷ accepted | Prior ML-assisted auction monitoring; note the B/A definition | Quantity misses and maturity reallocation rather than price surprises; definitional audit of the published ratio (B/A vs B/O) in our markets. |
| 5 | Gao, J., Epp, A. (Oct 2026). *Auction Timing Under Limited Information: Evidence from Sovereign Bond Auctions*. Bank of Canada Staff Analytical Paper 2026-51. DOI 10.34989/sap-2026-51 (not yet in Crossref) | V-page | Canada | Same-day volatility vs auction tails; scheduled releases and volatility | Timing of public information matters for auction outcomes | Different outcome (tail vs shortfall); motivates our strict release-time rules. |
| 6 | U.S. GAO (published 31 Mar 2026; released 3 Apr 2026). *Federal Debt Management: Treasury Is Meeting Borrowing Needs but the Deteriorating Fiscal Outlook Poses Risks*. GAO-26-107529 | V-page (front matter verbatim; Appendix II via fetch-tool summary, to re-read) | US, FY2014–FY2025 | Fixed-effects regressions of bid-to-cover on offering size, separately for bills and notes/bonds; explicitly not causal. Defines bid-to-cover as bids ÷ offered | Official use of B/O; larger offers coincide with slightly lower cover | Same caution on causality; we show the published ratio's denominator varies by vintage in Uganda. |
| 7 | Hortaçsu, A., Kastl, J., Zhang, A. (2018). Bid Shading and Bidder Surplus in the US Treasury Auction System. *American Economic Review* 108(1), 147–169. DOI 10.1257/aer.20160675 (NBER w24024, 2017) | V-meta | US | Structural estimation with bidder-level bids | Questions about strategy/surplus require bid-level data | We claim accounting decomposition only; no bidder-behaviour inference. |
| 8 | Allen, J., Hortaçsu, A., Richert, E., Wittwer, M. (Jan 2026). *Entry and Exit in Treasury Auctions*. NBER WP 34646. DOI 10.3386/w34646 | V-page | Canada, 20+ years | Auction model with endogenous participation | Participation dynamics need bidder data | Out of scope; cited for limits of aggregate data. |
| 9 | OECD (2025). *Africa Capital Markets Report 2025*, chapter on local-currency bond markets | **U** (HTTP 403) | Africa (per handoff: LSEG-based) | Per handoff: predictability of auction sizes | Possible overlap on announced vs realised issuance | Pending verification; if confirmed, our contribution is official notice-level data, maturity decomposition and release-aware tests. |
| 10 | OECD (2026). *Global Debt Report 2026*, sovereign borrowing outlook | **U** (HTTP 403) | OECD | Per handoff: caution on bid volume as appetite | — | Pending. |
| 11 | World Bank (2021). *Uganda Debt Transparency Policy Note* | U (lead) | Uganda | Auction practices | Institutional context | Pending. |
| 12 | Umlauf, S. R. (1993). An empirical study of the Mexican Treasury bill auction. *Journal of Financial Economics*. DOI 10.1016/0304-405X(93)90010-9 | V-meta (Crossref search hit) | Mexico | Auction format / bidder behaviour | Early emerging-market T-bill auction evidence | Background only. |
| 13 | (2014). Forecasting weekly auction of the 91-day Treasury bill rates of Ghana. *IOSR Journal of Economics and Finance*. DOI 10.9790/5933-0354653 | V-meta (search hit) | Ghana | Rate forecasting | Ghana bill *rate* forecasting exists | Different target. |

## Narrative

The overlap that matters most is the IMF's 2026 Uganda chapter (Qu 2026), now read in full. It
documents a post-pandemic divergence between sold and offered amounts in monthly aggregates. Bills
were on average oversold and bonds undersold. It interprets this as more active allocation to manage
borrowing costs, and uses the ratio only as a control in yield regressions. We therefore do **not**
claim that discrepancies, or their link to active allocation, are new. The incremental evidence on
offer is narrower and measurable, and none of it appears in the chapter:

1. an accounting split of every shortfall into *bids short of the offer* (D) and *bids not accepted*
   (R), at auction and maturity level, on audited official notices for three markets;
2. the observation that a filled headline can coexist with large maturity-level misses and a shift
   in the face-value-weighted maturity of new issuance;
3. a vintage audit showing the published "bid to cover" changes denominator over time;
4. a release-aware test of whether public pre-close information improves warnings.

**Gate 3 outcome:** the IMF chapter does not tabulate (1)–(4), so the claim stands as stated. Kenyan
and Ghanaian bill work found in this run concerns yields or rates, not issuance execution. The
deep-market auction literature (US, Eurozone, Canada) studies cover ratios, tails and bidder
behaviour with richer data; it supports our restraint about mechanisms.

**Pending before title lock:** OECD 2025/2026 chapters; CUK repository
record; Google Scholar / RePEc / SSRN forward-citation pass on items 1–3; practitioner leads
(Afronomics record, USIU dissertation, IISTE Ghana paper).
