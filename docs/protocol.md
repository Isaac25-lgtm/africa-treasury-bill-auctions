# Pre-analysis protocol

**Frozen:** 2026-11-06 (EAT), before the rebuilt panel's outcome summaries, robustness tables or any
forecast scores were computed. The only outcome information seen before freezing was (a) the pilot
summaries reproduced in the handoff and (b) a few dozen sample notices read to write the parsers.
Any later change is logged at the end of this file with its date and reason, and the tables it affects
are labelled as revisions.

## 1. Questions and hierarchy

| Aim | Status | Question |
|---|---|---|
| A1 | confirmatory | What share of nominal auction shortfall is mechanically attributable to gross bids falling short of the offer (D), as opposed to bids not accepted (R)? By country and common window, auction-wide and by maturity. |
| A2 | confirmatory | In Uganda and Kenya, how far does the accepted 91/182/364-day mix diverge from the advertised mix, including when the overall offer is met? |
| A3 | secondary | Do public pre-close models improve calibrated warnings over the strongest simple baseline? |
| A4 | practical | Template and brief; prediction value quantified only where A3 passes Gate 4. |

Measurement, prediction, institutional interpretation and causality are reported separately.
No causal mechanism (e.g. "the issuer rejected expensive bids") is asserted from these data.

## 2. Definitions (handoff Section 3, implemented in `src/treasury_auctions/measures.py`)

O offer, B gross bids tendered, A accepted face amount, on the same reporting basis.
S = max(O − A, 0); D = max(O − B, 0); R = S − D = max(min(O, B) − A, 0).
Volume share = Σ D / Σ S over a matched population with Σ S > 0 (undefined otherwise); a ratio of
sums, never a mean of ratios, never pooled across currencies.

* **Auction-wide:** sum O, B, A over the three maturities first, then compute S, D, R. Requires all
  three maturities present (otherwise undefined and excluded).
* **By maturity:** S, D, R per maturity row, then summed.
* **Classes** at exact threshold: 0 met (A ≥ O), 1 miss with B < O, 2 miss with B ≥ O.
* **Materiality** τ ∈ {0, 5%, 10%}: a row is a miss if A < (1 − τ) O. Primary ("policy") convention
  keeps the B ≥ O split; the pilot convention moving both cut-offs to (1 − τ) is reported as an
  alternative, together with the count of near-threshold mixed cases. Ties at exactly (1 − τ) O are
  "met". For material-miss volume shares, D and S are the original (un-thresholded) amounts summed
  over material misses.
* **Maturity:** face-value-weighted maturity Σ A_j d_j / Σ A_j vs Σ O_j d_j / Σ O_j; primary with
  nominal d ∈ {91, 182, 364}; sensitivity with parsed settlement-to-maturity days (80–380 accepted).
  Also the 364-day share shift. Interpreted as the maturity of that auction's bill issuance only.

## 3. Offer versions

* `result`: the offer printed with results. Widest coverage; primary for the full-sample tables.
* `announced`: the pre-close offer — Uganda invitation to tender; Kenya section C of the preceding
  results notice; Ghana section 3 of the preceding notice (combined target only). The latest version
  first public on or before the bid date is used. Reported for the matched subset with coverage.
* A disagreement between versions is never silently corrected; it is listed (A3 reconciliation) and
  the headline is re-estimated excluding those events.

## 4. Samples and windows

