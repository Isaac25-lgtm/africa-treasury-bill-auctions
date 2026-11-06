"""Content parsers for official notices.

Every parser returns a ``ParseResult`` with:
* ``doc_type`` - content classification (independent of the archive title)
* ``event``    - document-level fields (ids, dates, notes)
* ``rows``     - one dict per maturity (or one aggregate row for Ghana)
* ``raw``      - raw source line text for every extracted field (provenance)
* ``flags``    - validation problems; a non-empty ``blocking`` list keeps the
                 document out of primary estimands until reviewed.

Parsers never guess: an ambiguous number (e.g. ``1.141.12``) is a flag, not a value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from dateutil import parser as dparser

MONTH = r"(?:JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUNE?|JULY?|AUG(?:UST)?|SEPT?(?:EMBER)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)"
WEEKDAY = r"(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)"
# 08-Nov-2017 | 07-DEC-2022 | 9-Mar-23 | 04-December-2019 | 1ST MARCH 2024 | 1STMARCH 2024 | 30TH OCTOBER 2026
DATE_DMY = re.compile(
    rf"(?<!\d)(\d{{1,2}})\s*(?:ST|ND|RD|TH)?\s*[-/ .,]?\s*({MONTH})\.?\s*[-/ .,]?\s*(\d{{4}}|\d{{2}})(?!\d)", re.I)
DATE_NUM = re.compile(r"\b(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]\s*(\d{4}|\d{2})(?!\d)")
# Monday, 15 October 2026 | November 05, 2026 | Wednesday 21, October 2026 | December 03,2020
DATE_MDY = re.compile(rf"\b({MONTH})\.?\s+(\d{{1,2}})(?:ST|ND|RD|TH)?\s*,?\s*(\d{{4}})(?!\d)", re.I)

NUM = re.compile(r"(?<![\w.,/])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w/]|[.,]\d)")
TARGET_TYPES = {"ug_bill_result", "ug_bill_invitation", "ke_bill_result", "gh_bill_result"}
BAD_NUM = re.compile(r"\b\d{1,3}\.\d{3}\.\d{1,3}\b|\b\d+,\d{1,2}\b(?!\d)")


@dataclass
class ParseResult:
    doc_type: str
    event: dict = field(default_factory=dict)
    rows: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    flags: list[str] = field(default_factory=list)
    blocking: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True only for the target families (Treasury bill results and bill invitations)."""
        return self.doc_type in TARGET_TYPES


def _year(y: str) -> int:
    y = int(y)
    return y + 2000 if y < 100 else y


def to_date(m: re.Match | None, order: str = "dmy") -> str | None:
    if not m:
        return None
    try:
        if order == "dmy_name":
            d, mo, y = m.group(1), m.group(2), m.group(3)
            return dparser.parse(f"{d} {mo[:3]} {_year(y)}", dayfirst=True).date().isoformat()
        if order == "mdy_name":
            mo, d, y = m.group(1), m.group(2), m.group(3)
            return dparser.parse(f"{d} {mo[:3]} {_year(y)}", dayfirst=True).date().isoformat()
        d, mo, y = (int(x) for x in m.groups())
        return date(_year(str(y)), mo, d).isoformat()
    except (ValueError, OverflowError):
        return None


def first_date(s: str) -> str | None:
    """Earliest-positioned date of any supported form in s."""
    cands = []
    for rx, order in ((DATE_DMY, "dmy_name"), (DATE_MDY, "mdy_name"), (DATE_NUM, "dmy")):
        m = rx.search(s)
        if m:
            v = to_date(m, order)
            if v:
                cands.append((m.start(), v))
    return min(cands)[1] if cands else None


def nums(s: str) -> list[float]:
    s = re.sub(r"\([^)]*\)", " ", s)  # drop unit annotations such as (Kshs. M)
    return [float(x.replace(",", "")) for x in NUM.findall(s)]


def line_after(text: str, label: str, start: int = 0, end: int | None = None) -> tuple[str | None, int]:
    """Return the remainder of the first line at/after ``start`` whose stripped text starts with label."""
    rx = re.compile(rf"^[ \t]*{label}[ \t]*:?(.*)$", re.I | re.M)
    m = rx.search(text, start, end if end is not None else len(text))
    if not m:
        return None, -1
    return m.group(1), m.end()


