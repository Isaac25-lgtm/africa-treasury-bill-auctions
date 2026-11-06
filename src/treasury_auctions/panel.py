"""Normalized, linked tables from per-document parses (handoff Phase B schema).

Written to ``data/derived/`` (compact, provenance-carrying CSVs):

source_documents.csv  every inventory URL with hash, method, content class and status
auction_events.csv    one row per country/event with ids, native-time dates, release proxy, flags
offer_versions.csv    announced (pre-close) offers with first-public date and source; history kept
auction_outcomes.csv  one row per event x maturity (Ghana: per maturity B/A plus a 'total' row with O)
reconciliation.csv    invitation vs result offers, printed totals vs sums, cross-notice checks
duplicates.csv        repeated result documents per event and whether they agree

Quantities are stored in native reporting units: UGX bn, KES m, GHS m. Currencies are never mixed.
Genuinely missing quantities stay missing; nothing is filled with zero.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .config import CURRENCY, TIMEZONES, UNIT, Paths

QCOLS = ["O", "B", "A"]


def _read(paths: Paths, name: str) -> pd.DataFrame:
    p = paths.interim / f"{name}.csv"
    if not p.is_file() or p.stat().st_size < 5:
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _next_business_day(d: str | None) -> str | None:
    if not d or pd.isna(d):
        return None
    x = date.fromisoformat(str(d)[:10]) + timedelta(days=1)
    while x.weekday() >= 5:
        x += timedelta(days=1)
    return x.isoformat()


def _dedupe(rows: pd.DataFrame, key: str, value_cols: list[str], tol: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep one document per event when copies agree; quarantine conflicting copies.

    Returns (kept_rows, duplicate_report).
    """
    rep = []
    keep_urls = []
    for k, g in rows.groupby(key, sort=True):
        urls = list(dict.fromkeys(g.url))
        shas = list(dict.fromkeys(g.sha256))
        if len(urls) == 1:
            keep_urls.append(urls[0])
            continue
        piv = g.pivot_table(index="url", columns="tenor", values=value_cols, aggfunc="first")
        agree = bool(((piv.max() - piv.min()).abs() <= tol).all())
        rep.append(dict(key=k, copies=len(urls), distinct_hashes=len(shas), agree=agree, urls=" ; ".join(urls)))
        if agree:
            # prefer a text-layer extraction over OCR, then lexical URL order (deterministic)
            order = g.drop_duplicates("url").assign(o=lambda x: x.method.str.startswith("ocr").astype(int))
            keep_urls.append(order.sort_values(["o", "url"]).url.iloc[0])
    kept = rows[rows.url.isin(keep_urls)].copy()
    conflicts = {r["key"] for r in rep if not r["agree"]}
    conflict_rows = rows[rows[key].isin(conflicts)].copy()
    return pd.concat([kept, conflict_rows.assign(conflict=True)], ignore_index=True), pd.DataFrame(rep)


