"""Document text extraction with provenance.

Order (handoff Section 5): native text layer first (``pdftotext -layout`` when
installed, PyMuPDF otherwise), structured XML for DOCX, cell values for XLSX, and
targeted OCR of a rendered page only when the text layer lacks the auction table.
Every result records the method, tool version, page and OCR confidence.
OCR output is cached by content hash so unchanged bytes are never re-OCRed.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

os.environ.setdefault("OMP_THREAD_LIMIT", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")


@dataclass
class Extracted:
    text: str
    method: str  # pdftotext-layout | pymupdf | docx-xml | xlsx-cells | ocr-rapidocr | html | none
    tool: str
    pages: int | None = None
    ocr_page: int | None = None
    ocr_mean_conf: float | None = None
    ocr_min_conf: float | None = None
    notes: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def pdftotext_version() -> str | None:
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "-v"], capture_output=True, text=True, timeout=10)
        line = (out.stderr or out.stdout).splitlines()[0]
        return line.strip()
    except (OSError, subprocess.SubprocessError, IndexError):
        return None


def normalize_text(t: str) -> str:
    t = t.replace(" ", " ").replace("–", "-").replace("—", "-").replace("−", "-")
    t = t.replace("’", "'").replace("\r\n", "\n").replace("\f", "\n")
    return t


def pdf_text(payload: bytes) -> Extracted:
    """Primary extraction: PyMuPDF text layer in reading order (portable, pip-installable)."""
    import pymupdf

    doc = pymupdf.open(stream=payload, filetype="pdf")
    text = "\n".join(page.get_text("text", sort=True) for page in doc)
    return Extracted(normalize_text(text), "pymupdf", f"pymupdf {pymupdf.__version__}", pages=doc.page_count)


def pdf_text_plumber(payload: bytes) -> Extracted | None:
    """Independent second extraction with pdfminer.six (via pdfplumber): a different PDF parser from PyMuPDF.

    CBK notices embed a literal space after the leading digit of many amounts ("1 0,000.00"); for this
    audit engine only, one space between a lone leading digit and a following thousands group is removed.
    Digits themselves are never altered.
    """
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        with pdfplumber.open(io.BytesIO(payload)) as pdf:
            txt = "\n".join((p.extract_text(x_tolerance=3) or "") for p in pdf.pages)
            ver = pdfplumber.__version__
    except Exception:  # noqa: BLE001
        return None
    return Extracted(normalize_text(repair_split_digits(txt)), "pdfplumber", f"pdfplumber {ver}")


SPLIT_DIGIT = re.compile(r"(?<![\d,.])(\d) (?=(?:\d{0,2},\d{3})|(?:,\d{3})|(?:\d{1,2}\.\d{2}\b))")


def repair_split_digits(txt: str) -> str:
    """Join a lone leading digit to the rest of its amount ("1 0,000.00" -> "10,000.00"; "5 15.21" -> "515.21")."""
    return SPLIT_DIGIT.sub(r"\1", txt)


def pdf_text_alt(payload: bytes) -> Extracted | None:
    """Fallback second extraction (Poppler/Xpdf ``pdftotext -layout``); found to shift rows on some layouts."""
    ver = pdftotext_version()
    if not ver:
        return None
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "doc.pdf"
        dst = Path(tmp) / "doc.txt"
        src.write_bytes(payload)
        try:
            r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(src), str(dst)], capture_output=True,
                               timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
        if r.returncode != 0 or not dst.is_file():
            return None
        return Extracted(normalize_text(dst.read_text(encoding="utf-8", errors="replace")), "pdftotext-layout", ver)


def pdf_page_count(payload: bytes) -> int:
    import pymupdf

    return pymupdf.open(stream=payload, filetype="pdf").page_count


def docx_text(payload: bytes) -> Extracted:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find("w:body", ns)
    lines = []
    # paragraphs outside tables, then table rows with cells joined by two spaces
    for child in body:
        tag = child.tag.split("}")[1]
        if tag == "p":
            txt = "".join(t.text or "" for t in child.iter(f"{{{ns['w']}}}t")).strip()
            if txt:
                lines.append(txt)
        elif tag == "tbl":
            for tr in child.iter(f"{{{ns['w']}}}tr"):
                cells = ["".join(t.text or "" for t in tc.iter(f"{{{ns['w']}}}t")).strip()
                         for tc in tr.findall("w:tc", ns)]
                lines.append("   ".join(c for c in cells if c))
    return Extracted(normalize_text("\n".join(lines)), "docx-xml", "zipfile+ElementTree")


def xlsx_text(payload: bytes) -> Extracted:
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(payload), data_only=True, read_only=True)
    lines = []
    for sh in wb.worksheets:
        lines.append(f"## SHEET {sh.title}")
        for row in sh.iter_rows(values_only=True):
            vals = [str(v) for v in row if v is not None and str(v).strip()]
            if vals:
                lines.append("   ".join(vals))
    return Extracted("\n".join(lines), "xlsx-cells", f"openpyxl {openpyxl.__version__}")


def html_text(payload: bytes) -> Extracted:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(payload.decode("utf-8", "replace"), "lxml")
    lines = []
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if any(cells):
            lines.append("   ".join(c for c in cells if c))
    text = "\n".join(lines) or soup.get_text("\n")
    return Extracted(normalize_text(text), "html", "beautifulsoup4")


# ------------------------------------------------------------------------- OCR
@lru_cache(maxsize=1)
def _ocr_engine():
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None
    return RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)


def ocr_available() -> bool:
    return _ocr_engine() is not None


def ocr_tool() -> str:
    try:
        from importlib.metadata import version

        return f"rapidocr-onnxruntime {version('rapidocr-onnxruntime')}"
    except Exception:  # noqa: BLE001
        return "rapidocr-onnxruntime"


def boxes_to_lines(result) -> list[tuple[str, float]]:
    """Group OCR word boxes into visual rows by vertical overlap; join left-to-right.

    Cells on one row are separated by three spaces so table parsers can split them.
    """
    items = []
    for box, text, score in result or []:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        items.append((min(ys), max(ys), min(xs), max(xs), text, float(score)))
    items.sort(key=lambda r: ((r[0] + r[1]) / 2, r[2]))
    rows: list[list] = []
    for it in items:
        cy = (it[0] + it[1]) / 2
        h = it[1] - it[0]
        for row in rows:
            ry0, ry1 = row[0]
            if abs(cy - (ry0 + ry1) / 2) < 0.5 * max(h, ry1 - ry0):
                row[1].append(it)
                row[0] = (min(ry0, it[0]), max(ry1, it[1]))
                break
        else:
            rows.append([(it[0], it[1]), [it]])
    rows.sort(key=lambda r: r[0][0])
    out = []
    for _, cells in rows:
        cells.sort(key=lambda c: c[2])
        out.append(("   ".join(c[4] for c in cells), min(c[5] for c in cells)))
    return out


def ocr_pdf_page(payload: bytes, page: int = 0, dpi: int = 220, cache_dir: Path | None = None,
                 digest: str | None = None, top_fraction: float | None = None) -> Extracted:
    crop = f"_t{int(top_fraction * 100)}" if top_fraction else ""
    key = f"{digest}_p{page}_d{dpi}{crop}.json" if digest else None
    if cache_dir and key and (cache_dir / key).is_file():
        d = json.loads((cache_dir / key).read_text(encoding="utf-8"))
        return Extracted(d["text"], "ocr-rapidocr", d["tool"], ocr_page=page, ocr_mean_conf=d["mean"],
                         ocr_min_conf=d["min"], notes=["ocr cache hit"])
    engine = _ocr_engine()
    if engine is None:
        return Extracted("", "none", "no OCR engine installed", notes=["install extra [ocr]"])
    import numpy as np
    import pymupdf

    doc = pymupdf.open(stream=payload, filetype="pdf")
    pg = doc[page]
    clip = None
    if top_fraction:
        r = pg.rect
        clip = pymupdf.Rect(r.x0, r.y0, r.x1, r.y0 + r.height * top_fraction)
    pix = pg.get_pixmap(dpi=dpi, clip=clip)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    result, _ = engine(img)
    lines = boxes_to_lines(result)
    confs = [c for _, c in lines]
    text = normalize_text("\n".join(t for t, _ in lines))
    mean = round(float(sum(confs) / len(confs)), 4) if confs else None
    mn = round(float(min(confs)), 4) if confs else None
    if cache_dir and key:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / key).write_text(json.dumps({"text": text, "tool": ocr_tool(), "mean": mean, "min": mn}),
                                     encoding="utf-8")
    return Extracted(text, "ocr-rapidocr", ocr_tool(), ocr_page=page, ocr_mean_conf=mean, ocr_min_conf=mn)


def extract(payload: bytes, kind: str, name: str = "") -> Extracted:
    low = name.lower()
    if kind == "pdf":
        return pdf_text(payload)
    if kind == "zip" and (low.endswith(".xlsx") or b"xl/workbook" in payload[:4000] or b"xl/" in payload[:2000]):
        return xlsx_text(payload)
    if kind == "zip":
        try:
            return docx_text(payload)
        except KeyError:
            return xlsx_text(payload)
    if kind == "html":
        return html_text(payload)
    return Extracted("", "none", "unsupported", notes=[f"unsupported media kind {kind}"])


NUMBER = re.compile(r"(?<![\w/.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w/])")