def values(text: str, label: str, n: int = 3, start: int = 0, end: int | None = None):
    rest, pos = line_after(text, label, start, end)
    if rest is None:
        return None, None, -1
    v = nums(rest)
    return (v[:n] if len(v) >= n else None), rest.strip(), pos


def published_ratio_formula(ratio, O, B, A, precision=None) -> str:
    """Identify whether a published cover ratio equals B/O, B/A, A/O, or none, at quoted precision."""
    if ratio is None:
        return "missing"
    if precision is None:
        s = f"{ratio}"
        precision = len(s.split(".")[1]) if "." in s else 0
    tol = 0.5 * 10 ** (-precision) + 1e-9
    hits = []
    # the published label refers to B/A or B/O depending on vintage (handoff Section 3)
    for name, val in (("B/O", B / O if O else None), ("B/A", B / A if A else None)):
        if val is not None and abs(round(val, precision) - ratio) <= tol:
            hits.append(name)
    if len(hits) > 1:
        return "ambiguous:" + "|".join(hits)
    return hits[0] if hits else "inconsistent"


# =========================================================================== Uganda
UG_RESULT_HINT = re.compile(r"RESULTS?\s+OF\s+(?:THE\s+)?TREASURY\s+BILLS?|TREASURY\s+BILLS?\s+AUCTION\s+RESULTS|T[\s-]?BILLS?\s+AUCTION", re.I)
UG_BOND_HINT = re.compile(r"TREASURY\s+BONDS?|T[\s-]?BONDS?\b|BOND\s+AUCTION|RE-?OPEN", re.I)


UG_GLUED = [  # OCR drops spaces inside labels ("AMOUNTOFFERED"); restore known label words only
    ("AMOUNTOFFERED", "AMOUNT OFFERED"), ("AMOUNTTENDERED", "AMOUNT TENDERED"), ("ACCEPTEDBIDS", "ACCEPTED BIDS"),
    ("BIDTOCOVERRATIO", "BID TO COVER RATIO"), ("BIDTOCOVER", "BID TO COVER"), ("INVITATIONTOTENDER", "INVITATION TO TENDER"),
    ("AUCTIONDATE", "AUCTION DATE"), ("SETTLEMENTDATE", "SETTLEMENT DATE"), ("MATURITYDATE", "MATURITY DATE"),
    ("ISSUEDATE", "ISSUE DATE"), ("CUT-OFFPRICE", "CUT-OFF PRICE"), ("CUTOFFPRICE", "CUT OFF PRICE"),
    ("PRESSRELEASE", "PRESS RELEASE"), ("HELDON", "HELD ON"), ("ISSUENO", "ISSUE NO"), ("AUCTIONNO", "AUCTION NO"),
    ("EFFECTIVEYIELD", "EFFECTIVE YIELD"), ("OFFERINGAMOUNT", "OFFERING AMOUNT"),
    ("DESCRIPTIONOFOFFERING", "DESCRIPTION OF OFFERING"), ("DETAILSOFOFFERING", "DETAILS OF OFFERING"),
    ("RESULTSOFTREASURYBILLSAUCTION", "RESULTS OF TREASURY BILLS AUCTION"),
]


def deglue(text: str) -> str:
    """Repair OCR label artefacts without touching any numeric value.

    * re-insert spaces in known label words
    * O/0 confusion inside the labels AUCTION, NO, HELD ON (never inside numbers)
    * a 12-character ISIN glued to the following tenor ("UG12B070422691DAYS")
    """
    text = re.sub(r"AUCTI0N", "AUCTION", text, flags=re.I)
    text = re.sub(r"(AUCTION\s*)N0(?=\s*[:.])", r"\1NO", text, flags=re.I)
    text = re.sub(r"HELD\s*0N", "HELD ON", text, flags=re.I)
    text = re.sub(r"\b(UG\d{2}[A-Z]\d{7})(?=(?:91|182|364)\s*DAYS)", r"\1 ", text)
    for a, b in UG_GLUED:
        text = re.sub(a, b, text, flags=re.I)
    text = re.sub(r"RESULTS\s*OF\s*TREASURY\s*BILLS\s*AUCTION", "RESULTS OF TREASURY BILLS AUCTION", text, flags=re.I)
    return text