* Snapshot cutoff 2026-11-06 (no document dated after it).
* Common window 13 Jan 2023 – 30 Oct 2026 (the pilot's three-country window, kept for comparability).
* Recent window 1 Jan 2025 – 30 Oct 2026; and each country's full available window.
* Exclusions: conflicting duplicate documents; blocked parses (listed with reason); auctions missing a
  maturity (auction-wide only). Ghana is an aggregate replication: its tenor offers are never imputed.

## 5. Inference

Moving-block bootstrap over time-ordered auctions with blocks of 4, 8 and 13 auctions (all reported;
8 is the headline), 2000 replicates, seed 20261106; tenor rows of one auction resampled together.
Intervals describe sampling variation in the audited sample, not archive coverage bias, which is
handled by the coverage tables and the missingness bound (T6). With Σ D ≈ 0 the interval is
degenerate; report counts and the missingness bound instead of a normal approximation.

Robustness (T5): exclude OCR rows; matched-invitation subset; exclude offer-mismatch events;
leave-one-year-out; thresholds; by-year table (T2).

## 6. Forecasting (secondary)

* **Origin:** close of the business day before the bid date. A past result is usable only if its
  `available_from` (next business day after its date-only release proxy) ≤ origin. Announced offers
  usable only if first public ≤ origin. Same-auction outcomes, cut-offs, yields and current-batch
  redemptions are forbidden predictors.
* **Folds:** monthly walk-forward refits; training rows' labels must be public before the month start.
* **Periods:** development 2020-01 → 2022-12 (choose the strongest baseline by log loss);
  **locked holdout 2023-01 → 2024-12** (never evaluated by the pilot);
  replication 2025-01 → 2026-10 (the pilot's test period — reported, but labelled previously inspected).
* **Baselines:** smoothed unconditional series frequency; trailing-12 frequency; previous-state
  transition; blend of the last two (pilot adaptive baseline). Maturity shift: no shift, previous,
  rolling median of 6.
* **Models:** L2 logistic (history-only; full = history + announced offer + calendar); shallow
  histogram gradient boosting (depth 3, 150 iterations, learning rate 0.05, L2 1.0, min leaf 20);
  pooled logistic with country indicators; zero-shot transfer from the other countries (history
  features); locally recalibrated transfer. Ridge (α = 10) and boosting for maturity shift.
  No tuning beyond these fixed settings; no oversampling; no test-set calibration.
* **Metrics:** multiclass log loss (clip 1e-6), multiclass Brier, any-miss Brier and AUC,
  reliability tables, class counts; paired per-auction log-loss differences vs the strongest
  baseline with moving-block intervals; alert budget 25% with threshold set from each model's own
  earlier predictions; captured shortfall volume, miss recall, false alerts; MAE and 90th-percentile
  absolute error for maturity shift.
* **Gate 4 (smallest useful gain, provisional):** on the locked holdout, mean log-loss improvement of
  at least 0.02 nats per row vs the strongest development baseline with the 8-block 95% interval
  entirely below zero, **and** captured shortfall volume at the 25% alert budget at least the
  baseline's. To be confirmed or revised by the authors; any revision is logged below and does
  not change the reported numbers.

## 7. Deviations log

| Date | Change | Reason | Affects |
|---|---|---|---|
| 2026-11-06 | Gate 4 candidates restricted to non-baseline models (baselines are comparators, not candidates). | Implementation slip found on first scoring: baselines appeared as "passing". | F6 table only; rule unchanged. |
| 2026-11-06 | Added a *post-hoc* stricter Gate 4 variant: volume captured must also be ≥ the best of all four baselines (not only the log-loss-strongest one). Pre-registered rule is still reported as primary. | The strongest development baseline captured 0% of volume in some holdout cells (alert rate ≈ 0–3%), which makes the pre-registered volume test trivially passable. | F6 column `passes_gate4_strict_volume` (labelled post hoc). |
| 2026-11-06 | Added realised alert rates and a retrospective top-25% ranking diagnostic next to the fixed-budget results. | Thresholds set from earlier predictions drift under distribution shift; realised rates differ by model. Diagnostic only, ex post. | F5/F6 extra columns. |
| 2026-11-06 | Second extraction for text-layer PDFs switched from `pdftotext -layout` (Xpdf 4.00) to OCR of the rendered page. | Xpdf shifted table rows on some CBK/BoU layouts, so it was not an independent check. | A5 table. |
| 2026-11-06 | Uganda events keyed by held date when one printed auction number appears on two releases with different held dates (numbering typo); earliest keeps the number. | Two such cases found (1086, 1171); otherwise both auctions were quarantined as conflicts. | +2 Uganda events. |
| 2026-11-06 | Kenya due dates parsed for the settlement-to-maturity sensitivity. | Field was not yet extracted when the protocol was frozen. | T4 `median_actual_days` for Kenya. |
| 2026-11-06 | Sum Ghana results over the validated target scope and check offer scope across versions. Use the same discrepancy list in the reconciliation and the exclusion sensitivity. | A fixed three-maturity aggregation omitted 151 valid tenders and the original exclusion retained the flagged events. | Ghana measurement and forecast tables, A3, A8 and T5. |
| 2026-11-06 | Separate advertised and result-side maturity comparisons. Add a zero-bid stress test at the observed missing Uganda invitation amounts. | Clarify the offer estimands and make the missingness scenario conditional on stated targets. | T4c and T6. |
| 2026-11-06 | Update simple-rule histories at the same origin as model histories. Use the earlier recorded deadline or held date, use one common Ghana release proxy per notice, and test an additional weekday delay for public information. | Correct the information-set asymmetry and quantify sensitivity to date-only proxies. These changes were made after the initial evaluation. | F0–F6 and delayed-publication sensitivity. |
| 2026-11-06 | Keep the historical gate and report a positive-volume variant and an equal-rate retrospective ranking. Average across ties at the ranking boundary. | The historical quantile threshold does not cap realised alerts. The ranking is an ex-post diagnostic. | F5 and F6. |
| 2026-11-06 | Count expected cells, compare Ghana targets and check dates in the second extraction. | The original denominator omitted non-comparisons and Ghana combined targets. The revised check still uses the same parsers and correction ledger. | A5. |
