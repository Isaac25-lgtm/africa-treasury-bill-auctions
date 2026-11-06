# Research decision memo

**Snapshot and revision date** 6 November 2026, East Africa Time

**Decision** Continue with the measurement paper after author source review. Keep forecasting as a
secondary historical evaluation. The evidence is insufficient for operational alerts.

## Measurement

| Country | Common-window auctions | Shortfalls | Shortfalls with sufficient bids | Volume share from insufficient bids |
|---|---:|---:|---:|---:|
| Uganda | 91 | 34 | 34 | 0.0% |
| Kenya | 198 | 70 | 12 | 81.1% (70.8–89.5%) |
| Ghana | 199 | 81 | 8 | 74.5% (61.0–90.2%) |

Ghana's revised analysis includes 151 valid two-maturity tenders over the full period, including
10 in the common window. The full-period result-side share is 79.7% across 447 tenders. The corrected
offer-discrepancy exclusion leaves 90 Ugandan, 197 Kenyan and 198 Ghanaian auctions in the common
window, with unchanged shares at reported precision. Uganda's two missing invitations sum to
UGX 645bn. Its share would reach 21.7% if both attracted zero bids at the invitation targets.

Among auctions that met their totals, the median accepted-minus-offered maturity shift was +26.9
days in Uganda and −46.4 in Kenya using the result offers. The matched announced-offer comparison
gives +29.1 and −46.4 days. The main analysis is a descriptive accounting split. An individual
shortfall can include both insufficient submitted volume and bids left unaccepted.

## Forecasting

The original scoring rule is retained in F6 alongside revised historical predictions, the
realised alert rates, a positive-volume criterion and an equal-rate retrospective ranking.
The full logistic model improves historical holdout log loss by 0.137 nats for Kenya by maturity
and 0.127 nats for Ghana auction-wide. The 2025–26 intervals cross zero in both cases. A one-weekday
publication delay leaves the pattern intact. The historical 25% threshold targets a nominal rate,
and its realised rates vary. The equal-rate ranking is ex post. The 2025–26 comparison was inspected
in the pilot.

## Audit and release

The manifest replay verified 2,821 successful source URLs before parsing. A5 compared 869 of
946 expected quantity cells and 102 dates after a second extraction using the same parsers.
All compared quantities and dates agreed. The source audit separately records six same-scope
Ghana numeric discrepancies and eight scope discrepancy rows. The lead author decided on
2026-11-06 to retain the section-1 values in all of them and signed off the two ledger
corrections. Substituting the following-notice totals leaves Ghana's shares unchanged (T5b).

The project contribution is the notice-level decomposition and maturity evidence across the
three markets. Read it alongside the IMF work on Uganda's sold-to-offer patterns and the OECD
work on auction predictability and cover ratios. See the literature matrix for scope and links.

The copy remains a draft pending the Uganda invitation-join checks, institutional review, final release
identifiers and a genuinely prospective forecast evaluation if an operational claim is pursued.