def _bill_like_maturities(text: str) -> bool:
    """Three maturity dates about 3, 6 and 12 months apart (used when OCR misses the banner heading)."""
    line, _ = line_after(text, r"MATURITY\s+DATES?")
    if not line:
        return False
    ds = [to_date(m, "dmy_name") for m in DATE_DMY.finditer(line)]
    ds = [date.fromisoformat(d) for d in ds if d]
    if len(ds) != 3:
        return False
    gap1, gap2 = (ds[1] - ds[0]).days, (ds[2] - ds[0]).days
    return 80 <= gap1 <= 100 and 255 <= gap2 <= 290


def classify_ug(text: str) -> str:
    text = deglue(text)
    up = text.upper()
    has_table = bool(re.search(r"^\s*(?:AMOUNT\s+)?OFFERED", text, re.M | re.I)) and bool(
        re.search(r"^\s*(?:AMOUNT\s+)?(?:TENDERED|BIDS\s+RECEIVED)", text, re.M | re.I))
    if "INVITATION TO TENDER" in up or "DETAILS OF OFFERING" in up or "DESCRIPTION OF OFFERING" in up:
        if re.search(r"\b(?:91|182|364)\s*-?\s*DAYS?\b", up) and not re.search(r"\bYEAR|\bYR\b", up[:1500]):
            return "ug_bill_invitation"
        return "ug_bond_invitation" if UG_BOND_HINT.search(up) or "YEAR" in up else "ug_other_invitation"
    bill_maturities = bool(re.search(r"MATURITIES[^\n]*\b91\b[^\n]*\b364\b", up)) or _bill_like_maturities(text)
    if has_table and (re.search(r"\b91\b", up) or bill_maturities) and (
            UG_RESULT_HINT.search(up) or ("PRESS RELEASE" in up and bill_maturities and not UG_BOND_HINT.search(up))):
        return "ug_bill_result"
    if has_table and UG_BOND_HINT.search(up):
        return "ug_bond_result"
    if UG_BOND_HINT.search(up):
        return "ug_bond_other"
    if "## SHEET" in text or re.search(r"CLOSING\s+(?:PRICE|YIELD)|\bAS AT\b", up):
        return "ug_matrix"
    if not text.strip():
        return "ug_empty_text"
    return "ug_unclassified"


