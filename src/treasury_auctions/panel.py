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
    # A printed auction number shared by documents with *different* held dates denotes distinct auctions
    # with a numbering typo (e.g. the 18 Nov 2020 release prints 1086, as does 4 Nov 2020). The earliest
    # keeps UG-<no>; later ones are keyed UG-<no>-<held date> and flagged. The number is never guessed.
    first_date = r.groupby("auction_no").held_date.transform("min")
    r["number_reused"] = r.groupby("auction_no").held_date.transform("nunique") > 1
    r["ev_key"] = np.where(r.held_date == first_date, r.auction_no.astype(str),
                           r.auction_no.astype(str) + "-" + r.held_date.astype(str))
    r, dups = _dedupe(r, "ev_key", QCOLS, tol=1e-6)
    r["event_id"] = "UG-" + r.ev_key.astype(str)
    r["flags"] = np.where(r.number_reused, (r["flags"].fillna("") + " | printed auction number also used for another "
                                            "held date").str.strip(" |"), r["flags"])
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
                if len(vals) == 4:
                    # full header "91 DAYS 182 DAYS 364 DAYS TOTAL": map by column, keep the issued tenors only
                    colmap = dict(zip([91, 182, 364], vals[:3]))
                    pairs = [(t, colmap[t]) for t in tenors]
                    total = vals[3]
                elif len(vals) >= len(tenors):
                    pairs = list(zip(tenors, vals))
                    total = vals[len(tenors)] if len(vals) > len(tenors) else None
                else:
                    continue
                for t, val in pairs:
                    offer_rows.append(dict(country="KE", event_id=f"KE-{vd}", tenor=t, O_announced=val, version=ver,
                                           first_public_date=row.this_signed_date,
                                           first_public_basis="signature date of preceding results notice (date only)",
                                           deadline_date=row.next_closure_date, deadline_time_text=row.next_deadline_time_text,
                                           source_url=row.url, sha256=row.sha256, method=row.method,
                                           announced_total=total))
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
    if "maturity_date" in r:
        r["days_to_maturity"] = (pd.to_datetime(r.maturity_date) - pd.to_datetime(r.value_date)).dt.days
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
    g["scope"] = g.target_tenors.map(json.loads)
    g["target_tenors"] = g.scope.map(lambda ts: ";".join(map(str, ts)))
    for field in ("B", "A"):
        g[field] = g.apply(lambda row, field=field: row.reindex([f"{field}_{t}" for t in row.scope]).sum(
            min_count=len(row.scope)), axis=1)
    g["O"] = g.O_result
    g["tenor"] = 0  # placeholder for dedupe helper
    g["conflict"] = False
    g, dups = _dedupe(g, "tender_no", ["O", "B", "A"], tol=0.011)
    g["event_id"] = "GH-" + g.tender_no.astype(int).astype(str)
    g["country"] = "GH"
    ev = g[["event_id", "country", "tender_no", "held_date", "settlement_date", "signed_date", "notice_no", "posted_utc",
            "posted_local", "url", "sha256", "method", "conflict", "flags", "target_scope", "target_tenors"]].rename(
        columns={"url": "result_url", "sha256": "result_sha256"}).drop_duplicates("event_id")
    # release: archive post date when it is within 7 days of the signature date; posts made later are
    # archive back-fills (e.g. 2018 tenders uploaded in July 2019) and fall back to the signature date
    post = pd.to_datetime(ev.posted_local.str[:10], errors="coerce")
    sig = pd.to_datetime(ev.signed_date.fillna(ev.held_date), errors="coerce")
    timely = post.notna() & sig.notna() & ((post - sig).dt.days.between(0, 7))
    ev["release_date"] = np.where(timely, ev.posted_local.str[:10], ev.signed_date.fillna(ev.held_date))
    ev["release_basis"] = np.where(timely, "archive post date (BoG WordPress, within 7 days of signature)",
                                   "signature date (archive post is a later back-fill or missing)")
    ev["archive_backfill"] = post.notna() & ~timely
    ev["available_from"] = ev.release_date.map(_next_business_day)
    ev["n_tenors"] = ev.target_tenors.str.count(";") + 1
    # announced combined target: previous notice section 3, keyed by tender number
    nxt = g[g.next_tender_no.notna()][["tender_no", "next_tender_no", "next_target", "next_tenors",
                                       "next_raw", "url", "sha256", "method"]].copy()
    publication = ev.release_date.where(ev.release_date >= ev.held_date, ev.held_date)
    nxt["release_date"] = nxt.url.map(pd.Series(publication.to_numpy(), index=ev.result_url))
    # a notice cannot announce its own tender: self-references (source typo, e.g. tender 1655) are
    # excluded rather than re-assigned to a guessed tender number
    selfref = nxt[nxt.next_tender_no.astype(int) <= nxt.tender_no.astype(int)]
    nxt = nxt[nxt.next_tender_no.astype(int) > nxt.tender_no.astype(int)].copy()
    nxt["event_id"] = "GH-" + nxt.next_tender_no.astype(int).astype(str)
    nxt = nxt.sort_values(["event_id", "tender_no"])
    nxt["version"] = nxt.groupby("event_id").cumcount() + 1
    offers = pd.DataFrame(dict(country="GH", event_id=nxt.event_id, tenor="total", O_announced=nxt.next_target,
                               version=nxt.version,
                               first_public_date=nxt.release_date,
                               first_public_basis="publication proxy of the preceding results notice",
                               target_tenors=nxt.next_tenors, raw=nxt.next_raw,
                               deadline_date=None, deadline_time_text=None, source_url=nxt.url, sha256=nxt.sha256,
                               method=nxt.method))
    rows = []
    for _, x in g.iterrows():
        for t in x.scope:
            rows.append(dict(country="GH", event_id=x.event_id, tenor=str(t), O=np.nan, B=x[f"B_{t}"], A=x[f"A_{t}"],
                             url=x.url, sha256=x.sha256, method=x.method, raw=x.raw, conflict=x.conflict,
                             held_date=x.held_date, settlement_date=x.settlement_date))
        rows.append(dict(country="GH", event_id=x.event_id, tenor="total", O=x.O, B=x.B, A=x.A, url=x.url,
                         sha256=x.sha256, method=x.method, raw=x.raw, conflict=x.conflict, held_date=x.held_date,
                         settlement_date=x.settlement_date))
    outcomes = pd.DataFrame(rows)
    # cross-notice reconciliation: next notice's section 2 vs this notice's sums
    prev = g[g.prev_tender_no.notna()][["prev_tender_no", "prev_B_total", "prev_A_total", "prev_tenors", "url"]].copy()
    prev["event_id"] = "GH-" + prev.prev_tender_no.astype(int).astype(str)
    rc = g[["event_id", "B", "A", "target_tenors"]].merge(
        prev.rename(columns={"url": "following_notice_url"}), on="event_id", how="left")
    rc["B_diff"] = rc.prev_B_total - rc.B
    rc["A_diff"] = rc.prev_A_total - rc.A
    tolerance = 0.005 * (rc.target_tenors.str.count(";") + 2) + 1e-9
    rc["check"] = np.select(
        [rc.following_notice_url.isna(), rc.prev_B_total.isna() | rc.prev_A_total.isna(),
         rc.prev_tenors.isna(), rc.prev_tenors.ne(rc.target_tenors),
         rc.B_diff.abs().le(tolerance) & rc.A_diff.abs().le(tolerance)],
        ["no following notice", "following totals unavailable", "following scope unavailable",
         "scope mismatch", "match"], default="numeric mismatch")
    if not selfref.empty:
        rc = pd.concat([rc, pd.DataFrame(dict(event_id="GH-" + selfref.tender_no.astype(int).astype(str),
                                              check="section-3 announcement references its own tender number (excluded)",
                                              following_notice_url=selfref.url))], ignore_index=True)
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
    if not events.empty:
        # results cannot be public before the auction: a printed date earlier than the held date (e.g. a
        # wrong year on BoG 1789/1790, template dates on three CBK notices) is raised to the held date
        early = events.release_date.notna() & events.held_date.notna() & (events.release_date < events.held_date)
        events.loc[early, "release_basis"] = events.loc[early, "release_basis"] + "; printed date precedes auction, raised to held date"
        events.loc[early, "release_date"] = events.loc[early, "held_date"]
        events["available_from"] = events.release_date.map(_next_business_day)
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
