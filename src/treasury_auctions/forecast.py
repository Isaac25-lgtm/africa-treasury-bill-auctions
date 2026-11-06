"""Secondary predictive aim: pre-close warnings about auction execution (handoff Section 8).

Pre-registered design (docs/protocol.md, frozen before any evaluation was run):

* Forecast origin: close of the business day before the bid/held date (native calendar).
* A past result is eligible only if ``available_from`` (next business day after its date-only
  release proxy) is on or before the origin. Announced offers are eligible only if first public
  on or before the origin. Same-auction B, A, cut-offs, yields and redemptions are never features.
* Walk-forward monthly refits; train on rows whose labels were available before the month start.
* Periods: development 2020-01..2022-12 (baseline/model selection), locked holdout 2023-01..2024-12
  (never evaluated by the pilot), replication 2025-01..2026-10 (inspected by the pilot; exploratory).
* Targets: 3-class (0 met, 1 missed with B<O, 2 missed with B>=O) at exact threshold, tenor level
  (UG, KE) and auction-wide (UG, KE, GH); binary any-miss derived from the same probabilities.
* Log loss clipped at 1e-6. Paired moving-block bootstrap over time-ordered auctions.
* Smallest useful gain (provisional, set before the holdout was opened): improvement >= 0.02 nats per
  row over the strongest development baseline with a 95% interval excluding zero, AND captured
  shortfall volume under a fixed 25% alert budget not lower than the baseline's.
"""

from __future__ import annotations

import json
import warnings
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import Paths
from .measures import outcome_class

warnings.filterwarnings("ignore", category=UserWarning)
CLIP = 1e-6
PERIODS = {"development": ("2020-01-01", "2022-12-31"), "holdout": ("2023-01-01", "2024-12-31"),
           "replication": ("2025-01-01", "2026-10-31")}
ALERT_BUDGET = 0.25
MIN_TRAIN = 40
HIST_FEATS = ["cov_last", "fill_last", "acc_last", "cov_med6", "fill_med6", "acc_med6", "miss_rate12",
              "c1_rate12", "c2_rate12", "prev_class1", "prev_class2", "days_since_last", "n_hist"]
OFFER_FEATS = ["log_offer", "offer_share", "offer_change_vs_last"]
CAL_FEATS = ["month_sin", "month_cos", "quarter_end"]


def prev_business_day(d: str) -> str:
    x = date.fromisoformat(d) - timedelta(days=1)
    while x.weekday() >= 5:
        x -= timedelta(days=1)
    return x.isoformat()


