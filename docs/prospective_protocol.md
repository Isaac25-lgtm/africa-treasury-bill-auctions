# Prospective forecast evaluation (registered, not started)

**Registered:** 6 November 2026. **Status:** not started. No operational claim is made from the
historical evaluation (see `outputs/reports/decision_memo.md`). This protocol says how such a claim
could be earned. It is fixed before any prospective prediction exists.

## Why

The full logistic model beat the strongest simple baseline on the locked 2023–24 holdout for Kenya by
maturity and Ghana auction-wide. The 2025–26 intervals crossed zero, and that period had already been
inspected. Only predictions written down before the outcomes exist can settle the question.

## What is frozen

* **Candidates:** full L2 logistic (history + announced offer + calendar) for Kenya by maturity and
  Ghana auction-wide. These are the two cells with historical gains. Uganda is not included: none of
  its common-window shortfalls had bids short of the offer, and its historical gains were not
  established.
* **Comparator:** the strongest development baseline for the same cell, as in F6.
* **Code and settings:** the repository commit that first contains this file. Training uses all
  results public before each origin. No tuning, no feature changes and no recalibration during the
  evaluation.
* **Information rule:** origin is the close of the last business day before bid closure. A result
  counts only from the next business day after its notice date. Holidays come from the A9 calendar.

## Procedure

1. Before each Kenyan Thursday and Ghanaian Friday bid closure, run the model on data public at the
   origin. Write the class probabilities to `prospective/predictions.csv`, together with the origin
   date and the commit hash.
2. Commit and push that file **before** bid closure. The GitHub push time is the public timestamp.
   A prediction pushed after closure is marked late and is excluded.
3. After the result notice appears, append the outcome to `prospective/outcomes.csv` in a separate
   commit. Predictions are never edited.

## Evaluation and stopping rule

* **Sample:** 52 weeks or 150 Kenyan maturity rows, whichever comes later; Ghana over the same weeks.
  No interim significance testing. A single descriptive status note at 26 weeks is allowed.
* **Pass rule (as Gate 4):** mean log-loss improvement of at least 0.02 nats per row over the
  comparator, with the 8-block moving-block 95% interval entirely below zero, **and** captured
  shortfall volume at a 25% alert budget at least that of the best of the four baselines.
* **Reporting:** results are reported whether the model passes or fails, with realised alert rates
  and calibration tables. A failure ends the operational claim for that cell.

## Not covered

Any change to models, features or thresholds starts a new registration with a new start date.