# ------------------------------------------------------------------------ Uganda
def build_ug(paths: Paths, cutoff: str):
    r = _read(paths, "ug_result_rows")
    events = outcomes = offers = recon = dups = pd.DataFrame()
    if r.empty:
        return events, outcomes, offers, recon, dups
    r = r[r.status == "parsed"].copy()
    r["auction_no"] = r.auction_no.astype("Int64")
    r = r[r.held_date <= cutoff]
    for c in ["O", "B", "A", "B_comp", "B_noncomp", "A_comp", "A_noncomp"]:
        r[c] = r[c] / 1e9  # UGX -> UGX bn
    r["conflict"] = False
    r, dups = _dedupe(r, "auction_no", QCOLS, tol=1e-6)
    r["event_id"] = "UG-" + r.auction_no.astype(str)
    r["country"] = "UG"
    r["tenor"] = r.tenor.astype(int)
    r["days_to_maturity"] = (pd.to_datetime(r.maturity_date) - pd.to_datetime(r.settlement_date)).dt.days
    outcomes = r
    ev = r.sort_values("tenor").groupby("event_id").agg(
        auction_no=("auction_no", "first"), held_date=("held_date", "first"),
        settlement_date=("settlement_date", "first"), release_date_text=("release_date_text", "first"),
        result_url=("url", "first"), result_sha256=("sha256", "first"), method=("method", "first"),
        price_basis=("price_basis", "first"), yield_label=("yield_label", "first"), conflict=("conflict", "max"),
        n_tenors=("tenor", "nunique"), flags=("flags", lambda s: " | ".join(sorted({x for x in s.dropna() if x})))).reset_index()
    # release proxy: date printed on the release when plausible, else held date; strict availability = next
    # business day after that date (time of day not published)
    rel = pd.to_datetime(ev.release_date_text, errors="coerce")
    held = pd.to_datetime(ev.held_date)
    ok = rel.notna() & (rel >= held) & (rel <= held + pd.Timedelta(days=7))
    ev["release_date"] = np.where(ok, rel.dt.date.astype(str), ev.held_date)
    ev["release_basis"] = np.where(ok, "date printed on release (date only)", "held date (no plausible printed date)")
    ev["available_from"] = ev.release_date.map(_next_business_day)
    # invitations
    inv = _read(paths, "ug_invitation_rows")
    if not inv.empty:
        inv = inv[inv.status.isin(["parsed"]) & inv.O_announced.notna()].copy()
        inv["auction_no"] = inv.auction_no.astype("Int64")
        inv["O_announced"] = inv.O_announced / 1e9
        inv["event_id"] = "UG-" + inv.auction_no.astype(str)
        inv["first_public_date"] = inv.notice_date
        inv["first_public_basis"] = "date printed on invitation (date only)"
        inv["country"] = "UG"
        # one offer version per distinct (event, document); identical copies collapse
        sig = inv.groupby(["event_id", "url"]).apply(
            lambda g: tuple(sorted(zip(g.tenor, g.O_announced))), include_groups=False).rename("sig").reset_index()
        sig = sig.merge(inv.drop_duplicates(["event_id", "url"])[["event_id", "url", "first_public_date"]], on=["event_id", "url"])
        sig = sig.sort_values(["event_id", "first_public_date", "url"])
        sig["version"] = sig.groupby("event_id").sig.transform(lambda s: pd.factorize(s)[0] + 1)
        inv = inv.merge(sig[["event_id", "url", "version"]], on=["event_id", "url"])
        inv = inv.drop_duplicates(["event_id", "version", "tenor"])
        offers = inv[["country", "event_id", "auction_no", "tenor", "O_announced", "version", "first_public_date",
                      "first_public_basis", "deadline_date", "deadline_time_text", "auction_date", "url", "sha256",
                      "method", "flags"]].rename(columns={"url": "source_url"})
        ev = ev.merge(inv.groupby("event_id").agg(deadline_date=("deadline_date", "first"),
                                                  deadline_time_text=("deadline_time_text", "first"),
                                                  invitation_url=("url", "first"),
                                                  invitation_auction_date=("auction_date", "first")).reset_index(),
                      on="event_id", how="left")
    ev["country"] = "UG"
    return ev, outcomes, offers, recon, dups


