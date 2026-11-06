"""Independent source discovery for the three official archives.

Each discoverer returns a list of *asset records* (one per document URL) without
interpreting outcomes. Titles are used only for a provisional classification; the
parser re-classifies every document from its content (handoff Section 5: misfiled
matrices exist and odd titles must not be dropped).
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from .fetch import SourceCache

BOU_API = ("https://bou.or.ug/api/financial-market-auction-information?populate=auctionInformation.overview.button"
           "&populate=auctionInformation.items.file.file.file&populate=auctionInformation.items.file.fileWithMonth.file.file")
BOU_HOST = "https://bou.or.ug"
CBK_INDEX = "https://www.centralbank.go.ke/bills-bonds/treasury-bills/"
BOG_API = "https://www.bog.gov.gh/wp-json/wp/v2/gog_auction_results"

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], start=1)}


def asset_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def now_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- Uganda
def bou_family_hint(title: str, name: str) -> str:
    s = f"{title} {name}".upper().replace("_", " ").replace("-", " ")
    if re.search(r"\bAS AT\b|CLOSING|MATRIX|SECONDARY", s) or name.lower().endswith((".xls", ".xlsx")):
        return "matrix_or_workbook"
    if re.search(r"T ?BILL|TREASURY BILL|91 ?DAYS?|182 ?DAYS?|364 ?DAYS?", s):
        return "bill"
    if re.search(r"BOND|\bYR\b|\d ?YEAR|\bYTM\b|RE ?OPEN", s):
        return "bond"
    return "unknown"


def parse_bou_api(payload: dict, retrieved_utc: str, api_sha256: str) -> list[dict]:
    rows = []
    items = payload["data"]["auctionInformation"]["items"]
    for item in items:
        category = item.get("category") or ""
        for block in item.get("file") or []:
            year = block.get("year")
            entries = [("", x) for x in block.get("file") or []]
            for fw in block.get("fileWithMonth") or []:
                entries += [(fw.get("month") or "", x) for x in fw.get("file") or []]
            for month, entry in entries:
                f = entry.get("file") or {}
                rel = f.get("url")
                if not rel:
                    continue
                url = urljoin(BOU_HOST, rel)
                title = (entry.get("title") or "").strip()
                name = f.get("name") or ""
                kind = {"Auction results": "result", "Invitation to tender": "invitation"}.get(category, "other")
                num = re.search(r"(?:ISSUE[\s_-]*(?:NO\.?|NUMBER)?|TBILLS?|T[\s_-]?BILL[\s_-]*(?:NO)?|TENDER)[\s_.-]*(\d{3,4})\b",
                                f"{title} {name}", re.I)
                rows.append(dict(
                    asset_id=asset_id(url), country="UG", issuer="Bank of Uganda", url=url,
                    referrer=BOU_API, api_sha256=api_sha256, category=category, kind=kind, title=title,
                    file_name=name, ext=(f.get("ext") or "").lower(), size_kb=f.get("size"),
                    folder_year=str(year) if year else "", folder_month=month,
                    family_hint=bou_family_hint(title, name), auction_no_hint=int(num.group(1)) if num else None,
                    asset_created=f.get("createdAt"), asset_updated=f.get("updatedAt"),
                    posted_utc=None, discovered_utc=retrieved_utc,
                ))
    return rows


def discover_bou(cache: SourceCache) -> tuple[list[dict], dict]:
    rec = cache.get(BOU_API, kind="json", refresh=not cache.offline)
    payload = cache.read(BOU_API)
    if payload is None:
        raise RuntimeError(f"BoU API unavailable: {rec.detail}")
    rows = parse_bou_api(json.loads(payload), rec.retrieved_utc or now_utc(), rec.sha256)
    # the same asset URL can be listed under several month folders: keep first, count repeats
    seen: dict[str, dict] = {}
    for r in rows:
        if r["url"] in seen:
            seen[r["url"]]["listing_repeats"] = seen[r["url"]].get("listing_repeats", 1) + 1
        else:
            seen[r["url"]] = r
    meta = {"endpoint": BOU_API, "sha256": rec.sha256, "retrieved_utc": rec.retrieved_utc,
            "listed_entries": len(rows), "unique_urls": len(seen)}
    return list(seen.values()), meta


# --------------------------------------------------------------------------- Kenya
CBK_ISSUE = re.compile(r"(\d{4})\s*-\s*0?91\b.*?(\d{4})\s*-\s*182\b.*?(\d{4})\s*-\s*364\b", re.I)
CBK_ISSUE_2 = re.compile(r"(\d{4})\s*-\s*182\b.*?(\d{4})\s*-\s*364\b", re.I)
CBK_DATED = re.compile(r"DATED\s+(\d{1,2})\s*[-.]\s*(\d{1,2})\s*[-.]\s*(\d{2,4})", re.I)


def parse_cbk_index(html: str, retrieved_utc: str, page_sha256: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, dict] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        m = re.search(r"/uploads/(91|182|364)_day_historical_treasury_bill_results/", href)
        if not m:
            continue
        url = urljoin(CBK_INDEX, href)
        name = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
        rec = out.get(url)
        if rec:
            rec["listed_sections"] = sorted(set(rec["listed_sections"]) | {int(m.group(1))})
            continue
        iss = CBK_ISSUE.search(name)
        iss2 = None if iss else CBK_ISSUE_2.search(name)
        d = CBK_DATED.search(name)
        dated = None
        if d:
            dd, mm, yy = (int(x) for x in d.groups())
            yy = yy + 2000 if yy < 100 else yy
            try:
                dated = datetime(yy, mm, dd).date().isoformat()
            except ValueError:
                dated = None
        out[url] = dict(
            asset_id=asset_id(url), country="KE", issuer="Central Bank of Kenya", url=url, referrer=CBK_INDEX,
            api_sha256=page_sha256, category=f"{m.group(1)}-day historical results", kind="result",
            title=a.get_text(" ", strip=True)[:200], file_name=name, ext=".pdf",
            listed_sections=[int(m.group(1))], family_hint="bill",
            issue_91=int(iss.group(1)) if iss else None, issue_182=int(iss.group(2)) if iss else (int(iss2.group(1)) if iss2 else None),
            issue_364=int(iss.group(3)) if iss else (int(iss2.group(2)) if iss2 else None),
            dated_hint=dated, posted_utc=None, discovered_utc=retrieved_utc,
        )
    return list(out.values())


def discover_cbk(cache: SourceCache) -> tuple[list[dict], dict]:
    rec = cache.get(CBK_INDEX, kind="html", refresh=not cache.offline)
    payload = cache.read(CBK_INDEX)
    if payload is None:
        raise RuntimeError(f"CBK index unavailable: {rec.detail}")
    rows = parse_cbk_index(payload.decode("utf-8", "replace"), rec.retrieved_utc or now_utc(), rec.sha256)
    meta = {"endpoint": CBK_INDEX, "sha256": rec.sha256, "retrieved_utc": rec.retrieved_utc, "unique_urls": len(rows)}
    return rows, meta


# --------------------------------------------------------------------------- Ghana
def discover_bog(cache: SourceCache, max_pages: int = 50) -> tuple[list[dict], dict]:
    posts: list[dict] = []
    warnings: list[str] = []
    for page in range(1, max_pages + 1):
        url = f"{BOG_API}?per_page=100&page={page}&orderby=date&order=desc"
        rec = cache.get(url, kind="json", refresh=not cache.offline)
        payload = cache.read(url)
        if payload is None:
            if page == 1:
                raise RuntimeError(f"BoG API unavailable: {rec.detail}")
            # WordPress answers HTTP 400 past the last page. After a full page this is
            # either the true boundary (total divisible by 100) or an outage: record it.
            warnings.append(f"page {page} unavailable after a full page: {rec.detail}")
            break
        batch = json.loads(payload)
        if not isinstance(batch, list) or not batch:
            break
        posts += batch
        if len(batch) < 100:
            break
    total = len(posts)
    rows = []
    for p in posts:
        title = BeautifulSoup(p["title"]["rendered"], "lxml").get_text(" ", strip=True)
        tn = re.search(r"TENDER\s*(\d{3,4})", title, re.I)
        rows.append(dict(
            post_id=p["id"], post_url=p["link"], title=title, tender_no=int(tn.group(1)) if tn else None,
            posted_local=p.get("date"), posted_utc=(p.get("date_gmt") or "") + "Z" if p.get("date_gmt") else None,
            modified_utc=(p.get("modified_gmt") or "") + "Z" if p.get("modified_gmt") else None, slug=p.get("slug"),
        ))
    meta = {"endpoint": BOG_API, "posts": total, "first_posted": min((r["posted_local"] for r in rows), default=None),
            "last_posted": max((r["posted_local"] for r in rows), default=None), "warnings": warnings}
    return rows, meta


def bog_attachments(cache: SourceCache, posts: list[dict], workers: int = 4) -> list[dict]:
    """Visit each official post page and list attached PDFs."""
    cache.get_many([p["post_url"] for p in posts], workers=workers, kind="html")
    out = []
    for p in posts:
        payload = cache.read(p["post_url"])
        base = dict(country="GH", issuer="Bank of Ghana", referrer=p["post_url"], category="gog_auction_results",
                    kind="result", title=p["title"], tender_no_hint=p["tender_no"], post_id=p["post_id"],
                    posted_local=p["posted_local"], posted_utc=p["posted_utc"], modified_utc=p["modified_utc"],
                    family_hint="bill")
        if payload is None:
            out.append({**base, "asset_id": None, "url": None, "file_name": None, "ext": None,
                        "discovery_status": "post_page_unavailable"})
            continue
        soup = BeautifulSoup(payload.decode("utf-8", "replace"), "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            href = urljoin(p["post_url"], a["href"])
            if re.search(r"/wp-content/uploads/.+\.pdf$", href, re.I) and href not in links:
                links.append(href)
        if not links:
            out.append({**base, "asset_id": None, "url": None, "file_name": None, "ext": None,
                        "discovery_status": "no_pdf_on_post"})
        for href in links:
            out.append({**base, "asset_id": asset_id(href), "url": href,
                        "file_name": unquote(urlsplit(href).path.rsplit("/", 1)[-1]), "ext": ".pdf",
                        "discovery_status": "ok", "attachments_on_post": len(links)})
    return out
