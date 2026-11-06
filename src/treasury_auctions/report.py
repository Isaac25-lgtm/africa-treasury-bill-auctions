"""Programmatic verification of generated tables and the reproducibility record.

Checks (each recorded pass/fail in ``outputs/reports/verification.json``):
* decomposition identity sum_S = sum_D + sum_R and n_miss = n(B>=O) + n(B<O) in every T1 row
* volume shares in [0, 1] or undefined; no row pools currencies (one country per row)
* recomputing the headline T1 cells directly from ``data/derived`` reproduces the table
* every figure has its source CSV and the source rows trace to auction event ids present in the panel
* maturity table counts equal the number of eligible events
* derived files hashed; package/tool versions, git commit and command recorded
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import version

import numpy as np
import pandas as pd

from .config import SNAPSHOT_CUTOFF, Paths


def _sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git(paths: Paths, *args) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=paths.root, capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def verify(paths: Paths) -> dict:
    from .analysis import event_panel, window, with_offer
    from .measures import shortfall_parts, volume_share

    checks = {}
    t1 = pd.read_csv(paths.tables / "T1_decomposition.csv")
    checks["T1_identity_S_eq_D_plus_R"] = bool(np.allclose(t1.sum_S, t1.sum_D + t1.sum_R, atol=1e-6))
    checks["T1_counts_reconcile"] = bool((t1.n_miss == t1.n_miss_B_ge_O + t1.n_miss_B_lt_O).all())
    vs = t1.volume_share_D.dropna()
    checks["T1_shares_in_unit_interval"] = bool(((vs >= -1e-12) & (vs <= 1 + 1e-12)).all())
    checks["T1_undefined_when_no_shortfall"] = bool(t1[t1.sum_S == 0].volume_share_D.isna().all())
    # independent recomputation of the headline cells
    e = window(with_offer(event_panel(paths), "result"), "common_2023-01-13_2026-10-30")
    ok = True
    for c, g in e.groupby("country"):
        S, D, R = shortfall_parts(g.O, g.B, g.A)
        m = (g.A < g.O).to_numpy()
        share = volume_share(D[m], S[m])
        row = t1[(t1.country == c) & (t1.offer_version == "result") & (t1.window == "common_2023-01-13_2026-10-30")
                 & (t1.tol == 0) & (t1.level == "auction_wide")]
        if row.empty or int(row.n_events.iloc[0]) != len(g) or int(row.n_miss.iloc[0]) != int(m.sum()) or not (
                (np.isnan(share) and np.isnan(row.volume_share_D.iloc[0])) or abs(share - row.volume_share_D.iloc[0]) < 1e-12):
            ok = False
    checks["T1_headline_recomputed"] = ok
    ev = pd.read_csv(paths.root / "data" / "derived" / "auction_events.csv")
    ids = set(ev.event_id)
    for f in ("fig1_decomposition", "fig2_maturity_shift", "fig3_uganda_timeline"):
        checks[f"{f}_rendered"] = (paths.figures / f"{f}.png").is_file() and (paths.figures / f"{f}.pdf").is_file()
    src2 = pd.read_csv(paths.figures / "fig2_maturity_source.csv")
    src3 = pd.read_csv(paths.figures / "fig3_uganda_timeline_source.csv")
    checks["fig2_rows_trace_to_events"] = bool(src2.event_id.isin(ids).all())
    checks["fig3_rows_trace_to_events"] = bool(src3.event_id.isin(ids).all())
    checks["fig1_source_present"] = (paths.figures / "fig1_decomposition_source.csv").is_file()
    checks["readme_story_figures_rendered"] = len(list((paths.figures / "readme").glob("*.png"))) == 10
    mt = pd.read_csv(paths.tables / "T4_maturity_shift.csv")
    me = pd.read_csv(paths.tables / "maturity_events.csv")
    okm = True
    for _, r in mt.iterrows():
        x = window(me[me.country == r.country], r.window)
        x = x[x.met] if r.subset == "met" else x
        okm &= int(x.shift_nominal.notna().sum()) == int(r.n)
    checks["T4_counts_match_events"] = bool(okm)
    out = pd.read_csv(paths.root / "data" / "derived" / "auction_outcomes.csv", dtype={"tenor": str})
    checks["units_one_per_country"] = bool(out.groupby("country").unit.nunique().eq(1).all())
    checks["no_zero_filled_quantities"] = bool(not ((out.B == 0) & (out.A == 0) & out.O_result.isna()).any())
    eligible_gh = ev[(ev.country == "GH") & ~ev.conflict]
    gh_totals = out[(out.country == "GH") & out.tenor.eq("total") & ~out.conflict]
    gh_tenors = out[(out.country == "GH") & out.tenor.ne("total") & ~out.conflict]
    sums = gh_tenors.groupby("event_id")[["B", "A"]].sum(min_count=1)
    gh_totals = gh_totals.set_index("event_id")
    checks["GH_totals_cover_all_valid_events"] = bool(
        gh_totals.index.is_unique and set(gh_totals.index) == set(eligible_gh.event_id)
        and gh_totals[["O_result", "B", "A"]].notna().all().all()
        and np.allclose(gh_totals[["B", "A"]], sums.reindex(gh_totals.index)))
    reconciliation = pd.read_csv(paths.tables / "A3_offer_reconciliation.csv", dtype={"tenor": str})
    mismatches = reconciliation.loc[reconciliation.status.isin(["numeric mismatch", "scope mismatch"]), "event_id"]
    t5 = pd.read_csv(paths.tables / "T5_robustness.csv")
    no_mismatch = t5[(t5.spec == "exclude_offer_mismatch_events") & (t5.level == "auction_wide") & (t5.tol == 0)]
    checks["T5_excludes_offer_mismatches"] = (
        no_mismatch.set_index("country").n_events.to_dict()
        == e[~e.event_id.isin(mismatches)].groupby("country").event_id.nunique().to_dict())
    # every Ghana cross-notice discrepancy carries a recorded author decision
    cross = pd.read_csv(paths.root / "data" / "derived" / "ghana_cross_notice.csv")
    flagged = set(cross.loc[cross.check.isin(["numeric mismatch", "scope mismatch"]), "event_id"])
    dec_path = paths.root / "data" / "review" / "ghana_source_decisions.csv"
    decided = pd.read_csv(dec_path) if dec_path.is_file() else pd.DataFrame(columns=["event_id", "decided_by"])
    checks["GH_discrepancies_have_decisions"] = bool(
        flagged <= set(decided.event_id) and decided.decided_by.notna().all())
    return checks


def key_numbers(paths: Paths) -> dict:
    """Every number quoted in the memo / manuscript / brief, read from generated tables only."""
    t = paths.tables
    k: dict = {}
    t1 = pd.read_csv(t / "T1_decomposition.csv")
    for _, r in t1[(t1.offer_version == "result") & (t1.tol.isin([0, 0.05, 0.1]))].iterrows():
        key = f"{r.country}|{r.level}|{r.window}|tol{r.tol:g}"
        k[key] = dict(n_events=int(r.n_events), n_miss=int(r.n_miss), n_miss_B_ge_O=int(r.n_miss_B_ge_O),
                      share=None if pd.isna(r.volume_share_D) else round(float(r.volume_share_D), 4),
                      ci_b8=[None if pd.isna(r.ci95_lo_b8) else round(float(r.ci95_lo_b8), 4),
                             None if pd.isna(r.ci95_hi_b8) else round(float(r.ci95_hi_b8), 4)],
                      first=r["first"], last=r["last"], sum_S=round(float(r.sum_S), 2), sum_D=round(float(r.sum_D), 2))
    ann = t1[(t1.offer_version == "announced") & (t1.tol == 0) & (t1.window == "common_2023-01-13_2026-10-30")]
    for _, r in ann.iterrows():
        k[f"announced|{r.country}|{r.level}"] = dict(n_events=int(r.n_events), n_miss=int(r.n_miss),
                                                    share=None if pd.isna(r.volume_share_D) else round(float(r.volume_share_D), 4))
    m = pd.read_csv(t / "T4_maturity_shift.csv")
    for _, r in m.iterrows():
        k[f"maturity|{r.country}|{r.window}|{r.subset}"] = dict(
            n=int(r.n), median=round(float(r["median"]), 2), q1=round(float(r.q1), 2), q3=round(float(r.q3), 2),
            n_longer_30=int(r.n_longer_30), n_shorter_30=int(r.n_shorter_30),
            median_actual_days=None if pd.isna(r.median_actual_days) else round(float(r.median_actual_days), 2),
            median_share364_shift=round(float(r.median_share364_shift), 4))
    mk = pd.read_csv(t / "T3_masking.csv")
    for _, r in mk.iterrows():
        k[f"masking|{r.country}|{r.window}"] = dict(n_overall_met=int(r.n_overall_met),
                                                    n_met_with_tenor_miss=int(r.n_met_with_tenor_miss),
                                                    share=round(float(r.share_met_with_tenor_miss), 4))
    g4 = paths.tables / "F6_gate4_strict.csv"
    if g4.is_file():
        g = pd.read_csv(g4)
        k["gate4_pass_holdout_prereg"] = g[(g.period == "holdout") & g.passes_gate4][["level", "country", "model"]].values.tolist()
        k["gate4_pass_holdout_strict"] = g[(g.period == "holdout") & g.passes_gate4_strict_volume][["level", "country", "model"]].values.tolist()
        k["gate4_pass_replication_strict"] = g[(g.period == "replication") & g.passes_gate4_strict_volume][["level", "country", "model"]].values.tolist()
    ev = pd.read_csv(paths.root / "data" / "derived" / "auction_events.csv")
    k["events"] = {c: dict(n=int(len(x)), first=x.held_date.min(), last=x.held_date.max())
                   for c, x in ev.groupby("country")}
    (paths.reports / "key_numbers.json").write_text(json.dumps(k, indent=1, default=str), encoding="utf-8")
    return k


def run_report(paths: Paths) -> bool:
    key_numbers(paths)
    checks = verify(paths)
    derived = paths.root / "data" / "derived"
    files = {p.name: _sha(p) for p in sorted(derived.glob("*.csv"))}
    tables = {p.name: _sha(p) for p in sorted(paths.tables.glob("*.csv"))}
    pkgs = {}
    for pkg in ("pandas", "numpy", "scikit-learn", "scipy", "matplotlib", "pymupdf", "requests", "beautifulsoup4",
                "lxml", "openpyxl", "rapidocr-onnxruntime", "onnxruntime", "pytest"):
        try:
            pkgs[pkg] = version(pkg)
        except Exception:  # noqa: BLE001
            pkgs[pkg] = None
    from .extract import pdftotext_version

    rec = dict(
        generated_utc=datetime.now(UTC).isoformat(timespec="seconds"), snapshot_cutoff=SNAPSHOT_CUTOFF,
        python=sys.version.split()[0], platform=platform.platform(), packages=pkgs,
        pdftotext=pdftotext_version(), git_commit=_git(paths, "rev-parse", "HEAD") or None,
        git_dirty=bool(_git(paths, "status", "--porcelain")) if (paths.root / ".git").exists() else None,
        source_sha256={p.relative_to(paths.root).as_posix(): _sha(p)
                       for p in sorted((paths.root / "src").rglob("*.py"))},
        frozen_manifest_sha256=_sha(paths.frozen / "fetch_manifest.csv"),
        derived_sha256=files, table_sha256=tables,
        verification=checks, all_checks_pass=all(checks.values()),
    )
    inv_meta = paths.frozen / "inventory_meta.json"
    if inv_meta.is_file():
        rec["inventory"] = json.loads(inv_meta.read_text(encoding="utf-8"))
    (paths.reports / "verification.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
    (paths.reports / "run_record.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    return rec["all_checks_pass"]
