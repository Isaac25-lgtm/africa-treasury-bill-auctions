"""Parse stage: cached bytes -> per-document parse tables (``data/interim``).

Outputs
-------
documents.csv            one row per inventory URL: hash, extraction method, content class, status
ug_result_rows.csv       Uganda result tenor rows (raw units: UGX)
ug_invitation_rows.csv   Uganda invitation tenor offers (raw units: UGX)
ke_result_rows.csv       Kenya result tenor rows (KES million)
ke_next.csv              Kenya section-C announcements (next auction offer/closure/redemptions)
gh_results.csv           Ghana notices (combined target, tenor bids/accepted, previous/next sections)
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from .config import Paths
from .extract import Extracted, extract, ocr_available, ocr_pdf_page
from .fetch import SourceCache
from .inventory import load_inventory
from .parsers import (
    ParseResult,
    classify_ug,
    parse_gh_result,
    parse_ke_result,
    parse_ug_invitation,
    parse_ug_result,
)

PARSER_VERSION = "1.0.0"


def _parse_ug(text: str, listed_kind: str) -> ParseResult:
    cls = classify_ug(text)
    if cls == "ug_bill_invitation":
        return parse_ug_invitation(text)
    if cls == "ug_bill_result":
        return parse_ug_result(text)
    return ParseResult(cls)


def _needs_ocr(country: str, pr: ParseResult, e: Extracted, media_kind: str) -> bool:
    if media_kind != "pdf" or country != "UG":
        return False
    if pr.doc_type in ("ug_empty_text", "ug_unclassified"):
        return True
    if pr.doc_type == "ug_bill_result" and any(b.startswith("missing") for b in pr.blocking):
        return True
    if pr.doc_type == "ug_bill_invitation" and "no tenor offers found" in pr.blocking:
        return True
    # text layer without a readable quantity table (image table, or overlapping template layers as in
    # the 6 May 2026 release) cannot support a classification: read the rendered page instead
    import re

    has_rows = re.search(r"^\s*(?:AMOUNT\s+)?OFFERED", e.text, re.M | re.I) and re.search(
        r"^\s*(?:AMOUNT\s+)?TENDERED", e.text, re.M | re.I)
    if pr.doc_type in ("ug_bond_other", "ug_other_invitation") and not has_rows:
        return True
    # overlapping template layers leave doubled words ("RESULTSRESULTSOFOF", "AUCTIONAUCTION")
    if re.search(r"\b(RESULTS|AUCTION|TREASURY)\1", e.text[:1500].upper()):
        return True
    return False


def load_corrections(paths: Paths) -> dict[str, list[dict]]:
    """Reviewed corrections keyed by document hash (``data/review/corrections.csv``)."""
    p = paths.root / "data" / "review" / "corrections.csv"
    if not p.is_file():
        return {}
    out: dict[str, list[dict]] = {}
    for r in pd.read_csv(p, dtype=str).to_dict("records"):
        out.setdefault(r["doc_sha256"], []).append(r)
    return out


def apply_corrections(text: str, entries: list[dict]) -> tuple[str, list[str]]:
    """Replace the exact old token on the named maturity row only; return text and an audit note per entry."""
    import re

    notes = []
    lines = text.splitlines()
    for c in entries:
        rx = re.compile(rf"\b{c['tenor']}\s*[- ]?\s*DAY\s+(?:T\s*[/-]\s*)?BILLS?\b", re.I)
        hit = [i for i, ln in enumerate(lines) if rx.search(ln) and c["old_value"] in ln]
        if len(hit) != 1:
            notes.append(f"correction NOT applied ({c['tenor']} {c['field']}): row not uniquely found")
            continue
        new = f"{float(c['new_value']):,.2f}"
        lines[hit[0]] = lines[hit[0]].replace(c["old_value"], new, 1)
        notes.append(f"correction applied {c['tenor']} {c['field']}: {c['old_value']!r} -> {new} (evidence {c['evidence_url']})")
    return "\n".join(lines), notes


def parse_one(country: str, listed_kind: str, payload: bytes, media_kind: str, name: str, digest: str,
              ocr_dir, corrections: dict | None = None) -> tuple[Extracted, ParseResult]:
    e = extract(payload, media_kind, name)
    parser = {"UG": lambda t: _parse_ug(t, listed_kind), "KE": parse_ke_result, "GH": parse_gh_result}[country]
    pr = parser(e.text)
    if corrections and digest in corrections and pr.blocking:
        fixed, notes = apply_corrections(e.text, corrections[digest])
        prc = parser(fixed)
        if prc.ok and not prc.blocking:
            e = Extracted(fixed, e.method + "+ledger", e.tool, e.pages, notes=[*e.notes, *notes])
            prc.flags.extend(notes)
            return e, prc
    if _needs_ocr(country, pr, e, media_kind) and ocr_available():
        eo = ocr_pdf_page(payload, 0, cache_dir=ocr_dir, digest=digest)
        # 1) the rendered page alone; 2) text layer + OCR (header fields may survive only in the text layer)
        pro = parser(eo.text)
        if not (pro.ok and not pro.blocking) and e.text.strip():
            merged = Extracted(e.text + "\n" + eo.text, eo.method, eo.tool, ocr_page=eo.ocr_page,
                               ocr_mean_conf=eo.ocr_mean_conf, ocr_min_conf=eo.ocr_min_conf,
                               notes=[*eo.notes, "parsed on text layer + OCR"])
            prm = parser(merged.text)
            if prm.ok and not prm.blocking:
                eo, pro = merged, prm
        if pro.ok and not pro.blocking:
            eo.notes.append(f"text layer insufficient ({pr.doc_type}; {'; '.join(pr.blocking)})")
            return eo, pro
        if pr.doc_type in ("ug_empty_text", "ug_unclassified") and pro.doc_type not in ("ug_empty_text",):
            return eo, pro
    return e, pr


def _doc_row(item: dict, rec: dict | None, e: Extracted | None, pr: ParseResult | None, status: str,
             detail: str = "") -> dict:
    row = dict(asset_id=item["asset_id"], country=item["country"], listed_kind=item["kind"], url=item["url"],
               title=item.get("title"), folder_year=item.get("folder_year"), folder_month=item.get("folder_month"),
               posted_local=item.get("posted_local"), posted_utc=item.get("posted_utc"),
               sha256=(rec or {}).get("sha256"), bytes=(rec or {}).get("bytes"),
               media_kind=(rec or {}).get("media_kind"), retrieved_utc=(rec or {}).get("retrieved_utc"),
               parser_version=PARSER_VERSION, status=status, detail=detail)
    if e is not None:
        row.update(method=e.method, tool=e.tool, ocr_page=e.ocr_page, ocr_mean_conf=e.ocr_mean_conf,
                   ocr_min_conf=e.ocr_min_conf, text_chars=len(e.text), extract_notes="; ".join(e.notes))
    if pr is not None:
        ev = pr.event
        row.update(doc_type=pr.doc_type, blocking=" | ".join(pr.blocking), flags=" | ".join(pr.flags),
                   key_no=ev.get("auction_no") or ev.get("tender_no") or (ev.get("issues") or {}).get(91)
                   or (ev.get("issues") or {}).get(182),
                   key_date=ev.get("held_date") or ev.get("auction_date") or ev.get("value_date"))
    return row


def run_parse(paths: Paths, cache: SourceCache, cutoff: str, workers: int = 4) -> dict:
    inv = load_inventory(paths)
    inv = inv[inv.in_scope & inv.url.notna()].drop_duplicates("url")
    ocr_dir = paths.cache / "ocr"
    corrections = load_corrections(paths)
    items = inv.to_dict("records")

    def work(item):
        rec = cache.index.get(item["url"])
        payload = cache.read(item["url"])
        if payload is None:
            st = "not_fetched" if rec is None else f"fetch_{rec.get('status')}"
            return item, rec, None, None, st, (rec or {}).get("detail") or ""
        name = item.get("file_name") or item["url"]
        try:
            e, pr = parse_one(item["country"], item["kind"], payload, rec.get("media_kind"), name, rec["sha256"],
                              ocr_dir, corrections)
        except Exception as exc:  # noqa: BLE001 - recorded, never silent
            return item, rec, None, None, "extract_error", f"{type(exc).__name__}: {exc}"[:300]
        if pr.ok and not pr.blocking:
            st = "parsed"
        elif pr.ok:
            st = "blocked"
        else:
            st = "not_target_family"
        return item, rec, e, pr, st, ""

    # text extraction is cheap; OCR is serialized inside the engine (single-thread ONNX session)
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
        results = list(pool.map(work, items))

    docs, ugr, ugi, ker, ken, gh = [], [], [], [], [], []
    for item, rec, e, pr, st, detail in results:
        docs.append(_doc_row(item, rec, e, pr, st, detail))
        if pr is None or not pr.ok:
            continue
        base = dict(asset_id=item["asset_id"], url=item["url"], sha256=rec["sha256"], method=e.method,
                    ocr_mean_conf=e.ocr_mean_conf, status=st, blocking=" | ".join(pr.blocking),
                    flags=" | ".join(pr.flags), raw=json.dumps(pr.raw, ensure_ascii=False))
        ev = pr.event
        if pr.doc_type == "ug_bill_result":
            for row in pr.rows or [{}]:
                ugr.append({**base, **{k: v for k, v in ev.items()}, **row})
        elif pr.doc_type == "ug_bill_invitation":
            for row in pr.rows or [{}]:
                ugi.append({**base, **ev, **row, "folder_year": item.get("folder_year"),
                            "title": item.get("title")})
        elif pr.doc_type == "ke_bill_result":
            evs = {k: v for k, v in ev.items() if k not in ("next", "issues", "printed_totals")}
            evs["issues_json"] = json.dumps(ev.get("issues", {}))
            evs["printed_totals_json"] = json.dumps(ev.get("printed_totals", {}))
            for row in pr.rows or [{}]:
                ker.append({**base, **evs, **row, "tenors_present": ";".join(map(str, ev.get("tenors_present", [])))})
            nx = ev.get("next")
            if nx:
                ken.append({**base, "this_value_date": ev.get("value_date"), "this_signed_date": ev.get("signed_date"),
                            "this_issue_91": ev.get("issues", {}).get(91),
                            "this_issue_182": ev.get("issues", {}).get(182),
                            "next_issues_json": json.dumps(nx.get("issues", {})), "next_value_date": nx.get("value_date"),
                            "next_offers_json": json.dumps(nx.get("offers")), "next_offer_raw": nx.get("offer_raw"),
                            "next_closure_date": nx.get("closure_date"), "next_results_date": nx.get("results_date"),
                            "next_redemptions_total": nx.get("redemptions_total"),
                            "next_deadline_time_text": nx.get("deadline_time_text")})
        elif pr.doc_type == "gh_bill_result":
            row = {**base, **{k: v for k, v in ev.items() if k not in ("prev", "next")},
                   "posted_utc": item.get("posted_utc"), "posted_local": item.get("posted_local"),
                   "post_tender_no": item.get("tender_no_hint")}
            for t in pr.rows:
                row[f"B_{t['tenor']}"] = t["B"]
                row[f"A_{t['tenor']}"] = t["A"]
            prev, nxt = ev.get("prev") or {}, ev.get("next") or {}
            row.update(prev_tender_no=prev.get("tender_no"), prev_held_date=prev.get("held_date"),
                       prev_B_total=prev.get("B_total"), prev_A_total=prev.get("A_total"),
                       next_tender_no=nxt.get("tender_no"), next_target=nxt.get("target"),
                       next_raw=nxt.get("raw"), prev_raw=prev.get("raw"))
            gh.append(row)

    out = paths.interim
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(docs).sort_values(["country", "url"]).to_csv(out / "documents.csv", index=False)
    for name, rows in (("ug_result_rows", ugr), ("ug_invitation_rows", ugi), ("ke_result_rows", ker),
                       ("ke_next", ken), ("gh_results", gh)):
        pd.DataFrame(rows).to_csv(out / f"{name}.csv", index=False)
    d = pd.DataFrame(docs)
    summary = d.groupby(["country", "status"]).size().unstack(fill_value=0)
    print(summary.to_string())
    print(d.groupby(["country", "doc_type"]).size().to_string())
    (paths.reports / "parse_summary.json").write_text(
        json.dumps({"parser_version": PARSER_VERSION, "cutoff": cutoff,
                    "status_counts": {f"{k[0]}|{k[1]}": int(v) for k, v in d.groupby(["country", "status"]).size().items()},
                    "doc_types": {f"{k[0]}|{k[1]}": int(v) for k, v in d.groupby(["country", "doc_type"]).size().items()}},
                   indent=1), encoding="utf-8")
    from .panel import build_panel

    build_panel(paths, cutoff)
    return {"documents": len(docs)}