# ----------------------------------------------------------------- data assembly
def build_rows(paths: Paths, strict: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    from .analysis import event_panel, tenor_panel

    tp = tenor_panel(paths)
    tp = tp[(tp.O_result > 0) & tp.B.notna() & tp.A.notna() & ~tp.conflict].copy()
    tp["series"] = tp.country + "-" + tp.tenor.astype(str)
    ep = event_panel(paths)
    ep = ep[(ep.O_result > 0) & ep.B.notna() & ep.A.notna() & ~ep.conflict].copy()
    ev = pd.read_csv(paths.root / "data" / "derived" / "auction_events.csv")
    ep = ep.merge(ev[["event_id", "available_from", "release_date"]], on="event_id", how="left")
    ep["series"] = ep.country + "-total"
    ep["tenor"] = "total"
    return _features(tp, strict), _features(ep, strict)


def _features(df: pd.DataFrame, strict: bool) -> pd.DataFrame:
    df = df.sort_values(["series", "held_date"]).reset_index(drop=True)
    df["origin"] = df.held_date.map(prev_business_day) if strict else df.held_date
    df["label"] = outcome_class(df.O_result, df.B, df.A, 0.0)
    df["S"] = np.maximum(df.O_result - df.A, 0)
    df["cov"] = df.B / df.O_result
    df["fill"] = df.A / df.O_result
    df["acc"] = np.where(df.B > 0, df.A / df.B.where(df.B > 0), np.nan)
    avail = df.available_from if strict else df.release_date
    df["label_available"] = avail.fillna(df.held_date)
    feats = []
    for _, g in df.groupby("series", sort=False):
        g = g.reset_index()
        for i in range(len(g)):
            o = g.origin[i]
            h = g[(g.label_available <= o) if strict else (g.label_available < o)]
            h = h[h.held_date < g.held_date[i]]
            r = dict(index=g["index"][i], n_hist=len(h))
            if len(h):
                last = h.iloc[-1]
                r.update(cov_last=last["cov"], fill_last=last["fill"], acc_last=last["acc"],
                         cov_med6=h["cov"].tail(6).median(), fill_med6=h["fill"].tail(6).median(),
                         acc_med6=h["acc"].tail(6).median(), miss_rate12=(h.label.tail(12) > 0).mean(),
                         c1_rate12=(h.label.tail(12) == 1).mean(), c2_rate12=(h.label.tail(12) == 2).mean(),
                         prev_class=int(last.label), prev_class1=float(last.label == 1),
                         prev_class2=float(last.label == 2),
                         days_since_last=(pd.Timestamp(g.held_date[i]) - pd.Timestamp(last.held_date)).days,
                         last_offer=last.O_result)
            feats.append(r)
    f = pd.DataFrame(feats).set_index("index")
    df = df.join(f)
    # current-offer features use only the announced (pre-close) version known by the origin
    ann_ok = df.O_announced.notna() & (df.first_public_date.fillna("9999") <= df.origin)
    df["O_known"] = np.where(ann_ok, df.O_announced, np.nan)
    df["log_offer"] = np.log(df.O_known)
    tot = df.groupby("event_id").O_known.transform(lambda s: s.sum(min_count=1) if s.notna().all() else np.nan)
    df["offer_share"] = np.where(df.tenor.astype(str) == "total", 1.0, df.O_known / tot)
    df["offer_change_vs_last"] = np.log(df.O_known / df.last_offer)
    m = pd.to_datetime(df.held_date).dt.month
    df["month_sin"], df["month_cos"] = np.sin((m - 1) * np.pi / 6), np.cos((m - 1) * np.pi / 6)
    df["quarter_end"] = m.isin([3, 6, 9, 12]).astype(float)
    df["offer_known"] = ann_ok
    return df


# ----------------------------------------------------------------- models
def _freq(labels, alpha=1.0):
    c = np.bincount(np.asarray(labels, dtype=int), minlength=3).astype(float) + alpha
    return c / c.sum()


def baselines(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, np.ndarray]:
    out = {k: np.zeros((len(test), 3)) for k in ("base_unconditional", "base_recent12", "base_transition",
                                                    "base_blend")}
    for j, (_, r) in enumerate(test.iterrows()):
        h = train[(train.series == r.series)]
        h = h[h.label_available <= r.origin] if "origin" in r else h
        out["base_unconditional"][j] = _freq(h.label)
        out["base_recent12"][j] = _freq(h.label.tail(12))
        if len(h) > 1 and pd.notna(r.get("prev_class")):
            prev = h.label.shift(1)
            nxt = h.label[prev == r.prev_class]
            out["base_transition"][j] = _freq(nxt)
        else:
            out["base_transition"][j] = _freq(h.label)
        out["base_blend"][j] = (out["base_recent12"][j] + out["base_transition"][j]) / 2
    return out


def _clf(kind: str, seed: int):
    if kind == "logit":
        return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                             LogisticRegression(C=0.5, max_iter=2000))
    return make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                         HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150,
                                                        l2_regularization=1.0, min_samples_leaf=20,
                                                        random_state=seed))


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, feats: list[str], kind: str, seed: int) -> np.ndarray | None:
    y = train.label.to_numpy()
    if len(train) < MIN_TRAIN or len(np.unique(y)) < 2:
        return None
    X = train[feats].astype(float)
    m = _clf(kind, seed).fit(X, y)
    pp = m.predict_proba(test[feats].astype(float))
    res = np.full((len(test), 3), CLIP)
    res[:, m.classes_.astype(int)] = pp  # absent classes keep an explicit (clipped) probability
    return res / res.sum(axis=1, keepdims=True)