def parse_ug_result(text: str) -> ParseResult:
    text = deglue(text)
    r = ParseResult(classify_ug(text))
    if r.doc_type != "ug_bill_result":
        return r
    up = text.upper()
    ev = r.event
    m = re.search(r"AUCTION\s*(?:NO|NUMBER)\.?\s*:?\s*(\d{3,4})", up) or re.search(r"ISSUE\s*(?:NO|NUMBER)\.?\s*:?\s*(\d{3,4})", up)
    ev["auction_no"] = int(m.group(1)) if m else None
    held_line = re.search(r"(?:HELD\s+ON|AUCTION\s+DATE\s*:?)\s*([^\n]{0,60})", up)
    ev["held_date"] = first_date(held_line.group(1)) if held_line else None
    r.raw["held_date"] = held_line.group(0).strip() if held_line else None
    sett = re.search(r"(?:SETTLED|SETTLEMENT\s+DATE\s*:?|ISSUE\s+DATE\s*:?|VALUE\s+DATE\s*:?)\s*([^\n]{0,50})", up)
    ev["settlement_date"] = first_date(sett.group(1)) if sett else None
    r.raw["settlement_date"] = sett.group(0).strip() if sett else None
    tail = up[up.rfind("BID TO COVER"):] if "BID TO COVER" in up else up[-400:]
    ev["release_date_text"] = first_date(tail[:400])
    # maturity dates (per tenor) and price/yield basis labels
    mat_line, _ = line_after(text, r"MATURITY\s+DATES?")
    mats = []
    if mat_line:
        for rx, order in ((DATE_DMY, "dmy_name"), (DATE_NUM, "dmy")):
            mats = [to_date(mm, order) for mm in rx.finditer(mat_line)]
            if len(mats) >= 3:
                break
    r.raw["maturity_dates"] = mat_line.strip() if mat_line else None
    price_label = re.search(r"^\s*(WEIGHTED\s+AVERAGE\s+PRICE|CUT[\s-]*OFF\s+PRICE)", text, re.I | re.M)
    ev["price_basis"] = ("WAP" if price_label and "WEIGHTED" in price_label.group(1).upper() else
                         "cut-off" if price_label else None)
    yld, yraw, _ = values(text, r"EFFECTIVE\s+YIELD(?:\s*\(YTM\))?(?:\s+AT\s+(?:WAP|CUT\s*OFF(?:\s+PRICE)?))?")
    ylabel = re.search(r"^\s*(EFFECTIVE\s+YIELD[^\d\n]*)", text, re.I | re.M)
    ev["yield_label"] = re.sub(r"\s+", " ", ylabel.group(1)).strip(" :") if ylabel else None
    r.raw["effective_yield"] = yraw
    # quantities: OFFERED, TENDERED (+components), ACCEPTED (+components)
    O, Oraw, _ = values(text, r"(?:AMOUNT\s+)?OFFERED(?:\s*\(UGX\))?")
    B, Braw, pb = values(text, r"(?:AMOUNT\s+)?(?:TENDERED|BIDS\s+RECEIVED)")
    A, Araw, pa = values(text, r"(?:TOTAL\s+)?(?:AMOUNT\s+)?ACCEPTED(?:\s+BIDS)?")
    r.raw.update(offered=Oraw, tendered=Braw, accepted=Araw)
    Bc = Bn = Ac = An = None
    if pb > 0 and pa > 0:
        Bc, _, _ = values(text, r"COMPET[EI]TIVE", 3, pb, pa)
        Bn, _, _ = values(text, r"NON[\s-]*COMPET[EI]TIVE", 3, pb, pa)
        Ac, _, _ = values(text, r"COMPET[EI]TIVE", 3, pa)
        An, _, _ = values(text, r"NON[\s-]*COMPET[EI]TIVE", 3, pa)
    cover, craw, _ = values(text, r"BID\s+TO\s+COVER(?:\s+RATIO)?")
    r.raw["cover"] = craw
    for label, v in (("offered", O), ("tendered", B), ("accepted", A)):
        if v is None:
            r.blocking.append(f"missing {label} row")
    for k, rawv in r.raw.items():
        if isinstance(rawv, str) and BAD_NUM.search(rawv) and k in ("offered", "tendered", "accepted"):
            r.blocking.append(f"malformed number in {k}: {rawv[:80]}")
    if not ev.get("held_date"):
        r.blocking.append("held date not found")
    if r.blocking:
        return r
    for i, tenor in enumerate((91, 182, 364)):
        row = dict(tenor=tenor, O=O[i], B=B[i], A=A[i],
                   B_comp=Bc[i] if Bc else None, B_noncomp=Bn[i] if Bn else None,
                   A_comp=Ac[i] if Ac else None, A_noncomp=An[i] if An else None,
                   maturity_date=mats[i] if len(mats) >= 3 else None,
                   yield_pct=yld[i] if yld else None, cover_published=cover[i] if cover else None)
        row["cover_formula"] = published_ratio_formula(row["cover_published"], row["O"], row["B"], row["A"])
        r.rows.append(row)
    _quantity_checks(r, unit_floor=1e8, unit_cap=1e13)
    return r


def _quantity_checks(r: ParseResult, unit_floor: float, unit_cap: float, tol: float = 0.0) -> None:
    for row in r.rows:
        t = row["tenor"]
        if not (row["O"] > 0):
            r.blocking.append(f"{t}: non-positive offer")
        if row["A"] > row["B"] + tol:
            r.blocking.append(f"{t}: accepted exceeds tendered")
        for k in ("O", "B", "A"):
            if row[k] is not None and row[k] > 0 and not (unit_floor <= row[k] <= unit_cap):
                r.blocking.append(f"{t}: {k}={row[k]} outside plausible range")
        for tot, parts in (("B", ("B_comp", "B_noncomp")), ("A", ("A_comp", "A_noncomp"))):
            if row.get(parts[0]) is not None and row.get(parts[1]) is not None:
                if abs(row[parts[0]] + row[parts[1]] - row[tot]) > max(tol, 1e-6 * row[tot]) + 1e-9:
                    r.flags.append(f"{t}: competitive+noncompetitive != {tot}")


