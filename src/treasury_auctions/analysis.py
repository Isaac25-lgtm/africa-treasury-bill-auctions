"""Confirmatory measurement (handoff Section 7 Phase D, aims 1-2).

All tables are written to ``outputs/tables`` with a ``*_source.csv`` row-id file
where a figure uses them. Every number in the manuscript must come from here.

Estimands
---------
E1  volume share sum(D)/sum(S) by country x window x threshold, auction-wide
E2  same, tenor level (UG, KE only)
E3  share of auction-wide misses with B >= O (frequency) alongside E1 (volume)
E4  face-value-weighted maturity shift of accepted vs offered mix among
    auctions that met the overall offer (UG, KE)
Offer versions: 'result' (published with results; widest coverage) and
'announced' (pre-close notice; matched subset, primary where available).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import Paths
from .measures import near_threshold_mixed, outcome_class, shortfall_parts, volume_share

WINDOWS = {
    "common_2023-01-13_2026-10-30": ("2023-01-13", "2026-10-30"),
    "recent_2025-01-01_2026-10-30": ("2025-01-01", "2026-10-30"),
    "full": ("1900-01-01", "2100-01-01"),
}
THRESHOLDS = (0.0, 0.05, 0.10)
BLOCKS = (4, 8, 13)  # events per block (~1, 2, 3 months of weekly auctions)
N_BOOT = 2000


# ------------------------------------------------------------------ data loading
def load_panel(paths: Paths) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = paths.root / "data" / "derived"
    ev = pd.read_csv(d / "auction_events.csv")
    out = pd.read_csv(d / "auction_outcomes.csv", dtype={"tenor": str})
    off = pd.read_csv(d / "offer_versions.csv", dtype={"tenor": str}) if (d / "offer_versions.csv").stat().st_size > 5 else pd.DataFrame()
    return ev, out, off


def announced_offer(off: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """Latest pre-close offer version for each event x tenor.

    A version dated after the auction date is never 'announced'. An invitation without a printed
    date is still a pre-close document (it invites bids for that auction), so it is kept for
    *measurement*; its ``first_public_date`` stays empty and the forecasting stage therefore never
    treats it as known at a forecast origin.
    """
    if off.empty:
        return pd.DataFrame(columns=["event_id", "tenor", "O_announced", "announced_version", "announced_url",
                                     "n_distinct_versions", "first_public_date", "scope_status"])
    m = off.merge(ev[["event_id", "held_date"]], on="event_id", how="inner")
    m = m[m.first_public_date.isna() | (m.first_public_date <= m.held_date)]
    m = m.assign(_d=m.first_public_date.fillna("0000")).sort_values(["event_id", "tenor", "_d", "version"]).drop(columns="_d")
    last = m.groupby(["event_id", "tenor"]).tail(1)
    n_versions = m.groupby(["event_id", "tenor"]).O_announced.nunique().rename("n_distinct_versions")
    last = last.merge(n_versions.reset_index(), on=["event_id", "tenor"])
    last["scope_status"] = "not applicable"
    if "target_tenors" in last and "target_tenors" in ev:
        result_scope = last.event_id.map(ev.set_index("event_id").target_tenors)
        gh = last.event_id.str.startswith("GH-")
        last.loc[gh, "scope_status"] = np.select(
            [last.target_tenors.isna(), last.target_tenors.eq(result_scope)],
            ["scope unavailable", "same scope"], default="scope mismatch")[gh]
    return last.rename(columns={"version": "announced_version", "source_url": "announced_url"})[
        ["event_id", "tenor", "O_announced", "announced_version", "announced_url", "n_distinct_versions",
         "first_public_date", "scope_status"]]


def tenor_panel(paths: Paths) -> pd.DataFrame:
    ev, out, off = load_panel(paths)
    t = out[out.country.isin(["UG", "KE"])].copy()
    t["tenor_days"] = t.tenor.astype(int)
    t = t.merge(ev[["event_id", "held_date", "release_date", "available_from"]].rename(columns={"held_date": "ev_held"}),
                on="event_id", how="left")
    t["held_date"] = t.ev_held.fillna(t.held_date)
    t = t.drop(columns="ev_held")
    ann = announced_offer(off, ev)
    t = t.merge(ann, on=["event_id", "tenor"], how="left")
    t["ocr"] = t.method.fillna("").str.startswith("ocr")
    t["conflict"] = t.conflict.fillna(False).astype(bool)
    return t


def event_panel(paths: Paths) -> pd.DataFrame:
    """Auction-wide rows for all three countries: totals summed from tenor rows (UG, KE) or reported (GH)."""
    ev, out, off = load_panel(paths)
    t = tenor_panel(paths)
    full = t.groupby("event_id").tenor.nunique()
    t = t[t.event_id.isin(full[full == 3].index)]  # auction-wide needs every tenor (otherwise undefined)
    agg = t.groupby(["country", "event_id"]).agg(
        held_date=("held_date", "first"), O_result=("O_result", "sum"), B=("B", "sum"), A=("A", "sum"),
        O_announced=("O_announced", lambda s: s.sum() if s.notna().all() else np.nan),
        first_public_date=("first_public_date", lambda s: s.astype(str).max() if s.notna().all() else np.nan),
        ocr=("ocr", "max"), conflict=("conflict", "max")).reset_index()
    gh = out[(out.country == "GH") & (out.tenor == "total")].copy()
    gh = gh.merge(ev[["event_id", "held_date"]].rename(columns={"held_date": "h"}), on="event_id", how="left")
    gh["held_date"] = gh.h.fillna(gh.held_date)
    ann = announced_offer(off[off.country == "GH"] if not off.empty else off, ev)
    if not ann.empty:
        ann.loc[ann.scope_status != "same scope", "O_announced"] = np.nan
    gh = gh.merge(ann[["event_id", "O_announced", "first_public_date"]], on="event_id", how="left")
    gh["ocr"] = gh.method.fillna("").str.startswith("ocr")
    gh["conflict"] = gh.conflict.fillna(False).astype(bool)
    agg = pd.concat([agg, gh[["country", "event_id", "held_date", "O_result", "B", "A", "O_announced",
                              "first_public_date", "ocr", "conflict"]]], ignore_index=True)
    return agg.sort_values(["country", "held_date"]).reset_index(drop=True)


def with_offer(df: pd.DataFrame, version: str) -> pd.DataFrame:
    x = df.copy()
    if version == "result":
        x["O"] = x.O_result
    elif version == "announced":
        x = x[x.O_announced.notna()].copy()
        x["O"] = x.O_announced
    else:
        raise ValueError(version)
    x = x[(x.O > 0) & x.B.notna() & x.A.notna() & ~x.conflict]
    return x


def window(df: pd.DataFrame, name: str) -> pd.DataFrame:
    lo, hi = WINDOWS[name]
    return df[(df.held_date >= lo) & (df.held_date <= hi)]


# ------------------------------------------------------------------ uncertainty
def block_bootstrap_share(dfe: pd.DataFrame, block: int, n_boot: int, rng: np.random.Generator,
                          tol: float = 0.0) -> tuple[float, float]:
    """Moving-block bootstrap over time-ordered events (rows for one event stay together).

    ``dfe`` must have one row per event with columns D_ev, S_ev (already thresholded).
    """
    s = dfe.sort_values("held_date")
    D, S = s.D_ev.to_numpy(), s.S_ev.to_numpy()
    n = len(s)
    if n == 0 or S.sum() <= 0:
        return np.nan, np.nan
    b = min(block, n)
    starts = np.arange(n - b + 1)
    k = int(np.ceil(n / b))
    vals = np.empty(n_boot)
    for i in range(n_boot):
        idx = (rng.choice(starts, size=k)[:, None] + np.arange(b)[None, :]).ravel()[:n]
        ss = S[idx].sum()
        vals[i] = D[idx].sum() / ss if ss > 0 else np.nan
    vals = vals[np.isfinite(vals)]
    if len(vals) < 0.5 * n_boot:
        return np.nan, np.nan
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


# ------------------------------------------------------------------ decomposition
def decompose(df: pd.DataFrame, tol: float, keys: list[str], rng, level: str) -> dict:
    """Return summary dict for one population. ``df`` has O, B, A per row; rows grouped to events by event_id."""
    O, B, A = df.O.to_numpy(float), df.B.to_numpy(float), df.A.to_numpy(float)
    S, D, R = shortfall_parts(O, B, A)
    miss = A < (1 - tol) * O
    cls_policy = outcome_class(O, B, A, tol, "policy")
    cls_pilot = outcome_class(O, B, A, tol, "pilot")
    x = df.assign(S=S, D=D, R=R, miss=miss)
    xm = x[x.miss]
    res = dict(level=level, tol=tol, n_rows=len(df), n_events=df.event_id.nunique(),
               first=df.held_date.min(), last=df.held_date.max(),
               n_miss=int(miss.sum()), n_miss_B_ge_O=int((miss & (B >= O)).sum()),
               n_miss_B_lt_O=int((miss & (B < O)).sum()),
               n_class2_pilot_convention=int((cls_pilot == 2).sum()),
               n_class2_policy_convention=int((cls_policy == 2).sum()),
               n_near_threshold_mixed=int(near_threshold_mixed(O, B, A, tol).sum()),
               sum_S=float(xm.S.sum()), sum_D=float(xm.D.sum()), sum_R=float(xm.R.sum()),
               volume_share_D=volume_share(xm.D, xm.S))
    # event-level aggregation of material-miss D and S for bootstrap (tenor rows of one event stay together)
    e = x.assign(D_ev=np.where(x.miss, x.D, 0.0), S_ev=np.where(x.miss, x.S, 0.0)).groupby("event_id").agg(
        held_date=("held_date", "first"), D_ev=("D_ev", "sum"), S_ev=("S_ev", "sum")).reset_index()
    for b in BLOCKS:
        lo, hi = block_bootstrap_share(e, b, N_BOOT, rng)
        res[f"ci95_lo_b{b}"], res[f"ci95_hi_b{b}"] = lo, hi
    # with no volume-driven shortfall at all, report the share of events that would have to be
    # volume-driven to reach 10% of observed shortfall volume
    return res


def run_decomposition(paths: Paths, seed: int = 20261106) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    evp = event_panel(paths)
    tp = tenor_panel(paths)
    rows = []
    for version in ("result", "announced"):
        e_v = with_offer(evp, version)
        t_v = with_offer(tp, version)
        for wname in WINDOWS:
            for country in ("UG", "KE", "GH"):
                for tol in THRESHOLDS:
                    pop = window(e_v[e_v.country == country], wname)
                    if len(pop):
                        rows.append(dict(country=country, offer_version=version, window=wname,
                                         **decompose(pop, tol, [], rng, "auction_wide")))
                    if country != "GH":
                        tpop = window(t_v[t_v.country == country], wname)
                        if len(tpop):
                            rows.append(dict(country=country, offer_version=version, window=wname,
                                             **decompose(tpop, tol, [], rng, "tenor")))
    res = pd.DataFrame(rows)
    res.to_csv(paths.tables / "T1_decomposition.csv", index=False)
    return res


def masking_table(paths: Paths) -> pd.DataFrame:
    """Auctions where the overall offer was met but at least one maturity was missed."""
    tp = with_offer(tenor_panel(paths), "result")
    full = tp.groupby("event_id").tenor.nunique()
    tp = tp[tp.event_id.isin(full[full == 3].index)]
    rows = []
    for (c, wname), _ in pd.MultiIndex.from_product([["UG", "KE"], list(WINDOWS)]).to_frame().groupby(level=[0, 1]):
        x = window(tp[tp.country == c], wname)
        if x.empty:
            continue
        g = x.groupby("event_id")
        agg = g[["O", "B", "A"]].sum()
        tmiss = g.apply(lambda z: int((z.A < z.O).sum()), include_groups=False)
        tvol = g.apply(lambda z: float(np.maximum(z.O - z.A, 0).sum()), include_groups=False)
        met = agg.A >= agg.O
        rows.append(dict(country=c, window=wname, n_events=len(agg), n_overall_met=int(met.sum()),
                         n_met_with_tenor_miss=int((met & (tmiss > 0)).sum()),
                         share_met_with_tenor_miss=float((met & (tmiss > 0)).sum() / max(met.sum(), 1)),
                         tenor_shortfall_hidden_native=float(tvol[met].sum()),
                         unit="UGX_bn" if c == "UG" else "KES_m"))
    out = pd.DataFrame(rows)
    out.to_csv(paths.tables / "T3_masking.csv", index=False)
    return out


# ------------------------------------------------------------------ maturity
def maturity_table(paths: Paths, version: str = "result") -> tuple[pd.DataFrame, pd.DataFrame]:
    tp = with_offer(tenor_panel(paths), version)
    full = tp.groupby("event_id").tenor.nunique()
    tp = tp[tp.event_id.isin(full[full == 3].index)].copy()
    tp["days_actual"] = tp.days_to_maturity.where(tp.days_to_maturity.between(80, 380))
    rows = []
    for eid, g in tp.groupby("event_id"):
        O, A = g.O.to_numpy(float), g.A.to_numpy(float)
        nom = g.tenor_days.to_numpy(float)
        act = g.days_actual.to_numpy(float)
        rec = dict(country=g.country.iloc[0], event_id=eid, held_date=g.held_date.iloc[0], O_tot=O.sum(), B_tot=g.B.sum(),
                   A_tot=A.sum(), met=bool(A.sum() >= O.sum()))
        if O.sum() > 0 and A.sum() > 0:
            rec["mat_offered"] = float((O * nom).sum() / O.sum())
            rec["mat_accepted"] = float((A * nom).sum() / A.sum())
            rec["shift_nominal"] = rec["mat_accepted"] - rec["mat_offered"]
            if np.isfinite(act).all():
                rec["shift_actual"] = float((A * act).sum() / A.sum() - (O * act).sum() / O.sum())
            rec["share364_shift"] = float(A[nom == 364].sum() / A.sum() - O[nom == 364].sum() / O.sum())
        rows.append(rec)
    ev = pd.DataFrame(rows)
    if version == "result":
        ev.to_csv(paths.tables / "maturity_events.csv", index=False)
    summ = []
    for wname in WINDOWS:
        for c in ("UG", "KE"):
            for subset in ("met", "all"):
                x = window(ev[ev.country == c], wname)
                if subset == "met":
                    x = x[x.met]
                x = x[x.shift_nominal.notna()]
                if x.empty:
                    continue
                q = x.shift_nominal.quantile([0.25, 0.5, 0.75])
                summ.append(dict(country=c, window=wname, subset=subset, n=len(x), median=q[0.5], q1=q[0.25], q3=q[0.75],
                                 mean=x.shift_nominal.mean(), n_longer_30=int((x.shift_nominal >= 30).sum()),
                                 n_shorter_30=int((x.shift_nominal <= -30).sum()),
                                 share_abs_ge_30=float((x.shift_nominal.abs() >= 30).mean()),
                                 median_actual_days=x.shift_actual.median() if "shift_actual" in x else np.nan,
                                 n_actual=int(x.shift_actual.notna().sum()) if "shift_actual" in x else 0,
                                 median_share364_shift=x.share364_shift.median()))
    s = pd.DataFrame(summ)
    if version == "result":
        s.to_csv(paths.tables / "T4_maturity_shift.csv", index=False)
        by_year = ev[ev.met & ev.shift_nominal.notna()].assign(year=lambda z: z.held_date.str[:4]).groupby(
            ["country", "year"]).shift_nominal.agg(["size", "median", "mean"]).reset_index()
        by_year.to_csv(paths.tables / "T4b_maturity_shift_by_year.csv", index=False)
    else:
        s.to_csv(paths.tables / "T4c_maturity_shift_announced.csv", index=False)
    return ev, s


# ------------------------------------------------------------------ robustness
def robustness(paths: Paths, seed: int = 20261106) -> pd.DataFrame:
    from .audit import offer_reconciliation

    rng = np.random.default_rng(seed + 1)
    evp = with_offer(event_panel(paths), "result")
    tp = with_offer(tenor_panel(paths), "result")
    specs = []
    base = window(evp, "common_2023-01-13_2026-10-30")
    tb = window(tp, "common_2023-01-13_2026-10-30")
    specs.append(("baseline", base, tb))
    specs.append(("exclude_ocr_rows", base[~base.ocr], tb[~tb.ocr]))
    matched_e = base[base.O_announced.notna()]
    specs.append(("matched_invitation_result_offer", matched_e, tb[tb.O_announced.notna()]))
    rec = offer_reconciliation(paths, write=False)
    mism = set(rec.loc[rec.status.isin(["numeric mismatch", "scope mismatch"]), "event_id"]) if not rec.empty else set()
    specs.append(("exclude_offer_mismatch_events", base[~base.event_id.isin(mism)], tb[~tb.event_id.isin(mism)]))
    for y in sorted(set(base.held_date.str[:4])):
        specs.append((f"leave_out_{y}", base[base.held_date.str[:4] != y], tb[tb.held_date.str[:4] != y]))
    rows = []
    for name, e, t in specs:
        for c in ("UG", "KE", "GH"):
            for tol in THRESHOLDS:
                pe = e[e.country == c]
                if len(pe):
                    d = decompose(pe, tol, [], rng, "auction_wide")
                    rows.append(dict(spec=name, country=c, tol=tol, level="auction_wide", n_events=d["n_events"],
                                     n_miss=d["n_miss"], n_miss_B_ge_O=d["n_miss_B_ge_O"], share=d["volume_share_D"]))
                pt = t[t.country == c]
                if c != "GH" and len(pt):
                    d = decompose(pt, tol, [], rng, "tenor")
                    rows.append(dict(spec=name, country=c, tol=tol, level="tenor", n_events=d["n_events"],
                                     n_miss=d["n_miss"], n_miss_B_ge_O=d["n_miss_B_ge_O"], share=d["volume_share_D"]))
    out = pd.DataFrame(rows)
    out.to_csv(paths.tables / "T5_robustness.csv", index=False)
    by_year = []
    for (c, y), g in evp.assign(year=evp.held_date.str[:4]).groupby(["country", "year"]):
        S, D, R = shortfall_parts(g.O, g.B, g.A)
        m = g.A < g.O
        by_year.append(dict(country=c, year=y, n_events=len(g), n_miss=int(m.sum()), n_miss_B_ge_O=int((m & (g.B >= g.O)).sum()),
                            share=volume_share(D[m.to_numpy()], S[m.to_numpy()])))
    pd.DataFrame(by_year).to_csv(paths.tables / "T2_decomposition_by_year.csv", index=False)
    return out


def missingness_bound(paths: Paths) -> pd.DataFrame:
    """Report typical-size and zero-bid invitation scenarios for missing auctions."""
    evp = window(with_offer(event_panel(paths), "result"), "common_2023-01-13_2026-10-30")
    rows = []
    for c in ("UG", "KE", "GH"):
        x = evp[evp.country == c]
        S, D, R = shortfall_parts(x.O, x.B, x.A)
        sS, sD = S.sum(), D.sum()
        med_O = x.O.median()
        # Illustrative scenario using the same country's median offer and miss depth.
        miss = x.A < x.O
        depth = float(np.median((S / x.O.to_numpy())[miss.to_numpy()])) if miss.any() else np.nan
        add = med_O * depth if np.isfinite(depth) else np.nan
        need = (sS - 2 * sD) / add if add and add > 0 and sD / sS < 0.5 else 0.0
        rows.append(dict(country=c, n_events=len(x), sum_S=sS, sum_D=sD, share=sD / sS if sS else np.nan,
                         median_offer=med_O, median_miss_depth=depth,
                         hypothetical_missing_fully_volume_driven_events_to_reach_50pct=need))
    out = pd.DataFrame(rows)
    ev, _, off = load_panel(paths)
    if not off.empty and "auction_date" in off:
        lo, hi = WINDOWS["common_2023-01-13_2026-10-30"]
        inv = off[(off.country == "UG") & ~off.event_id.isin(ev.event_id)].copy()
        inv["scheduled"] = inv.auction_date.fillna(inv.source_url.str.extract(
            r"scheduled_for_(\d{1,2}_[a-zA-Z]+_\d{4})", expand=False).map(
                lambda s: pd.to_datetime(s.replace("_", " "), format="mixed").date().isoformat()
                if pd.notna(s) else None))
        observed_dates = ev.loc[ev.country == "UG", "held_date"]
        inv = inv[inv.scheduled.between(lo, hi) & ~inv.scheduled.isin(observed_dates)]
        inv = inv.sort_values("version").drop_duplicates(["event_id", "tenor"], keep="last")
        complete = inv.groupby("event_id").filter(lambda g: set(g.tenor) == {"91", "182", "364"})
        missing_offer = complete.O_announced.sum()
        ug = out.country == "UG"
        out.loc[ug, "missing_invitation_count"] = complete.event_id.nunique()
        out.loc[ug, "missing_invitation_offer"] = missing_offer
        out.loc[ug, "zero_bids_at_invitation_targets_share"] = (
            (out.loc[ug, "sum_D"] + missing_offer) / (out.loc[ug, "sum_S"] + missing_offer))
    out.to_csv(paths.tables / "T6_missingness_bound.csv", index=False)
    return out


def run_measure(paths: Paths, offer_version: str = "announced_or_result", seed: int = 20261106) -> None:
    from .figures import make_figures

    dec = run_decomposition(paths, seed)
    mask = masking_table(paths)
    mev, mat = maturity_table(paths)
    maturity_table(paths, "announced")
    robustness(paths, seed)
    missingness_bound(paths)
    make_figures(paths)
    key = dec[(dec.window == "common_2023-01-13_2026-10-30") & (dec.tol == 0) & (dec.offer_version == "result")]
    print(key[["country", "level", "n_events", "n_miss", "n_miss_B_ge_O", "volume_share_D", "ci95_lo_b8",
               "ci95_hi_b8"]].to_string(index=False))
    print(mat[(mat.subset == "met")].to_string(index=False))
    print(mask.to_string(index=False))
    (paths.reports / "measure_meta.json").write_text(json.dumps({"seed": seed, "n_boot": N_BOOT, "blocks": BLOCKS,
                                                                 "windows": WINDOWS, "thresholds": THRESHOLDS},
                                                                indent=1), encoding="utf-8")