def recalibrate(train_logp: np.ndarray, train_y: np.ndarray, test_logp: np.ndarray) -> np.ndarray | None:
    if len(train_y) < MIN_TRAIN or len(np.unique(train_y)) < 2:
        return None
    m = LogisticRegression(C=1.0, max_iter=2000).fit(train_logp, train_y)
    pp = m.predict_proba(test_logp)
    res = np.full((len(test_logp), 3), CLIP)
    res[:, m.classes_.astype(int)] = pp
    return res / res.sum(axis=1, keepdims=True)


def walk_forward(rows: pd.DataFrame, level: str, seed: int) -> pd.DataFrame:
    """Return long table: one row per (test row, model) with class probabilities."""
    months = pd.date_range("2020-01-01", "2026-10-01", freq="MS")
    full = HIST_FEATS + OFFER_FEATS + CAL_FEATS
    preds = []
    for ms in months:
        start, end = ms.date().isoformat(), (ms + pd.offsets.MonthBegin(1)).date().isoformat()
        test_all = rows[(rows.held_date >= start) & (rows.held_date < end)]
        if test_all.empty:
            continue
        train_all = rows[rows.label_available < start]  # labels public before the month starts
        for c, test in test_all.groupby("country"):
            train = train_all[train_all.country == c]
            other = train_all[train_all.country != c]
            cand = {}
            cand.update(baselines(train, test))
            cand["logit_history"] = fit_predict(train, test, HIST_FEATS, "logit", seed)
            cand["logit_full"] = fit_predict(train, test, full, "logit", seed)
            cand["hgb_full"] = fit_predict(train, test, full, "hgb", seed)
            pooled_feats = full + ["is_UG", "is_KE", "is_GH"]
            tr = train_all.assign(is_UG=(train_all.country == "UG") * 1.0, is_KE=(train_all.country == "KE") * 1.0,
                                  is_GH=(train_all.country == "GH") * 1.0)
            te = test.assign(is_UG=(test.country == "UG") * 1.0, is_KE=(test.country == "KE") * 1.0,
                             is_GH=(test.country == "GH") * 1.0)
            if level == "tenor":
                tr = tr[tr.country.isin(["UG", "KE"])]
            cand["pooled_logit"] = fit_predict(tr, te, pooled_feats, "logit", seed)
            if level == "tenor":
                other = other[other.country.isin(["UG", "KE"])]
            cand["transfer_zero_shot"] = fit_predict(other, test, HIST_FEATS, "logit", seed)
            if cand["transfer_zero_shot"] is not None and len(train) >= MIN_TRAIN:
                tz_train = fit_predict(other, train, HIST_FEATS, "logit", seed)
                cand["transfer_recalibrated"] = (recalibrate(np.log(tz_train), train.label.to_numpy(),
                                                             np.log(cand["transfer_zero_shot"]))
                                                 if tz_train is not None else None)
            for name, p in cand.items():
                if p is None:
                    continue
                df = test[["country", "event_id", "series", "tenor", "held_date", "origin", "label", "S", "O_result",
                           "offer_known"]].copy()
                df["model"] = name
                df["fold"] = start
                df["train_rows"] = len(train)
                df[["p0", "p1", "p2"]] = p
                preds.append(df)
    out = pd.concat(preds, ignore_index=True)
    out["level"] = level
    return out


# ----------------------------------------------------------------- metrics
def row_logloss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(p[np.arange(len(y)), y], CLIP, 1))


