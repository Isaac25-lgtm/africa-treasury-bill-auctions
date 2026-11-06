# Research decision memo

**Date:** 6 November 2026 · **Snapshot cutoff:** 6 November 2026 · **Run record:**
`outputs/reports/run_record.json` · **Numbers:** `outputs/reports/key_numbers.json`

## Verdict

**Proceed with an audited measurement paper; report forecasting as a pre-registered evaluation with a
largely negative result. Do not build or claim a prediction product.**

The measurement contrast replicates the pilot on an independently rebuilt, audited and larger panel
and survives every pre-specified robustness check. The forecasting gate fails in the sense that
matters: the one gain that passed in the locked holdout did not persist in the following period.
Title lock waits on one open item (Gate 3: the IMF 2026 Uganda chapter could not be read in this run).

## Evidence by gate

### Gate 1 — provenance and coverage: **passed, with documented gaps**

* 1,210 auctions: Uganda 227 (Jan 2017 – Nov 2026), Kenya 536 (Sep 2014 – Nov 2026; complete weekly
  from 2017), Ghana 447 (Jan 2018 – Oct 2026). Every value links to the source URL, the SHA-256 of
  the parsed bytes and the raw source line.
* Independent re-extraction (pdfminer.six; OCR/text-layer cross-checks for OCR rows): **882/882 cells
  agree** on 105 documents (stratified sample + all flagged/OCR rows). Software re-extraction, not human
  double entry.
* Gaps: Uganda 2019 (auctions 1047–1059) and 10 other numbers; 2 missing in the 2023–26 window. Kenya
  2014–2016 sparse. Ghana: 7 HTTP 404 attachments, 7 notices blocked (target scope ≠ maturities).
  One Kenyan issue quarantined (accepted > bids beyond rounding).
* Pre-close offers recovered and matched for most events; disagreements: Uganda #1235 (182-day),
  Kenya 13 Jul 2026 (91-day), Ghana #1582, #1710, #1860 (+#1842 unparseable). None corrected.
* Two Ghana values corrected through the committed ledger with cross-notice evidence; pending human
  sign-off (reviewer field).

### Gate 2 — measurement replication: **passed**

Common window 13 Jan 2023 – 30 Oct 2026, result-side offer, exact threshold (95% 8-block bootstrap):

| | Auctions | Shortfalls | of which B ≥ O | Volume share from insufficient bids |
|---|---:|---:|---:|---|
| Uganda auction-wide | 91 | 34 | 34 | 0.0% (Σ D = 0) |
| Uganda by maturity | 91 | 163 rows | 161 | 0.3% (0.0–0.7) |
| Kenya auction-wide | 198 | 70 | 12 | 81.1% (70.8–89.5) |
| Kenya by maturity | 198 | 313 rows | 27 | 93.6% (90.5–96.1) |
| Ghana auction-wide | 189 | 79 | 8 | 74.4% (60.1–89.9) |

* Identical to the pilot for Kenya (81.14%) and Ghana (74.39%); Uganda 0% on 91 auctions (pilot 81).
* Robust to 5%/10% materiality (UG 0.0/0.0; KE 82.2/82.4; GH 74.3/74.5), announced offers (UG 0.0%,
  KE 80.9%, GH 74.4%), excluding OCR rows, excluding offer-mismatch events, leave-one-year-out
  (KE 77.8–84.0%, GH 66.9–80.9%, UG 0.0%). Missingness: ≈32 unobserved fully volume-driven Uganda
  auctions would be needed to reach a 50% share; 2 are missing.
* **Direction changes over time:** Ghana's share fell from > 90% (2019–2024) to 70% (2025) and 49%
  (2026; 8 of 19 shortfalls with sufficient bids). Report as era heterogeneity, not a single constant.
* **Maturity (funded auctions, common window):** Uganda median +26.9 days (IQR +8.4 to +40.4; 57
  auctions; 364-day share +13.6 pp), Kenya −46.4 days (−82.7 to +5.5; 128; −13.7 pp). 2025–26: Uganda
  +40.1 (28), Kenya −17.0 (70). Full series smaller (UG +5.7, KE −11.7) — an era effect.
