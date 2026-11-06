"""Exact accounting definitions (handoff Section 3).

O = offer, B = valid gross bids tendered, A = accepted face amount (same basis).

* signed deviation          A - O ; normalized A/O - 1
* gross bid coverage        B / O
* offer fill                A / O
* bid acceptance share      A / B  (defined only for B > 0)
* total positive shortfall  S = max(O - A, 0)
* volume-driven shortfall   D = max(O - B, 0)
* unaccepted-bid remainder  R = S - D = max(min(O, B) - A, 0)

Identity S = D + R holds whenever 0 <= A <= B (asserted). Volume shares are ratios
of sums over matched populations, never means of ratios and never pooled across
currencies.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def shortfall_parts(O, B, A):
    """Return (S, D, R) arrays. Requires 0 <= A <= B (within tolerance) and O > 0."""
    O = np.asarray(O, dtype=float)
    B = np.asarray(B, dtype=float)
    A = np.asarray(A, dtype=float)
    S = np.maximum(O - A, 0.0)
    D = np.maximum(O - B, 0.0)
    R = np.maximum(np.minimum(O, B) - A, 0.0)
    ok = (A <= B + 1e-9) & (A >= 0)
    if not np.all(np.isclose(S[ok], D[ok] + R[ok], rtol=0, atol=1e-6)):
        raise AssertionError("S != D + R for a population with A <= B")
    return S, D, R


def outcome_class(O, B, A, tol: float = 0.0, convention: str = "policy"):
    """Three-way class.

    0 = met/exceeded offer, 1 = missed with B < O, 2 = missed with B >= O.

    ``policy``  : miss if A < (1 - tol) O ; split stays at B >= O (handoff preferred)
    ``pilot``   : both cut-offs move to (1 - tol), reproducing the pilot sensitivity code
    At tol = 0 both conventions coincide. Ties at exactly A == (1 - tol) O count as met.
    """
    O = np.asarray(O, dtype=float)
    B = np.asarray(B, dtype=float)
    A = np.asarray(A, dtype=float)
    miss = A < (1 - tol) * O
    split = B < O if convention == "policy" else B < (1 - tol) * O
    return np.where(~miss, 0, np.where(split, 1, 2))


def near_threshold_mixed(O, B, A, tol: float) -> np.ndarray:
    """Material misses where (1 - tol) O <= B < O: classes differ between conventions."""
    O = np.asarray(O, dtype=float)
    B = np.asarray(B, dtype=float)
    A = np.asarray(A, dtype=float)
    return (A < (1 - tol) * O) & (B < O) & (B >= (1 - tol) * O)


def volume_share(D, S) -> float:
    """sum(D) / sum(S); NaN (displayed 'undefined') when there is no shortfall."""
    s = float(np.nansum(S))
    return float(np.nansum(D)) / s if s > 0 else float("nan")


def add_ratios(df: pd.DataFrame, o="O", b="B", a="A") -> pd.DataFrame:
    out = df.copy()
    O, B, A = out[o].astype(float), out[b].astype(float), out[a].astype(float)
    out["dev"] = A - O
    out["dev_norm"] = A / O - 1
    out["coverage"] = B / O
    out["fill"] = A / O
    out["acceptance"] = np.where(B > 0, A / B.where(B > 0), np.nan)
    S, D, R = shortfall_parts(O, B, A)
    out["S"], out["D"], out["R"] = S, D, R
    out["cls"] = outcome_class(O, B, A)
    return out


def auction_wide(tenor_rows: pd.DataFrame, keys=("country", "event_id"), o="O", b="B", a="A") -> pd.DataFrame:
    """Sum O, B, A first, then compute S, D, R (aggregation before shortfall)."""
    g = tenor_rows.groupby(list(keys), sort=True)
    agg = g[[o, b, a]].sum(min_count=1).reset_index()
    agg["n_tenors"] = g.size().to_numpy()
    return add_ratios(agg, o, b, a)


def across_tenors(tenor_rows: pd.DataFrame, keys=("country", "event_id")) -> pd.DataFrame:
    """Compute S, D, R at each maturity, then sum positive shortfalls per event."""
    t = add_ratios(tenor_rows)
    out = t.groupby(list(keys))[["S", "D", "R"]].sum().reset_index()
    out = out.rename(columns={"S": "S_tenor", "D": "D_tenor", "R": "R_tenor"})
    out["tenor_misses"] = t.assign(m=t.cls > 0).groupby(list(keys)).m.sum().to_numpy()
    return out


def weighted_maturity(amounts, days) -> float:
    amounts = np.asarray(amounts, dtype=float)
    days = np.asarray(days, dtype=float)
    tot = np.nansum(amounts)
    if not np.isfinite(tot) or tot <= 0:
        return float("nan")
    return float(np.nansum(amounts * days) / tot)


def maturity_profile(tenor_rows: pd.DataFrame, keys=("country", "event_id"), days_col="tenor") -> pd.DataFrame:
    """Offered vs accepted face-value-weighted maturity of one auction's bill issuance.

    Undefined (NaN) when there is no accepted amount or no positive offer.
    """
    rows = []
    for k, g in tenor_rows.groupby(list(keys), sort=True):
        off = weighted_maturity(g.O, g[days_col])
        acc = weighted_maturity(g.A, g[days_col])
        share364_o = g.loc[g.tenor == 364, "O"].sum() / g.O.sum() if g.O.sum() > 0 else np.nan
        share364_a = g.loc[g.tenor == 364, "A"].sum() / g.A.sum() if g.A.sum() > 0 else np.nan
        rows.append((*k, off, acc, acc - off, share364_o, share364_a, share364_a - share364_o))
    return pd.DataFrame(rows, columns=[*keys, "mat_offered", "mat_accepted", "mat_shift",
                                       "share364_offered", "share364_accepted", "share364_shift"])