def parse_ug_invitation(text: str) -> ParseResult:
    text = deglue(text)
    r = ParseResult(classify_ug(text))
    if r.doc_type != "ug_bill_invitation":
        return r
    up = text.upper()
    ev = r.event
    m = re.search(r"ISSUE\s*(?:NO|NUMBER)\.?\s*:?\s*(\d{3,4})", up)
    ev["auction_no"] = int(m.group(1)) if m else None
    ad = re.search(r"AUCTION\s+DATE\s*:?\s*([^\n]{0,60})", up)
    ev["auction_date"] = first_date(ad.group(1)) if ad else None
    sd = re.search(r"(?:SETTLEMENT|VALUE|ISSUE)\s+DATE\s*:?\s*([^\n]{0,60})", up)
    ev["settlement_date"] = first_date(sd.group(1)) if sd else None
    dl = re.search(r"SUBMISSION\s+DEADLINE[\s\S]{0,300}?BY\s+([\d.:]+\s*(?:AM|PM|A\.M\.|P\.M\.)?)\s*,?\s*([^\n]{0,60})", up)
    ev["deadline_time_text"] = dl.group(1).strip() if dl else None
    ev["deadline_date"] = first_date(dl.group(2)) if dl else ev.get("auction_date")
    # publication date: last date in the document (above MANAGEMENT), date only
    cands = [first_date(x) for x in re.findall(rf"(?:{WEEKDAY},?\s*)?[^\n]{{0,40}}\d{{4}}", up[-500:])]
    cands = [c for c in cands if c]
    ev["notice_date"] = cands[-1] if cands else None
    offers = {}
    raw = {}
    for tenor in (91, 182, 364):
        mm = re.search(rf"\b{tenor}\s*-?\s*DAYS?\b[^\n\d]*([\d,]{{7,}})\s*(?:/=)?", up)
        if mm:
            offers[tenor] = float(mm.group(1).replace(",", ""))
            raw[tenor] = mm.group(0).strip()
    tot = re.search(r"(?:TOTAL|OFFERING\s+AMOUNT|MATURITIES\s*\(DAYS\)\s*:?)[^\n\d]*([\d,]{7,})\s*/=", up)
    ev["printed_total"] = float(tot.group(1).replace(",", "")) if tot else None
    r.raw.update({f"offer_{k}": v for k, v in raw.items()})
    if len(offers) < 3:
        # an invitation may legitimately omit a tenor; record which are present
        r.flags.append(f"offers found for tenors {sorted(offers)}")
    if not offers:
        r.blocking.append("no tenor offers found")
        return r
    for tenor, val in offers.items():
        r.rows.append(dict(tenor=tenor, O_announced=val))
    s = sum(offers.values())
    if ev["printed_total"] is not None and abs(ev["printed_total"] - s) > 1:
        r.flags.append(f"printed total {ev['printed_total']:.0f} != tenor sum {s:.0f}")
    return r


# =========================================================================== Kenya
def classify_ke(text: str) -> str:
    up = text.upper()
    if re.search(r"RESULTS\s+OF\s+(?:THE\s+)?(?:91|182|364)", up) and re.search(r"AMOUNT\s+OFFERED|OFFERED", up):
        return "ke_bill_result"
    if not up.strip():
        return "ke_empty_text"
    return "ke_unclassified"


def _ke_row(text, label, start=0, end=None):
    """Return (values, raw); values keep the trailing TOTAL column if present (n = 3 or 4).

    The label must be followed (after an optional unit in parentheses) directly by a number, so
    narrative sentences such as "bids received was 194 amounting to ..." never match.
    """
    rest, pos = line_after(text, label + r"(?:\s*\([^)\n]*\))?(?=[ \t:]*\d)", start, end)
    if rest is None:
        return None, None, -1
    v = nums(rest)
    return v, rest.strip(), pos