# ------------------------------------------------------------------------ Kenya
def build_ke(paths: Paths, cutoff: str):
    r = _read(paths, "ke_result_rows")
    events = outcomes = offers = recon = dups = pd.DataFrame()
    if r.empty:
        return events, outcomes, offers, recon, dups
    r = r[r.status == "parsed"].copy()
    nx = _read(paths, "ke_next")
    r = r[r.value_date.notna()]
    r["conflict"] = False
    r, dups = _dedupe(r, "value_date", QCOLS, tol=0.011)
    r["event_id"] = "KE-" + r.value_date.astype(str)
    r["country"] = "KE"
    r["tenor"] = r.tenor.astype(int)
    # auction (bid closure) date and announced offers come from the previous notice's section C
    if not nx.empty:
        nx = nx[nx.status == "parsed"].copy()
        nx = nx.sort_values(["next_value_date", "this_value_date", "url"]).drop_duplicates(
            ["next_value_date", "next_offers_json", "next_closure_date"])
    ev = r.sort_values("tenor").groupby("event_id").agg(
        value_date=("value_date", "first"), signed_date=("signed_date", "first"), result_url=("url", "first"),
        result_sha256=("sha256", "first"), method=("method", "first"), conflict=("conflict", "max"),
        n_tenors=("tenor", "nunique"), issues_json=("issues_json", "first"),
        printed_totals_json=("printed_totals_json", "first"),
        reported_redemptions_total=("reported_redemptions_total", "first"),
        flags=("flags", lambda s: " | ".join(sorted({x for x in s.dropna() if x})))).reset_index()
    offer_rows = []
    if not nx.empty:
        nxv = nx.groupby("next_value_date")
        closure = nxv.next_closure_date.first()
        results_d = nxv.next_results_date.first()
        ev["held_date"] = ev.value_date.map(closure)
        ev["results_date_announced"] = ev.value_date.map(results_d)
        ev["deadline_time_text"] = ev.value_date.map(nxv.next_deadline_time_text.first())
        ev["announced_redemptions_total"] = ev.value_date.map(nxv.next_redemptions_total.first())
        ev["announcement_url"] = ev.value_date.map(nxv.url.first())
        ev["announcement_signed_date"] = ev.value_date.map(nxv.this_signed_date.first())
        for (vd,), g in nx.groupby(["next_value_date"]):
            for ver, (_, row) in enumerate(g.iterrows(), start=1):
                vals = json.loads(row.next_offers_json) if isinstance(row.next_offers_json, str) else None
                if not vals or vals == [None]:
                    continue
                iss = json.loads(row.next_issues_json or "{}")
                tenors = sorted(int(t) for t in iss) if iss else [91, 182, 364][: max(0, len(vals) - 1)]
                if len(vals) < len(tenors):
                    continue
                for i, t in enumerate(tenors):
                    offer_rows.append(dict(country="KE", event_id=f"KE-{vd}", tenor=t, O_announced=vals[i], version=ver,
                                           first_public_date=row.this_signed_date,
                                           first_public_basis="signature date of preceding results notice (date only)",
                                           deadline_date=row.next_closure_date, deadline_time_text=row.next_deadline_time_text,
                                           source_url=row.url, sha256=row.sha256, method=row.method,
                                           announced_total=vals[len(tenors)] if len(vals) > len(tenors) else None))
    else:
        ev["held_date"] = None
    # if no preceding announcement: held date unknown; fall back to signed date for the event calendar only
    ev["held_date_basis"] = np.where(ev.held_date.notna(), "bid closure date in preceding notice",
                                     "signature date of results notice (fallback)")
    ev["held_date"] = ev.held_date.fillna(ev.signed_date)
    ev["release_date"] = ev.signed_date.fillna(ev.get("results_date_announced"))
    ev["release_basis"] = np.where(ev.signed_date.notna(), "signature date on results notice (date only)",
                                   "announced results date in preceding notice")
    ev["available_from"] = ev.release_date.map(_next_business_day)
    ev = ev[ev.held_date.fillna(ev.value_date) <= cutoff]
    r = r[r.event_id.isin(ev.event_id)]
    r = r.merge(ev[["event_id", "held_date"]], on="event_id", how="left")
    r["settlement_date"] = r.value_date
    offers = pd.DataFrame(offer_rows)
    if not offers.empty:
        offers = offers[offers.event_id.isin(ev.event_id) | (offers.first_public_date <= cutoff)]
    ev["country"] = "KE"
    ev["settlement_date"] = ev.value_date
    return ev, r, offers, recon, dups


# ------------------------------------------------------------------------ Ghana
def build_gh(paths: Paths, cutoff: str):
    g = _read(paths, "gh_results")
    events = outcomes = offers = recon = dups = pd.DataFrame()
    if g.empty:
        return events, outcomes, offers, recon, dups
    g = g[g.status == "parsed"].copy()
    g = g[g.held_date <= cutoff]
    g["B"] = g[["B_91", "B_182", "B_364"]].sum(axis=1, min_count=3)
    g["A"] = g[["A_91", "A_182", "A_364"]].sum(axis=1, min_count=3)
    g["O"] = g.O_result
    g["tenor"] = 0  # placeholder for dedupe helper
    g["conflict"] = False
    g, dups = _dedupe(g, "tender_no", ["O", "B", "A"], tol=0.011)
    g["event_id"] = "GH-" + g.tender_no.astype(int).astype(str)
    g["country"] = "GH"
    ev = g[["event_id", "country", "tender_no", "held_date", "settlement_date", "signed_date", "notice_no", "posted_utc",
            "posted_local", "url", "sha256", "method", "conflict", "flags", "target_scope"]].rename(
        columns={"url": "result_url", "sha256": "result_sha256"}).drop_duplicates("event_id")
    # release: earliest of archive posting time (UTC, from WordPress metadata) and signature date
    ev["release_date"] = ev.posted_local.str[:10].where(ev.posted_local.notna(), ev.signed_date)
    ev["release_basis"] = np.where(ev.posted_local.notna(), "archive post time (BoG WordPress date)",
                                   "signature date (date only)")
    ev["available_from"] = ev.release_date.map(_next_business_day)
    ev["n_tenors"] = 3
    # announced combined target: previous notice section 3, keyed by tender number
    nxt = g[g.next_tender_no.notna()][["tender_no", "next_tender_no", "next_target", "url", "sha256", "signed_date",
                                       "posted_local", "method"]].copy()
    nxt["event_id"] = "GH-" + nxt.next_tender_no.astype(int).astype(str)
    nxt = nxt.sort_values(["event_id", "tender_no"])
    nxt["version"] = nxt.groupby("event_id").cumcount() + 1
    offers = pd.DataFrame(dict(country="GH", event_id=nxt.event_id, tenor="total", O_announced=nxt.next_target,
                               version=nxt.version,
                               first_public_date=nxt.posted_local.str[:10].where(nxt.posted_local.notna(), nxt.signed_date),
                               first_public_basis="previous notice section 3 (archive post date)",
                               deadline_date=None, deadline_time_text=None, source_url=nxt.url, sha256=nxt.sha256,
                               method=nxt.method))
    rows = []
    for _, x in g.iterrows():
        for t in (91, 182, 364):
            rows.append(dict(country="GH", event_id=x.event_id, tenor=str(t), O=np.nan, B=x[f"B_{t}"], A=x[f"A_{t}"],
                             url=x.url, sha256=x.sha256, method=x.method, raw=x.raw, conflict=x.conflict,
                             held_date=x.held_date, settlement_date=x.settlement_date))
        rows.append(dict(country="GH", event_id=x.event_id, tenor="total", O=x.O, B=x.B, A=x.A, url=x.url,
                         sha256=x.sha256, method=x.method, raw=x.raw, conflict=x.conflict, held_date=x.held_date,
                         settlement_date=x.settlement_date))
    outcomes = pd.DataFrame(rows)
    # cross-notice reconciliation: next notice's section 2 vs this notice's sums
    prev = g[g.prev_tender_no.notna()][["prev_tender_no", "prev_B_total", "prev_A_total", "url"]].copy()
    prev["event_id"] = "GH-" + prev.prev_tender_no.astype(int).astype(str)
    rc = g[["event_id", "B", "A"]].merge(prev.rename(columns={"url": "following_notice_url"}), on="event_id", how="left")
    rc["B_diff"] = rc.prev_B_total - rc.B
    rc["A_diff"] = rc.prev_A_total - rc.A
    rc["check"] = np.where(rc.prev_B_total.isna(), "no following notice",
                           np.where((rc.B_diff.abs() <= 0.011 * 3) & (rc.A_diff.abs() <= 0.011 * 3), "match", "mismatch"))
    recon = rc
    return ev, outcomes, offers, recon, dups


