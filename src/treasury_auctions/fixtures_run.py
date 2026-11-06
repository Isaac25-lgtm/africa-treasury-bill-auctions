"""Fixture-only end-to-end run (no network, no real cache).

Renders the text fixtures into small synthetic PDFs, seeds an offline cache and
frozen inventories in a temporary project root, then runs parse -> panel ->
audit -> decomposition, asserting the ground-truth cells survive the full path.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .config import Paths

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

DOCS = [
    ("UG", "result", "https://bou.or.ug/uploads/fixture_ug_1237_result.pdf", "ug_1237_result.txt"),
    ("UG", "result", "https://bou.or.ug/uploads/fixture_ug_1237_result_copy.pdf", "ug_1237_result.txt"),
    ("UG", "result", "https://bou.or.ug/uploads/fixture_ug_1235.pdf", "ug_docx_runtogether.txt"),
    # same printed number, different held date: a numbering typo in the source -> separate, flagged event
    ("UG", "result", "https://bou.or.ug/uploads/fixture_ug_1237_renumbered.pdf", "ug_1237_result.txt|04-NOV-2026>05-NOV-2026"),
    ("UG", "result", "https://bou.or.ug/uploads/fixture_ug_bond.pdf", "ug_bond_result.txt"),
    ("UG", "result", "https://bou.or.ug/uploads/fixture_ug_malformed.pdf", "ug_malformed.txt"),
    ("UG", "invitation", "https://bou.or.ug/uploads/fixture_ug_inv_1236.pdf", "ug_invitation_1236.txt"),
    ("KE", "result", "https://www.centralbank.go.ke/uploads/91_day_historical_treasury_bill_results/fixture_ke.pdf",
     "ke_2026-10-26_result.txt"),
    ("GH", "result", "https://www.bog.gov.gh/wp-content/uploads/2024/03/fixture-1892.pdf", "gh_1892_joined_date.txt"),
    ("GH", "result", "https://www.bog.gov.gh/wp-content/uploads/2024/03/fixture-1893.pdf", "gh_1893_two_tenors.txt"),
]


def text_to_pdf(text: str) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=1000, height=1200)
    y = 30
    for line in text.splitlines():
        page.insert_text((20, y), line.replace("¢", "C"), fontname="cour", fontsize=7)
        y += 10
    return doc.tobytes()


def run_fixtures(_paths: Paths | None = None, keep: Path | None = None) -> bool:
    from .analysis import event_panel, with_offer
    from .audit import offer_reconciliation
    from .fetch import SourceCache, sha256
    from .pipeline import run_parse

    tmp = Path(keep) if keep else Path(tempfile.mkdtemp(prefix="tba_fixtures_"))
    paths = Paths(tmp).ensure()
    cache = SourceCache(paths.cache, offline=True)
    inv = {"UG": [], "KE": [], "GH": []}
    for i, (c, kind, url, fx) in enumerate(DOCS):
        name, _, swap = fx.partition("|")
        text = (FIXTURES / name).read_text(encoding="utf-8")
        if swap:
            a, b = swap.split(">")
            text = text.replace(a, b)
        payload = text_to_pdf(text)
        digest = cache._store(payload)
        cache.index[url] = dict(url=url, status="fetched", sha256=digest, bytes=len(payload), media_kind="pdf",
                                retrieved_utc=datetime.now(UTC).isoformat(timespec="seconds"))
        assert sha256(payload) == digest
        inv[c].append(dict(asset_id=f"fx{i:02d}", country=c, kind=kind, url=url, in_scope=True, file_name=Path(url).name,
                           folder_year="2026", title=fx, posted_local="2024-03-01T18:00:00" if c == "GH" else None,
                           posted_utc=None, tender_no_hint=None))
    cache.save_index()
    for c, rows in inv.items():
        pd.DataFrame(rows).to_csv(paths.frozen / f"inventory_{c}.csv", index=False)
    run_parse(paths, cache, cutoff="2026-11-06", workers=1)
    d = tmp / "data" / "derived"
    out = pd.read_csv(d / "auction_outcomes.csv", dtype={"tenor": str})
    ev = pd.read_csv(d / "auction_events.csv")
    docs = pd.read_csv(d / "source_documents.csv")
    checks = {}
    u = out[out.event_id == "UG-1237"].set_index("tenor")
    checks["ug1237_cells"] = (len(u) == 3 and abs(u.loc["91", "A"] - 4.2349) < 1e-9
                              and abs(u.loc["364", "B"] - 933.5267) < 1e-9 and abs(u.O_result.sum() - 350) < 1e-9)
    checks["ug_duplicate_collapsed"] = int((ev.event_id == "UG-1237").sum()) == 1
    checks["ug_reused_number_separate_event"] = "UG-1237-2026-11-05" in set(ev.event_id) and not bool(
        ev.loc[ev.event_id == "UG-1237", "conflict"].iloc[0])
    checks["ug1235_date"] = ev.loc[ev.event_id == "UG-1235", "held_date"].tolist() == ["2026-09-30"]
    checks["bond_excluded"] = docs.loc[docs.url.str.contains("bond"), "status"].tolist() == ["not_target_family"]
    checks["malformed_blocked"] = docs.loc[docs.url.str.contains("malformed"), "status"].tolist() == ["blocked"]
    k = out[out.country == "KE"]
    checks["ke_cells"] = sorted(k.A.round(2).tolist()) == sorted([14334.18, 7685.02, 6773.91])
    checks["gh_date"] = ev.loc[ev.event_id == "GH-1892", "held_date"].tolist() == ["2024-03-01"]
    gh = with_offer(event_panel(paths), "result").set_index("event_id")
    checks["gh_two_tenors_enter_analysis"] = (
        abs(gh.loc["GH-1893", "B"] - 3700.02) < 1e-9 and abs(gh.loc["GH-1893", "A"] - 3677.02) < 1e-9
        and ev.loc[ev.event_id == "GH-1893", "n_tenors"].tolist() == [2]
        and set(out.loc[out.event_id == "GH-1893", "tenor"]) == {"91", "182", "total"})
    rec = offer_reconciliation(paths, write=False)
    checks["gh_same_amount_different_scope"] = (
        rec.loc[rec.event_id == "GH-1893", "status"].tolist() == ["scope mismatch"]
        and pd.isna(gh.loc["GH-1893", "O_announced"]))
    off = pd.read_csv(d / "offer_versions.csv", dtype={"tenor": str})
    checks["ug_invitation_offer"] = (not off.empty) and set(
        off[off.event_id == "UG-1236"].O_announced.round(6)) == {15.0, 35.0, 300.0}
    checks["currencies_not_mixed"] = out.groupby("country").currency.nunique().eq(1).all()
    ok = all(checks.values())
    (paths.reports / "fixture_checks.json").write_text(json.dumps({k: bool(v) for k, v in checks.items()}, indent=1))
    print(json.dumps({k: bool(v) for k, v in checks.items()}, indent=1))
    print("FIXTURE RUN", "PASSED" if ok else "FAILED", "at", tmp)
    return ok
