# Reading a Treasury bill auction: three numbers the headline hides

*Policy brief — draft for author review. Evidence: official auction notices of the Bank of Uganda,
the Central Bank of Kenya and the Bank of Ghana, 2017–2026. Figures from the project's generated
tables (`outputs/reports/key_numbers.json`).*

## The problem

After each bill auction, the headline is usually one number: the auction was under- or
over-subscribed, or its "bid-to-cover" ratio was high or low. Two auctions with the same headline can
mean very different things for a debt manager:

1. **How much of the gap came from bid volume?** Part can come from bids falling short of the offer
   and part from submitted bids left unaccepted. Both can occur in the same auction.
2. **Which maturities were sold?** An auction can fill its total target while under-selling some
   maturities and over-selling others — changing when the new debt must be repaid.
3. **What does the cover ratio divide by?** The published ratio is sometimes bids ÷ accepted and
   sometimes bids ÷ offered.

## What the notices show (13 January 2023 – 30 October 2026)

**The accounting split differs across the three markets.**

| | Auctions | Fell short of offer | Share of shortfall volume because bids did not reach the offer |
|---|---:|---:|---:|
| Uganda | 91 | 34 | **0%** — every shortfall had enough bids |
| Kenya | 198 | 70 | **81%** |
| Ghana | 199 | 81 | **74.5%** (falling to 64% in 2025–26) |

**Filled totals hide maturity misses.** Of auctions that met the overall offer, **88% in Uganda** and
**85% in Kenya** still missed the offer on at least one maturity.

**The maturity of new debt moved away from the plan.** In fully funded auctions the accepted mix was
on median **27 days longer** than the mix in the results notice in Uganda (40 days in 2025–26) and
**46 days shorter** in Kenya (17 days shorter in 2025–26). Comparing with the original invitations
where available gives the same directions.

**The cover ratio is not one measure.** Uganda's published ratio matched bids ÷ offered in most 2020
releases and bids ÷ accepted from 2021; Kenya's matches bids ÷ accepted, with a separate
"performance rate" equal to bids ÷ offered.

## A worked Ugandan example — auction #1237, 4 November 2026

| | 91-day | 182-day | 364-day | Total |
|---|---:|---:|---:|---:|
| Offered (UGX bn) | 15.0 | 35.0 | 300.0 | 350.0 |
| Bids (UGX bn) | 81.9 | 60.3 | 933.5 | 1,075.7 |
| Accepted (UGX bn) | 4.2 | 10.3 | 424.5 | 439.0 |

The headline says "oversubscribed and over-filled". Underneath, bids exceeded the offer at every
maturity, yet the 91- and 182-day bills sold well under their offers, and the 364-day bill sold more
than offered. The accepted mix was 23 days longer than advertised. Source: BoU results release #1237.

## What this does not show

These are accounting facts from published totals. Notices do not say *why* bids were not accepted;
aggregate bids include all submitted prices, so "enough bids" does not mean "enough at an acceptable
yield". The figures describe face values of each auction's issuance, not cash raised, cost or the
portfolio's average maturity. Three markets and these years do not establish patterns elsewhere.

## Can a model warn in advance?

Some models improved probability forecasts in the historical holdout. The evidence across periods
and alert thresholds is insufficient to establish a reliable warning rule for operational use.

## Recommendations for public auction reporting

1. Publish offer, bids and accepted amount **per maturity**, together with the total.
2. Show the shortfall split: **bids short of the offer** versus **bids not accepted**.
3. Report the **advertised and accepted weighted maturity** of each auction's issue.
4. **Define the cover ratio** (bids ÷ offered or bids ÷ accepted) and keep it constant, or publish both.
5. When the offer changes after the invitation, publish the revision and its date.
6. Keep a complete, numbered archive; several releases are missing or reuse an auction number.