def parse_ke_result(text: str) -> ParseResult:
    r = ParseResult(classify_ke(text))
    if r.doc_type != "ke_bill_result":
        return r
    up = text.upper()
    ev = r.event
    secC = re.search(r"^\s*C\.\s*NEXT\s+TREASURY\s+BILLS?", text, re.I | re.M)
    endA = secC.start() if secC else len(text)
    head = re.search(r"RESULTS\s+OF[^\n]*?ISSUES?\s+(?:NOS?\.?\s*)?([^\n]*)", up)
    hl = head.group(0) if head else ""
    r.raw["heading"] = hl.strip()
    iss = re.findall(r"(\d{3,4})\s*/\s*0?(91|182|364)", hl)
    ev["issues"] = {int(t): int(n) for n, t in iss}
    dm = re.search(r"DATED\s*([0-9/.\- ]{6,12})", hl)
    ev["value_date"] = first_date(dm.group(1)) if dm else None
    # which tenors are present (2016-era notices may only carry 182/364 or 91/182/364)
    # Tenors issued: from the heading's issue numbers ("2206/91 & 2116/364"). Older notices keep a 182-day
    # column filled with "-" when that bill was not offered, so column headers are not reliable.
    if ev["issues"]:
        present = sorted(ev["issues"])
    else:
        present = [t for t in (91, 182, 364) if re.search(rf"\b{t}\s*-?\s*DAYS?\b", up[:endA][:3000])]
    ev["tenors_present"] = present
    O, Oraw, _ = _ke_row(text, r"Amount\s+Offered", 0, endA)
    B, Braw, _ = _ke_row(text, r"(?:Bids\s+Received|Amount\s+(?:Applied|Tendered|Received))", 0, endA)
    A, Araw, pa = _ke_row(text, r"(?:Total\s+)?Amount\s+Accepted", 0, endA)
    Ac, _, _ = _ke_row(text, r"Of\s+which\s*:?\s*Competitive(?:\s+bids)?", max(pa, 0), endA)
    An, _, _ = _ke_row(text, r":?\s*Non[\s-]*competitive(?:\s+bids)?", max(pa, 0), endA)
    perf, _, _ = _ke_row(text, r"Performance\s+Rate", 0, endA)
    cover, craw, _ = _ke_row(text, r"Bid[\s-]*to[\s-]*Cover(?:\s+Ratio)?", 0, endA)
    red, rraw, _ = _ke_row(text, r"Rollover\s*/\s*Redemptions?", 0, endA)
    war, _, _ = _ke_row(text, r"Weighted\s+Average\s+Interest\s+Rate\s+of(?:\s+accepted\s+bids)?", 0, endA)
    if war is not None and len(war) < len(present):
        # rates on the next line (layout wraps the label)
        m = re.search(r"Weighted\s+Average\s+Interest\s+Rate\s+of[^\n]*\n([^\n]*)", text[:endA], re.I)
        war = nums(m.group(1)) if m else war
    due_line, _ = line_after(text[:endA], r"Due\s+Date")
    dues = [to_date(m, "dmy") for m in DATE_NUM.finditer(due_line)] if due_line else []
    r.raw.update(offered=Oraw, bids=Braw, accepted=Araw, cover=craw, redemptions=rraw,
                 due_date=due_line.strip() if due_line else None)
    k = len(present)
    if k == 0:
        r.blocking.append("no tenor columns detected")
        return r
    for label, v in (("offered", O), ("bids", B), ("accepted", A)):
        if v is None or len(v) < k:
            r.blocking.append(f"missing {label} row")
    for key in ("offered", "bids", "accepted"):
        if r.raw.get(key) and BAD_NUM.search(r.raw[key] or ""):
            r.blocking.append(f"malformed number in {key}")
    if r.blocking:
        return r
    totals = {}
    for name, v in (("O", O), ("B", B), ("A", A)):
        if len(v) >= k + 1:
            totals[name] = v[k]
            if abs(sum(v[:k]) - v[k]) > 0.011 * k + 1e-9:  # two-decimal million rounding
                r.flags.append(f"{name}: tenor sum {sum(v[:k]):.2f} != printed total {v[k]:.2f}")
    ev["printed_totals"] = totals
    ev["reported_redemptions_total"] = red[k] if red and len(red) > k else (red[-1] if red else None)
    for i, t in enumerate(present):
        row = dict(tenor=t, O=O[i], B=B[i], A=A[i], A_comp=Ac[i] if Ac and len(Ac) > i else None,
                   A_noncomp=An[i] if An and len(An) > i else None, perf_published=perf[i] if perf and len(perf) > i else None,
                   cover_published=cover[i] if cover and len(cover) > i else None,
                   yield_pct=war[i] if war and len(war) > i and war[i] < 40 else None,
                   redemptions=red[i] if red and len(red) > i else None, issue_no=ev["issues"].get(t),
                   maturity_date=dues[i] if len(dues) == k else None)
        row["cover_formula"] = published_ratio_formula(row["cover_published"], row["O"], row["B"], row["A"])
        r.rows.append(row)
    _quantity_checks(r, unit_floor=1, unit_cap=1e6, tol=0.02)
    # next auction (section C): announced offer, closure date, announced redemptions
    if secC:
        tc = text[secC.start():]
        nh = re.search(r"NEXT\s+TREASURY\s+BILLS?\s+AUCTIONS?[^\n]*", tc, re.I)
        nl = nh.group(0).upper() if nh else ""
        nx = {}
        nx["issues"] = {int(t): int(n) for n, t in re.findall(r"(\d{3,4})\s*/\s*0?(91|182|364)", nl)}
        dm = re.search(r"DATED\s*([0-9/.\- ]{6,12})", nl)
        nx["value_date"] = first_date(dm.group(1)) if dm else None
        off, oraw, _ = _ke_row(tc, r"Offer\s+amount")
        nx["offer_raw"] = oraw
        nx["offers"] = off
        cl, _ = line_after(tc, r"Auction\s+Dates?\s*(?:&|and)\s*Bids?\s+Closure")
        nx["closure_date"] = first_date(cl) if cl else None
        an, _ = line_after(tc, r"Results\s+Announcement")
        nx["results_date"] = first_date(an) if an else None
        rd, _, _ = _ke_row(tc, r"Redemptions")
        nx["redemptions_total"] = rd[-1] if rd else None
        dd = re.search(r"by\s+([\d.:]+\s*(?:a\.?m\.?|p\.?m\.?))[^\n]*?(?:on\s+)?(?:" + WEEKDAY + r")?,?\s*([^\n]{0,40})", tc, re.I)
        nx["deadline_time_text"] = dd.group(1) if dd else None
        ev["next"] = nx
    # signature / release date: last date-like string near the end
    tail = re.sub(r"[ \t]+", " ", text).rstrip()[-700:]
    sig = None
    for rx, order in ((DATE_MDY, "mdy_name"), (DATE_DMY, "dmy_name")):
        ms = list(rx.finditer(tail))
        if ms:
            sig = to_date(ms[-1], order)
            break
    ev["signed_date"] = sig
    return r