def build_panel(paths: Paths, cutoff: str) -> dict:
    derived = paths.root / "data" / "derived"
    derived.mkdir(parents=True, exist_ok=True)
    evs, outs, offs, recs, dps = [], [], [], [], []
    for country, fn in (("UG", build_ug), ("KE", build_ke), ("GH", build_gh)):
        ev, out, off, rec, dup = fn(paths, cutoff)
        if not ev.empty:
            ev["currency"] = CURRENCY[country]
            ev["unit"] = UNIT[country]
            ev["timezone"] = TIMEZONES[country]
            evs.append(ev)
        if not out.empty:
            out["currency"] = CURRENCY[country]
            out["unit"] = UNIT[country]
            outs.append(out)
        if not off.empty:
            off["unit"] = UNIT[country]
            offs.append(off)
        if not rec.empty:
            recs.append(rec.assign(country=country))
        if not dup.empty:
            dps.append(dup.assign(country=country))
    events = pd.concat(evs, ignore_index=True) if evs else pd.DataFrame()
    outcomes = pd.concat(outs, ignore_index=True) if outs else pd.DataFrame()
    offers = pd.concat(offs, ignore_index=True) if offs else pd.DataFrame()
    keep_out = ["country", "event_id", "tenor", "O", "B", "A", "B_comp", "B_noncomp", "A_comp", "A_noncomp", "unit",
                "currency", "yield_pct", "yield_label", "price_basis", "cover_published", "cover_formula",
                "perf_published", "maturity_date", "settlement_date", "days_to_maturity", "held_date", "issue_no",
                "redemptions", "conflict", "method", "ocr_mean_conf", "url", "sha256", "flags", "raw"]
    outcomes = outcomes[[c for c in keep_out if c in outcomes.columns]].rename(columns={"O": "O_result"})
    outcomes = outcomes.sort_values(["country", "event_id", "tenor"], key=lambda s: s.astype(str))
    events = events.sort_values(["country", "held_date", "event_id"])
    events.to_csv(derived / "auction_events.csv", index=False)
    outcomes.to_csv(derived / "auction_outcomes.csv", index=False)
    offers.to_csv(derived / "offer_versions.csv", index=False)
    (pd.concat(recs, ignore_index=True) if recs else pd.DataFrame()).to_csv(derived / "ghana_cross_notice.csv", index=False)
    (pd.concat(dps, ignore_index=True) if dps else pd.DataFrame()).to_csv(derived / "duplicates.csv", index=False)
    docs = pd.read_csv(paths.interim / "documents.csv")
    docs.to_csv(derived / "source_documents.csv", index=False)
    print(events.groupby("country").agg(events=("event_id", "nunique"), first=("held_date", "min"),
                                        last=("held_date", "max")).to_string())
    return {"events": len(events)}