* **Masking:** 50/57 Ugandan and 109/128 Kenyan auctions that met the overall offer missed ≥ 1 maturity.

### Gate 3 — advance over closest work: **conditional (open item)**

Verified: Kenyan ML work targets *yields* (Njeri et al. 2025; single 80/20 split; reported MASE 1.15);
US/Eurozone/Canada work studies cover ratios, tails and bidder behaviour with richer data. **Not
verified:** the IMF 2026 Uganda Selected Issues chapter (closest overlap; eLibrary shows a human-
verification page) and the OECD 2025/2026 chapters (HTTP 403). Our claim is deliberately narrow: a
D/R decomposition per auction and maturity on audited official notices in three markets, the maturity
shift when the total is met, the ratio-definition audit, and a release-aware forecasting test.
**Action:** an author opens the IMF chapter and records whether it tabulates insufficient-vs-rejected
splits or tenor-level misses; if it does, narrow the claim to the cross-country comparison and the
maturity evidence.

### Gate 4 — forecast credibility: **failed for any deployable claim**

* Strongest development baselines: trailing-frequency/transition blend (Uganda; Kenya by maturity) or
  transition rule (auction-wide Kenya and Ghana).
* Locked holdout 2023–24: Kenyan maturity-level logistic models improved log loss by 0.11–0.14 nats
  per row (8-block intervals below zero) and captured 73–75% of shortfall volume at the 25% budget vs
  63% (best baseline 69%), partly via more alerts (38–40% vs 32%); retrospective ranking 52% vs 49%.
  No Ugandan or Kenyan auction-wide model passed; Ghana's pooled model passed only because its
  comparator issued almost no alerts.
* Replication 2025–26: the Kenyan maturity-level gain **vanished** (+0.017 to +0.034 nats). Two
  Kenyan auction-wide passes occur at 0–1% alert rates (no monitoring value). Uganda's pilot gain is
  not reproduced under strict timing.
* Maturity-shift magnitude: rolling median ≈ ridge/boosting (holdout MAE UG 15.7 vs 14.5; KE 23.6 vs
  23.9), far better than no-shift (22.1; 78.7).
* Provisional gain threshold (0.02 nats + volume criterion) still needs the authors' confirmation;
  the conclusion does not depend on it.

### Gate 5 — reproducibility and release: **local pass; remote pending verification**

* `python -m treasury_auctions --offline build` ran end to end (parse 199 s, audit 360 s, measure 74 s,
  evaluate 329 s, report 3 s); **14/14** programmatic table/figure checks pass; 47 tests pass; lint clean.
* Fixture-only integration (no network) passes and is what CI runs.
* Rights: source PDFs not redistributed; derived factual tables attributed; code MIT.

## Deviations from protocol (all logged in `docs/protocol.md`)

Gate-4 candidate restriction (baselines excluded), a post-hoc stricter volume comparison (reported
alongside, not instead of, the pre-registered rule), alert-rate and ranking diagnostics, second-
extraction engine change (Xpdf row shifts → pdfminer), Uganda reused-number keying, Kenya due dates.

## Live blockers / decisions for the authors

1. IMF 2026 Uganda chapter and OECD chapters: read and record overlap (Gate 3).
2. Confirm or revise the Gate-4 gain threshold (does not change conclusions).
3. Human sign-off on the two ledger corrections.
4. Authorship, affiliations, institutional review of Section 2, journal targeting (not started).

## Exact next actions

* Open the IMF eLibrary chapter in a browser; add findings to `docs/literature_matrix.md`.
* Review `manuscript/manuscript_draft.md` §2 (institutional detail) and the policy brief.
* Run `python -m treasury_auctions inventory && python -m treasury_auctions fetch` after new auctions to
  extend the panel; forecasts for genuinely unseen auctions can then be scored prospectively.
