"""Source audit and missingness (handoff Phase C).

Outputs in ``outputs/reports`` and ``outputs/tables``:
A1_inventory_waterfall.csv      discovered -> in scope -> fetched -> target family -> parsed -> event, by country/year
A2_calendar_gaps.csv            expected event numbers vs observed (consecutive auction/tender/issue ids)
A3_offer_reconciliation.csv     announced (pre-close) vs result-side offer, per event x tenor
A4_ratio_definitions.csv        published cover ratio = B/A, B/O, ambiguous, inconsistent (by country/year)
A5_second_extraction.csv        independent re-extraction agreement on a stratified sample + all unusual rows
A6_pilot_comparison.csv         this rebuild vs the frozen pilot replay, cell by cell
A7_timing_screen.csv            date-order sanity checks (release after held, value date not used as release)
audit_summary.json              headline counts for the decision memo
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .config import Paths


def _derived(paths, name, **kw):
    p = paths.root / "data" / "derived" / f"{name}.csv"
    return pd.read_csv(p, **kw) if p.is_file() and p.stat().st_size > 5 else pd.DataFrame()


def waterfall(paths: Paths) -> pd.DataFrame:
    docs = pd.read_csv(paths.interim / "documents.csv")
    ev = _derived(paths, "auction_events")
    docs["year"] = docs.key_date.fillna("").astype(str).str[:4].replace("", "unknown")
    tgt = {"UG": ("ug_bill_result",), "KE": ("ke_bill_result",), "GH": ("gh_bill_result",)}
    rows = []
    for (c, y), g in docs.groupby(["country", "year"]):
        is_res = g.listed_kind.eq("result") | g.doc_type.isin(tgt[c])
        gr = g[is_res]
        rows.append(dict(country=c, year=y, listed_documents=len(gr),
                         fetched=int(gr.sha256.notna().sum()),
                         fetch_failed=int(gr.status.str.startswith("fetch_").sum() + gr.status.eq("not_fetched").sum()),
                         target_family=int(gr.doc_type.isin(tgt[c]).sum()),
                         other_family=int((~gr.doc_type.isin(tgt[c]) & gr.sha256.notna()).sum()),
                         parsed=int((gr.status == "parsed").sum()), blocked=int((gr.status == "blocked").sum()),
                         extract_error=int((gr.status == "extract_error").sum()),
                         events=int(ev[(ev.country == c) & (ev.held_date.astype(str).str[:4] == y)].event_id.nunique())
                         if not ev.empty else 0))
    w = pd.DataFrame(rows)
    w.to_csv(paths.tables / "A1_inventory_waterfall.csv", index=False)
    return w


def calendar_gaps(paths: Paths, cutoff: str) -> pd.DataFrame:
    ev = _derived(paths, "auction_events")
    docs = pd.read_csv(paths.interim / "documents.csv")
    inv = pd.read_csv(paths.interim / "ug_invitation_rows.csv") if (paths.interim / "ug_invitation_rows.csv").stat().st_size > 5 else pd.DataFrame()
    rows = []
    # Uganda: bill auction numbers are consecutive (one per bill auction)
    u = ev[ev.country == "UG"]
    if not u.empty:
        nos = set(u.auction_no.astype(int))
        inv_nos = set(inv.auction_no.dropna().astype(int)) if not inv.empty else set()
        blocked = docs[(docs.country == "UG") & (docs.status == "blocked")].key_no.dropna().astype(int)
        lo, hi = min(nos), max(nos)
        for n in range(lo, hi + 1):
            if n in nos:
                continue
            st = ("result document present but blocked" if n in set(blocked) else
                  "invitation found, result not in archive" if n in inv_nos else "no invitation or result found")
            rows.append(dict(country="UG", expected_id=n, status=st))
    # Kenya: weekly issues, 91-day issue numbers are consecutive in the modern series; use 182-day if absent
    k = ev[ev.country == "KE"]
    if not k.empty:
        iss = k.issues_json.map(lambda s: json.loads(s) if isinstance(s, str) else {})
        n182 = sorted({int(d.get("182")) for d in iss if d.get("182")})
        if n182:
            have = set(n182)
            for n in range(min(have), max(have) + 1):
                if n not in have:
                    rows.append(dict(country="KE", expected_id=n, status="182-day issue number not observed"))
    g = ev[ev.country == "GH"]
    if not g.empty:
        have = set(g.tender_no.astype(int))
        blocked = set(docs[(docs.country == "GH") & (docs.status == "blocked")].key_no.dropna().astype(int))
        for n in range(min(have), max(have) + 1):
            if n not in have:
                rows.append(dict(country="GH", expected_id=n,
                                 status="result document present but blocked" if n in blocked else "tender number not observed"))
    out = pd.DataFrame(rows, columns=["country", "expected_id", "status"])
    out.to_csv(paths.tables / "A2_calendar_gaps.csv", index=False)
    return out


def offer_reconciliation(paths: Paths) -> pd.DataFrame:
    from .analysis import announced_offer

    ev = _derived(paths, "auction_events")
    out = _derived(paths, "auction_outcomes", dtype={"tenor": str})
    off = _derived(paths, "offer_versions", dtype={"tenor": str})
    if off.empty:
        return pd.DataFrame()
    ann = announced_offer(off, ev)
    res = out[["country", "event_id", "tenor", "O_result"]].dropna(subset=["O_result"])
    m = res.merge(ann, on=["event_id", "tenor"], how="outer", indicator=True)
    m["country"] = m.country.fillna(m.event_id.str[:2])
    m["status"] = np.select(
        [m._merge == "left_only", m._merge == "right_only",
         (m.O_announced - m.O_result).abs() <= 1e-6 * m.O_result.abs() + 0.005],
        ["result only (no pre-close notice recovered)", "announcement only (result not in panel)", "agree"],
        default="mismatch")
    m = m.drop(columns="_merge").merge(ev[["event_id", "held_date"]], on="event_id", how="left")
    m.sort_values(["country", "held_date", "tenor"]).to_csv(paths.tables / "A3_offer_reconciliation.csv", index=False)
    return m


def ratio_definitions(paths: Paths) -> pd.DataFrame:
    out = _derived(paths, "auction_outcomes", dtype={"tenor": str})
    x = out[out.cover_formula.notna()].copy()
    x["year"] = x.held_date.astype(str).str[:4]
    x["formula"] = x.cover_formula.str.replace(r"ambiguous:.*", "ambiguous (A = B)", regex=True)
    t = x.groupby(["country", "year", "formula"]).size().unstack(fill_value=0).reset_index()
    t.to_csv(paths.tables / "A4_ratio_definitions.csv", index=False)
    return t


def second_extraction(paths: Paths, seed: int = 7, per_stratum: int = 4) -> pd.DataFrame:
    """Re-extract with an independent engine (pdftotext -layout; OCR for OCR-derived rows) and compare."""
    from .extract import ocr_available, ocr_pdf_page, pdf_text, pdf_text_alt
    from .fetch import SourceCache
    from .parsers import parse_gh_result, parse_ke_result, parse_ug_result

    cache = SourceCache(paths.cache, offline=True)
    out = _derived(paths, "auction_outcomes", dtype={"tenor": str})
    ev = _derived(paths, "auction_events")
    if out.empty:
        return pd.DataFrame()
    docs = out.drop_duplicates("url")[["country", "event_id", "url", "sha256", "method", "flags"]].merge(
        ev[["event_id", "held_date"]], on="event_id", how="left")
    docs["year"] = docs.held_date.astype(str).str[:4]
    unusual = docs[docs["flags"].notna() | docs.method.fillna("").str.startswith("ocr")]
    rng = np.random.default_rng(seed)
    sample = docs.groupby(["country", "year"], group_keys=False).apply(
        lambda g: g.iloc[rng.permutation(len(g))[:per_stratum]], include_groups=False)
    sample = docs.loc[sample.index] if not sample.empty else sample
    chosen = pd.concat([sample.assign(reason="stratified sample"), unusual.assign(reason="unusual row")]).drop_duplicates("url")
    parser = {"UG": parse_ug_result, "KE": parse_ke_result, "GH": parse_gh_result}
    rows = []
    for _, d in chosen.iterrows():
        payload = cache.read(d.url)
        if payload is None or not payload.startswith(b"%PDF"):
            rows.append(dict(url=d.url, country=d.country, event_id=d.event_id, reason=d.reason, engine=None,
                             status="not a PDF or missing from cache (DOCX/XLSX re-parsed from XML only)"))
            continue
        if str(d.method).startswith("ocr"):
            alt = pdf_text(payload)  # text layer as the independent check of OCR
            engine = alt.method
            pr = parser[d.country](alt.text)
            if not pr.rows and ocr_available():
                alt = ocr_pdf_page(payload, 0, dpi=300)  # different resolution, uncached
                engine = "ocr-rapidocr@300dpi"
                pr = parser[d.country](alt.text)
        else:
            # independent of the text layer: OCR of the rendered page (pdftotext/Xpdf 4.00 was tried first
            # and found to shift table rows on some CBK and BoU layouts, so it is not an independent check)
            alt = ocr_pdf_page(payload, 0, dpi=220, cache_dir=paths.cache / "ocr_audit",
                               digest=d.sha256) if ocr_available() else pdf_text_alt(payload)
            engine = alt.method if alt else None
            pr = parser[d.country](alt.text) if alt else None
            if (pr is None or not pr.rows) and alt is not None:
                alt2 = pdf_text_alt(payload)
                if alt2 is not None:
                    pr2 = parser[d.country](alt2.text)
                    if pr2.rows:
                        pr, engine = pr2, alt2.method + " (fallback; OCR unparseable)"
        if pr is None or not pr.rows:
            rows.append(dict(url=d.url, country=d.country, event_id=d.event_id, reason=d.reason, engine=engine,
                             status="second engine could not parse"))
            continue
        mine = out[out.url == d.url]
        scale = 1e9 if d.country == "UG" else 1.0
        cells = 0
        agree = 0
        maxabs = 0.0
        for row in pr.rows:
            t = str(row["tenor"])
            m = mine[mine.tenor == t]
            if m.empty:
                continue
            for k_alt, k_mine in (("O", "O_result"), ("B", "B"), ("A", "A")):
                if k_alt not in row or k_mine not in m:
                    continue
                a = row[k_alt] / scale
                b = m[k_mine].iloc[0]
                if pd.isna(b):
                    continue
                cells += 1
                diff = abs(a - b)
                maxabs = max(maxabs, diff)
                agree += diff <= 1e-9 + 1e-9 * abs(b)
        date_alt = pr.event.get("held_date") or pr.event.get("value_date")
        rows.append(dict(url=d.url, country=d.country, event_id=d.event_id, reason=d.reason, engine=engine,
                         status="compared", cells=cells, cells_agree=agree, max_abs_diff=maxabs,
                         date_second=date_alt))
    a = pd.DataFrame(rows)
    a.to_csv(paths.tables / "A5_second_extraction.csv", index=False)
    return a


def pilot_comparison(paths: Paths) -> pd.DataFrame:
    pr = paths.root / "pilot_reference" / "cached_exploratory"
    if not (pr / "panel.csv").is_file():
        return pd.DataFrame()
    p = pd.read_csv(pr / "panel.csv")
    g = pd.read_csv(pr / "ghana.csv")
    out = _derived(paths, "auction_outcomes", dtype={"tenor": str})
    ev = _derived(paths, "auction_events")
    mine = out.merge(ev[["event_id", "held_date", "settlement_date"]].rename(
        columns={"held_date": "ev_held", "settlement_date": "ev_settle"}), on="event_id", how="left")
    # pilot keyed Uganda by held date, Kenya by issue/value date, Ghana by held date
    mine["pilot_date"] = np.where(mine.country == "KE", mine.ev_settle, mine.ev_held)
    rows = []
    pt = p.assign(tenor=p.tenor.astype(str))
    for c in ("UG", "KE"):
        a = pt[pt.country == c][["date", "tenor", "offered", "bids", "accepted", "source"]]
        b = mine[mine.country == c][["pilot_date", "tenor", "O_result", "B", "A", "event_id", "url"]]
        m = a.merge(b, left_on=["date", "tenor"], right_on=["pilot_date", "tenor"], how="outer", indicator=True)
        for _, r in m.iterrows():
            st = {"left_only": "pilot only", "right_only": "rebuild only"}.get(r._merge)
            if st is None:
                same = all(abs(x - y) <= 1e-6 + 1e-6 * abs(y) for x, y in
                           ((r.offered, r.O_result), (r.bids, r.B), (r.accepted, r.A)))
                st = "match" if same else "value difference"
            rows.append(dict(country=c, date=r.date if isinstance(r.date, str) else r.pilot_date, tenor=r.tenor,
                             status=st, pilot_O=r.offered, pilot_B=r.bids, pilot_A=r.accepted, O=r.O_result, B=r.B,
                             A=r.A, pilot_source=r.source, source=r.url))
    gb = mine[(mine.country == "GH") & (mine.tenor == "total")]
    m = g.merge(gb, left_on="date", right_on="pilot_date", how="outer", indicator=True)
    for _, r in m.iterrows():
        st = {"left_only": "pilot only", "right_only": "rebuild only"}.get(r._merge)
        if st is None:
            same = all(abs(x - y) <= 0.011 + 1e-6 * abs(y) for x, y in
                       ((r.offered, r.O_result), (r.bids, r.B), (r.accepted, r.A)))
            st = "match" if same else "value difference"
        rows.append(dict(country="GH", date=r.date if isinstance(r.date, str) else r.pilot_date, tenor="total",
                         status=st, pilot_O=r.offered, pilot_B=r.bids, pilot_A=r.accepted, O=r.O_result, B=r.B,
                         A=r.A, pilot_source=r.source_x if "source_x" in r else r.get("source"), source=r.url))
    out = pd.DataFrame(rows)
    out.to_csv(paths.tables / "A6_pilot_comparison.csv", index=False)
    return out


def timing_screen(paths: Paths) -> pd.DataFrame:
    ev = _derived(paths, "auction_events")
    if ev.empty:
        return ev
    x = ev[["country", "event_id", "held_date", "release_date", "release_basis", "available_from",
            "settlement_date"]].copy()
    x["release_before_held"] = x.release_date < x.held_date
    x["release_after_settlement"] = x.release_date > x.settlement_date
    x["value_date_after_release"] = x.settlement_date > x.release_date
    x["release_lag_days"] = (pd.to_datetime(x.release_date) - pd.to_datetime(x.held_date)).dt.days
    x.to_csv(paths.tables / "A7_timing_screen.csv", index=False)
    return x


def _cnt(df: pd.DataFrame, cols: list[str]) -> dict:
    if df is None or df.empty:
        return {}
    return {"|".join(str(x) for x in k): int(v) for k, v in df.groupby(cols).size().items()}


def run_audit(paths: Paths, cutoff: str) -> dict:
    w = waterfall(paths)
    gaps = calendar_gaps(paths, cutoff)
    rec = offer_reconciliation(paths)
    rat = ratio_definitions(paths)
    sec = second_extraction(paths)
    pil = pilot_comparison(paths)
    tim = timing_screen(paths)
    ev = _derived(paths, "auction_events")
    summary = {
        "events": ev.groupby("country").event_id.nunique().to_dict(),
        "event_span": {c: [g.held_date.min(), g.held_date.max()] for c, g in ev.groupby("country")},
        "events_by_year": {c: g.held_date.str[:4].value_counts().sort_index().to_dict() for c, g in ev.groupby("country")},
        "calendar_gaps": _cnt(gaps, ["country", "status"]),
        "offer_reconciliation": _cnt(rec, ["country", "status"]),
        "ratio_definitions": rat.drop(columns="year").groupby("country").sum().to_dict(orient="index")
        if not rat.empty else {},
        "second_extraction": {
            "documents": int(len(sec)), "compared": int((sec.status == "compared").sum()) if not sec.empty else 0,
            "cells": int(sec.cells.sum()) if "cells" in sec else 0,
            "cells_agree": int(sec.cells_agree.sum()) if "cells_agree" in sec else 0,
            "max_abs_diff": float(sec.max_abs_diff.max()) if "max_abs_diff" in sec and sec.max_abs_diff.notna().any() else None,
        },
        "pilot_comparison": _cnt(pil, ["country", "status"]),
        "timing": {"release_before_held": int(tim.release_before_held.sum()),
                   "median_release_lag_days": tim.groupby("country").release_lag_days.median().to_dict()},
        "waterfall_totals": w.drop(columns="year").groupby("country").sum().to_dict(orient="index"),
    }
    (paths.reports / "audit_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str)[:6000])
    return summary