def brier_multi(p, y):
    oh = np.eye(3)[y]
    return ((p - oh) ** 2).sum(axis=1)


def period_of(d: str) -> str | None:
    for k, (lo, hi) in PERIODS.items():
        if lo <= d <= hi:
            return k
    return None


def paired_block_ci(diff_by_event: pd.Series, block: int, n_boot: int, rng) -> tuple[float, float]:
    v = diff_by_event.to_numpy()
    n = len(v)
    if n < 5:
        return np.nan, np.nan
    b = min(block, n)
    starts = np.arange(n - b + 1)
    k = int(np.ceil(n / b))
    stats = np.empty(n_boot)
    for i in range(n_boot):
        idx = (rng.choice(starts, size=k)[:, None] + np.arange(b)[None, :]).ravel()[:n]
        stats[i] = v[idx].mean()
    return float(np.quantile(stats, 0.025)), float(np.quantile(stats, 0.975))


def score(preds: pd.DataFrame, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    preds = preds.copy()
    preds["period"] = preds.held_date.map(period_of)
    preds = preds[preds.period.notna()]
    P = preds[["p0", "p1", "p2"]].to_numpy()
    y = preds.label.to_numpy().astype(int)
    preds["logloss"] = row_logloss(P, y)
    preds["brier"] = brier_multi(P, y)
    preds["p_miss"] = 1 - preds.p0
    preds["brier_miss"] = (preds.p_miss - (y > 0)) ** 2
    # common support: compare models on rows every model predicted
    key = ["level", "country", "period"]
    rows, comps = [], []
    for k, g in preds.groupby(key):
        counts = g.groupby("model").size()
        ids = set.intersection(*[set(zip(x.event_id, x.tenor.astype(str))) for _, x in g.groupby("model")])
        g = g[[(e, str(t)) in ids for e, t in zip(g.event_id, g.tenor)]]
        for m, x in g.groupby("model"):
            from sklearn.metrics import roc_auc_score

            yy = (x.label > 0).astype(int)
            auc = roc_auc_score(yy, x.p_miss) if yy.nunique() == 2 else np.nan
            rows.append(dict(zip(key, k), model=m, n_rows=len(x), n_events=x.event_id.nunique(),
                             n_class0=int((x.label == 0).sum()), n_class1=int((x.label == 1).sum()),
                             n_class2=int((x.label == 2).sum()), logloss=x.logloss.mean(), brier=x.brier.mean(),
                             brier_miss=x.brier_miss.mean(), auc_miss=auc, models_with_full_support=int(len(counts))))
    sc = pd.DataFrame(rows)
    # strongest baseline chosen on development log loss (per level x country)
    dev = sc[(sc.period == "development") & sc.model.str.startswith("base_")]
    best = dev.loc[dev.groupby(["level", "country"]).logloss.idxmin(), ["level", "country", "model"]].rename(
        columns={"model": "strongest_baseline"})
    sc = sc.merge(best, on=["level", "country"], how="left")
    for (lev, c, per), g in preds.groupby(["level", "country", "period"]):
        bname = best[(best.level == lev) & (best.country == c)].strongest_baseline
        if bname.empty:
            continue
        bname = bname.iloc[0]
        base = g[g.model == bname].set_index(["event_id", "tenor"])
        for m, x in g.groupby("model"):
            if m == bname:
                continue
            x = x.set_index(["event_id", "tenor"])
            j = x.join(base[["logloss", "held_date"]], rsuffix="_b", how="inner")
            if j.empty:
                continue
            d = (j.logloss - j.logloss_b).groupby(level=0).mean()
            order = j.groupby(level=0).held_date.first().sort_values().index
            d = d.loc[order]
            lo4, hi4 = paired_block_ci(d, 4, 2000, rng)
            lo8, hi8 = paired_block_ci(d, 8, 2000, rng)
            comps.append(dict(level=lev, country=c, period=per, model=m, baseline=bname, n_events=len(d),
                              mean_diff=float(d.mean()), ci95_lo_b4=lo4, ci95_hi_b4=hi4, ci95_lo_b8=lo8, ci95_hi_b8=hi8))
    cmp_ = pd.DataFrame(comps)
    # calibration (reliability) for any-miss probability, by level x country x period x model
    cal = preds.assign(bin=pd.cut(preds.p_miss, [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0], include_lowest=True))
    cal = cal.groupby(["level", "country", "period", "model", "bin"], observed=True).agg(
        n=("label", "size"), mean_p=("p_miss", "mean"), observed=("label", lambda s: (s > 0).mean())).reset_index()
    return sc, cmp_, cal


def alert_budget(preds: pd.DataFrame, budget: float = ALERT_BUDGET) -> pd.DataFrame:
    """Fixed alert budget with the probability threshold chosen from training-period predictions only.

    For each fold the threshold is the (1 - budget) quantile of the model's predicted P(miss) on rows
    from earlier folds of the same country/level (the model's own past predictions); folds without
    at least 20 earlier predictions use no alert.
    """
    preds = preds.copy()
    preds["period"] = preds.held_date.map(period_of)
    preds["p_miss"] = 1 - preds.p0
    rows = []
    for (lev, c, m), g in preds.groupby(["level", "country", "model"]):
        g = g.sort_values("held_date")
        alerts = np.zeros(len(g), dtype=bool)
        folds = g.fold.to_numpy()
        pm = g.p_miss.to_numpy()
        for f in np.unique(folds):
            past = pm[folds < f]
            if len(past) < 20:
                continue
            thr = np.quantile(past, 1 - budget)
            idx = folds == f
            alerts[idx] = pm[idx] >= thr
        g = g.assign(alert=alerts)
        for per, x in g.groupby("period"):
            if per is None:
                continue
            tot = x.S.sum()
            rows.append(dict(level=lev, country=c, model=m, period=per, n_rows=len(x), alert_rate=x.alert.mean(),
                             misses=int((x.label > 0).sum()), misses_alerted=int(((x.label > 0) & x.alert).sum()),
                             false_alerts=int(((x.label == 0) & x.alert).sum()),
                             shortfall_volume_captured_share=float(x.S[x.alert].sum() / tot) if tot > 0 else np.nan,
                             # retrospective ranking diagnostic (ex post; NOT a usable live threshold)
                             retro_top25_volume_share=_top_share(x, budget)))
    return pd.DataFrame(rows)


def _top_share(x: pd.DataFrame, budget: float) -> float:
    tot = x.S.sum()
    if tot <= 0 or len(x) == 0:
        return np.nan
    k = max(1, int(round(budget * len(x))))
    top = x.sort_values("p_miss", ascending=False, kind="mergesort").head(k)
    return float(top.S.sum() / tot)


# ----------------------------------------------------------------- maturity shift magnitude
def maturity_forecast(paths: Paths, seed: int, strict: bool = True) -> pd.DataFrame:
    tp, _ = build_rows(paths, strict)
    full = tp.groupby("event_id").tenor.nunique()
    tp = tp[tp.event_id.isin(full[full == 3].index)]
    e = tp.groupby(["country", "event_id"]).apply(lambda g: pd.Series(dict(
        held_date=g.held_date.iloc[0], origin=g.origin.iloc[0], label_available=g.label_available.max(),
        mshift=(g.A * g.tenor_days).sum() / g.A.sum() - (g.O_result * g.tenor_days).sum() / g.O_result.sum()
        if g.A.sum() > 0 else np.nan,
        ann_mat=(g.O_known * g.tenor_days).sum() / g.O_known.sum() if g.O_known.notna().all() else np.nan,
        ann_share364=g.loc[g.tenor_days == 364, "O_known"].sum() / g.O_known.sum() if g.O_known.notna().all() else np.nan,
    )), include_groups=False).reset_index()
    e = e[e.mshift.notna()].sort_values(["country", "held_date"]).reset_index(drop=True)
    rows = []
    for c, g in e.groupby("country"):
        g = g.reset_index(drop=True)
        for i in range(len(g)):
            h = g[(g.label_available <= g.origin[i]) & (g.held_date < g.held_date[i])]
            rows.append(dict(idx=g.index[i], country=c, prev=h["mshift"].iloc[-1] if len(h) else np.nan,
                             med6=h["mshift"].tail(6).median() if len(h) else np.nan,
                             med12=h["mshift"].tail(12).median() if len(h) else np.nan, nh=len(h)))
    f = pd.DataFrame(rows)
    e = pd.concat([e.reset_index(drop=True), f.drop(columns=["idx", "country"]).reset_index(drop=True)], axis=1)
    out = []
    feats = ["prev", "med6", "med12", "ann_mat", "ann_share364"]
    for ms in pd.date_range("2020-01-01", "2026-10-01", freq="MS"):
        start, end = ms.date().isoformat(), (ms + pd.offsets.MonthBegin(1)).date().isoformat()
        test = e[(e.held_date >= start) & (e.held_date < end)]
        for c, t in test.groupby("country"):
            tr = e[(e.country == c) & (e.label_available < start)]
            preds = {"no_shift": np.zeros(len(t)), "previous": t.prev.fillna(0).to_numpy(),
                     "rolling_median6": t.med6.fillna(0).to_numpy()}
            if len(tr) >= MIN_TRAIN:
                rid = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(),
                                    Ridge(alpha=10.0)).fit(tr[feats], tr["mshift"])
                preds["ridge"] = rid.predict(t[feats])
                hg = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                                   HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=150,
                                                                 min_samples_leaf=20, random_state=seed)).fit(tr[feats], tr["mshift"])
                preds["hgb"] = hg.predict(t[feats])
            for m, p in preds.items():
                out.append(pd.DataFrame(dict(country=c, event_id=t.event_id, held_date=t.held_date, model=m,
                                             actual=t["mshift"], pred=p, fold=start)))
    o = pd.concat(out, ignore_index=True)
    o["period"] = o.held_date.map(period_of)
    o["abs_err"] = (o.pred - o.actual).abs()
    s = o.dropna(subset=["period"]).groupby(["country", "period", "model"]).agg(
        n=("abs_err", "size"), mae=("abs_err", "mean"), p90_abs_err=("abs_err", lambda v: v.quantile(0.9))).reset_index()
    s.to_csv(paths.tables / "F4_maturity_forecast.csv", index=False)
    o.to_csv(paths.tables / "F4_maturity_predictions.csv", index=False)
    return s