# =========================================================================== Ghana
GH_TENOR_ROW = re.compile(
    r"\b(91|182|364)\s*[- ]?\s*DAY\s+(?:T\s*[/-]\s*)?BILLS?\s+GH\s*[^\s\d]?\s*([\d,.]+)\s+GH\s*[^\s\d]?\s*([\d,.]+)", re.I)


def classify_gh(text: str) -> str:
    up = text.upper()
    if re.search(r"RESULTS\s+OF\s+(?:THE\s+)?TENDER\s*\d+", up) and re.search(r"\b91\s*[- ]?\s*DAY", up):
        return "gh_bill_result"
    if re.search(r"RESULTS\s+OF\s+(?:THE\s+)?TENDER", up):
        return "gh_other_result"
    if not up.strip():
        return "gh_empty_text"
    return "gh_unclassified"


def gh_number(s: str) -> float | None:
    s = s.strip().rstrip(".")
    if re.fullmatch(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", s):
        return float(s.replace(",", ""))
    return None  # e.g. 1.141.12 -> requires review


def gh_bill_scope(label: str) -> list[int]:
    if not re.search(r"BILL", label) or re.search(r"YEAR|NOTE|BOND|FXR", label):
        return []
    return sorted({int(t) for t in re.findall(r"(?<!\d)(91|182|364)(?!\d)", label)})


def parse_gh_result(text: str) -> ParseResult:
    r = ParseResult(classify_gh(text))
    if r.doc_type != "gh_bill_result":
        return r
    up = text.upper()
    ev = r.event
    s2 = re.search(r"\b2\.?\s*SUMMARY\s+OF\s+TENDER", up)
    s3 = re.search(r"\b3\.?\s*TARGET\s+FOR\s+TENDER", up)
    sec1 = up[: s2.start()] if s2 else up[: s3.start()] if s3 else up
    head = re.search(r"RESULTS\s+OF\s+(?:THE\s+)?TENDER\s*(\d{3,4})\s+HELD\s+ON\s+([^\n]*?)(?:FOR\b|$)", sec1, re.M)
    r.raw["heading"] = head.group(0).strip() if head else None
    if not head:
        r.blocking.append("section-1 heading not found")
        return r
    ev["tender_no"] = int(head.group(1))
    held = DATE_DMY.search(head.group(2))
    ev["held_date"] = to_date(held, "dmy_name")
    iss = re.search(r"TO\s+BE\s+ISSUED\s+ON\s+([^\n]{0,40})", sec1)
    ev["settlement_date"] = first_date(iss.group(1)) if iss else None
    nn = re.search(r"NOTICE\s+TO\s+BANKS[^\n]*?NO\.?\s*([A-Z0-9/ -]+)", up)
    ev["notice_no"] = nn.group(1).strip() if nn else None
    if not ev["held_date"]:
        r.blocking.append("held date not parsed from section 1")
    # units: table heading must state millions
    ev["units_stated"] = bool(re.search(r"GH\s*[^\s\d]\s*\(\s*M\s*\)|MILLION", sec1))
    if not ev["units_stated"]:
        r.blocking.append("unit (millions) not stated in section 1")
    rows = {}
    for m in GH_TENOR_ROW.finditer(sec1):
        t = int(m.group(1))
        b, a = gh_number(m.group(2)), gh_number(m.group(3))
        r.raw[f"row_{t}"] = m.group(0)
        if b is None or a is None:
            r.blocking.append(f"{t}: malformed amount {m.group(2)!r}/{m.group(3)!r}")
            continue
        if t in rows:
            r.flags.append(f"{t}: duplicate tenor row in section 1")
            continue
        rows[t] = (b, a)
    other = re.findall(r"\b(\d+)\s*[- ]?\s*(?:YEAR|YR)\b[^\n]*GH", sec1)
    ev["other_securities_in_section1"] = len(other)
    tg = re.search(r"TARGET\s+FOR\s+([^\n:]*?)\s*:\s*GH\s*[^\s\d]?\s*([\d,.]+)\s*(MILLION)?", sec1)
    r.raw["target"] = tg.group(0).strip() if tg else None
    if not tg:
        r.blocking.append("section-1 target not found")
        return r
    scope = tg.group(1)
    ev["target_scope"] = re.sub(r"\s+", " ", scope).strip()
    # digit lookarounds, not \b: scopes such as "91AND182 T/BILL" (tender 1671) have no word boundary
    scope_tenors = gh_bill_scope(scope)
    ev["target_tenors"] = scope_tenors
    ev["target_bills_only"] = bool(scope_tenors)
    target = gh_number(tg.group(2))
    if target is None:
        r.blocking.append(f"malformed target {tg.group(2)!r}")
        return r
    ev["O_result"] = target
    if not ev["target_bills_only"]:
        r.blocking.append(f"target scope not bills-only: {ev['target_scope']}")
        return r
    if set(rows) != set(scope_tenors):
        # the combined target must cover exactly the maturities reported in section 1
        r.blocking.append(f"tenor rows {sorted(rows)} != target scope {scope_tenors}")
        return r
    for t in scope_tenors:
        b, a = rows[t]
        r.rows.append(dict(tenor=t, B=b, A=a))
        if a > b + 0.02:
            r.blocking.append(f"{t}: accepted exceeds tendered")
    # section 2 (previous tender) and section 3 (next target)
    if s2:
        sec2 = up[s2.start(): s3.start() if s3 else len(up)]
        pm = re.search(r"SUMMARY\s+OF\s+TENDER\s*(\d{3,4})\s+HELD\s+ON\s+([^\n]*)", sec2)
        bill_line = next((ln for ln in sec2.splitlines() if re.search(r"BILLS?\b", ln) and "MILLION" in ln), "")
        amts = re.findall(r"GH\s*[^\s\d]?\s*([\d,.]+)\s*MILLION", bill_line)
        ev["prev"] = dict(tender_no=int(pm.group(1)) if pm else None,
                          held_date=to_date(DATE_DMY.search(pm.group(2)), "dmy_name") if pm else None,
                          B_total=gh_number(amts[0]) if len(amts) > 0 else None,
                          A_total=gh_number(amts[1]) if len(amts) > 1 else None,
                          tenors=gh_bill_scope(bill_line.split("GH", 1)[0]),
                          raw=re.sub(r"\s+", " ", sec2[:400]))
    if s3:
        sec3 = up[s3.start(): s3.start() + 600]
        nm = re.search(r"TARGET\s+FOR\s+TENDER\s*(\d{3,4})", sec3)
        am = re.search(r"([^\n]*BILLS?)\s*GH\s*[^\s\d]?\s*([\d,.]+)\s*(MILLION)?", sec3)
        ev["next"] = dict(tender_no=int(nm.group(1)) if nm else None,
                          target=gh_number(am.group(2)) if am else None,
                          tenors=gh_bill_scope(am.group(1)) if am else [],
                          raw=re.sub(r"\s+", " ", sec3[:300]))
    tail = up[-500:]
    ms = list(DATE_DMY.finditer(tail))
    ev["signed_date"] = to_date(ms[-1], "dmy_name") if ms else None
    return r