def run_evaluate(paths: Paths, seed: int = 20261106, strict_timing: bool = True,
                 reuse_predictions: bool = False) -> None:
    tag = "strict" if strict_timing else "lenient"
    f0 = paths.tables / f"F0_predictions_{tag}.csv"
    if reuse_predictions and f0.is_file():
        preds = pd.read_csv(f0, dtype={"tenor": str})
        print(f"reusing {f0.name} ({len(preds)} rows)")
    else:
        tp, ep = build_rows(paths, strict_timing)
        tp.to_csv(paths.interim / f"features_tenor_{tag}.csv", index=False)
        ep.to_csv(paths.interim / f"features_auction_{tag}.csv", index=False)
        p_t = walk_forward(tp, "tenor", seed)
        p_e = walk_forward(ep, "auction", seed)
        preds = pd.concat([p_t, p_e], ignore_index=True)
        preds.to_csv(f0, index=False)
    sc, cmp_, cal = score(preds, seed)
    ab = alert_budget(preds)
    sc.to_csv(paths.tables / f"F1_scores_{tag}.csv", index=False)
    cmp_.to_csv(paths.tables / f"F2_paired_differences_{tag}.csv", index=False)
    cal.to_csv(paths.tables / f"F3_calibration_{tag}.csv", index=False)
    ab.to_csv(paths.tables / f"F5_alert_budget_{tag}.csv", index=False)
    mf = maturity_forecast(paths, seed, strict_timing)
    # Gate 4 decision on the locked holdout
    gate = []
    for per in ("holdout", "replication"):
        for (lev, c), g in cmp_[(cmp_.period == per) & ~cmp_.model.str.startswith("base_")].groupby(["level", "country"]):
            abm = ab[(ab.level == lev) & (ab.country == c) & (ab.period == per)].set_index("model")
            base_names = [m for m in abm.index if m.startswith("base_")]
            best_base_vol = abm.loc[base_names, "shortfall_volume_captured_share"].max() if base_names else np.nan
            for _, r in g.iterrows():
                vm = abm.shortfall_volume_captured_share.get(r.model, np.nan)
                vb = abm.shortfall_volume_captured_share.get(r.baseline, np.nan)
                ll_ok = bool((r.mean_diff <= -0.02) and (r.ci95_hi_b8 < 0))
                # pre-registered rule (volume vs the strongest development baseline)
                passes = ll_ok and bool(np.isfinite(vm) and np.isfinite(vb) and vm >= vb)
                # post-hoc stricter sensitivity (deviation log): volume vs the best of all four baselines
                passes_strict = ll_ok and bool(np.isfinite(vm) and np.isfinite(best_base_vol) and vm >= best_base_vol)
                gate.append(dict(period=per, level=lev, country=c, model=r.model, baseline=r.baseline,
                                 n_events=r.n_events, logloss_diff=r.mean_diff, ci95_lo_b8=r.ci95_lo_b8,
                                 ci95_hi_b8=r.ci95_hi_b8, logloss_criterion=ll_ok,
                                 alert_rate_model=abm.alert_rate.get(r.model, np.nan),
                                 alert_rate_baseline=abm.alert_rate.get(r.baseline, np.nan),
                                 volume_captured_model=vm, volume_captured_baseline=vb,
                                 volume_best_of_baselines=best_base_vol,
                                 retro_top25_model=abm.retro_top25_volume_share.get(r.model, np.nan),
                                 retro_top25_baseline=abm.retro_top25_volume_share.get(r.baseline, np.nan),
                                 passes_gate4=passes, passes_gate4_strict_volume=passes_strict))
    g = pd.DataFrame(gate)
    g.to_csv(paths.tables / f"F6_gate4_{tag}.csv", index=False)
    meta = dict(seed=seed, strict_timing=strict_timing, periods=PERIODS, clip=CLIP, alert_budget=ALERT_BUDGET,
                min_train=MIN_TRAIN, features=dict(history=HIST_FEATS, offer=OFFER_FEATS, calendar=CAL_FEATS),
                models=sorted(preds.model.unique()),
                hyperparameters=dict(logit="L2, C=0.5", hgb="depth 3, lr 0.05, 150 iter, l2 1.0, min leaf 20",
                                     ridge_alpha=10.0),
                gate4_any_pass_holdout=bool(g[g.period == "holdout"].passes_gate4.any()) if not g.empty else False)
    (paths.reports / f"forecast_meta_{tag}.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    view = sc[(sc.period == "holdout")][["level", "country", "model", "n_rows", "logloss", "brier_miss", "auc_miss",
                                           "strongest_baseline"]]
    print(view.to_string(index=False))
    print(g[["period", "level", "country", "model", "logloss_diff", "ci95_hi_b8", "alert_rate_model", "alert_rate_baseline",
             "volume_captured_model", "volume_captured_baseline", "volume_best_of_baselines", "passes_gate4",
             "passes_gate4_strict_volume"]].to_string(index=False) if not g.empty else "no gate rows")
    print(mf.to_string(index=False))
