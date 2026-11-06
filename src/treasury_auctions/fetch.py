"""Idempotent, checksum-verified download cache.

Design rules (handoff Phase A.5):
* bytes are stored once under ``cache/blobs/<sha256[:2]>/<sha256>`` and never edited;
* an index maps URL -> retrieval record (time, status, hash, media type, bytes);
* HTML error pages masquerading as documents are failures, not successes;
* only official hosts are contacted; redirects off those hosts are rejected;
* ``offline=True`` answers from the cache only and reports misses explicitly.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import requests

from .config import OFFICIAL_HOSTS, USER_AGENT

MAGIC = {
    "pdf": (b"%PDF",),
    "zip": (b"PK\x03\x04",),  # docx / xlsx
    "ole": (b"\xd0\xcf\x11\xe0",),  # legacy .xls / .doc
}


def sniff(payload: bytes) -> str:
    head = payload[:16]
    for kind, sigs in MAGIC.items():
        if any(head.startswith(s) for s in sigs):
            return kind
    if b"%PDF" in payload[:1024]:
        return "pdf"
    text = payload[:2048].lstrip().lower()
    if text.startswith(b"<!doctype html") or text.startswith(b"<html") or b"<html" in text[:600]:
        return "html"
    if text.startswith(b"<?xml"):
        return "xml"
    if text.startswith(b"{") or text.startswith(b"["):
        return "json"
    if text.startswith(b"{\\rtf"):
        return "rtf"
    return "unknown"


def expected_kind(url: str) -> str | None:
    path = urlsplit(url).path.lower()
    for ext, kind in ((".pdf", "pdf"), (".docx", "zip"), (".xlsx", "zip"), (".xls", "ole"), (".doc", "ole")):
        if path.endswith(ext):
            return kind
    return None


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=quote(parts.path, safe="/%:@!$&'()*+,;=-._~")))


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass
class FetchRecord:
    url: str
    status: str  # fetched | cached | failed | missing_offline
    sha256: str | None = None
    bytes: int | None = None
    media_kind: str | None = None
    content_type: str | None = None
    retrieved_utc: str | None = None
    http_status: int | None = None
    detail: str | None = None
    final_url: str | None = None


class SourceCache:
    def __init__(self, cache_dir: Path, offline: bool = False, timeout: tuple[float, float] = (15, 60),
                 retries: int = 3, min_interval: float = 0.25):
        self.dir = Path(cache_dir)
        self.blobs = self.dir / "blobs"
        self.index_path = self.dir / "index.json"
        self.offline = offline
        self.timeout = timeout
        self.retries = retries
        self.min_interval = min_interval
        self._lock = threading.Lock()
        self._last = 0.0
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.index: dict[str, dict] = {}
        if self.index_path.is_file():
            self.index = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    # ----------------------------------------------------------------- storage
    def blob_path(self, digest: str) -> Path:
        return self.blobs / digest[:2] / digest

    def read(self, url: str) -> bytes | None:
        rec = self.index.get(url)
        if not rec or not rec.get("sha256"):
            return None
        p = self.blob_path(rec["sha256"])
        if not p.is_file():
            return None
        payload = p.read_bytes()
        if sha256(payload) != rec["sha256"]:
            raise RuntimeError(f"cache corruption for {url}")
        return payload

    def _store(self, payload: bytes) -> str:
        digest = sha256(payload)
        p = self.blob_path(digest)
        if not p.is_file():
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".part")
            tmp.write_bytes(payload)
            tmp.replace(p)
        return digest

    def save_index(self) -> None:
        with self._lock:
            tmp = self.index_path.with_suffix(".part")
            tmp.write_text(json.dumps(self.index, indent=1, sort_keys=True), encoding="utf-8")
            tmp.replace(self.index_path)

    # ----------------------------------------------------------------- network
    def _throttle(self) -> None:
        with self._lock:
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def get(self, url: str, kind: str | None = None, refresh: bool = False) -> FetchRecord:
        """Return a record; bytes are in the cache when status is fetched/cached."""
        host = urlsplit(url).hostname
        if host not in OFFICIAL_HOSTS:
            return FetchRecord(url, "failed", detail=f"non-official host {host}")
        if not refresh and self.read(url) is not None:
            rec = self.index[url]
            return FetchRecord(**{**{k: rec.get(k) for k in FetchRecord.__dataclass_fields__}, "status": "cached"})
        if self.offline:
            return FetchRecord(url, "missing_offline", detail="not in cache and offline mode")
        want = kind or expected_kind(url)
        detail = None
        for attempt in range(self.retries):
            self._throttle()
            try:
                r = self.session.get(safe_url(url), timeout=self.timeout, allow_redirects=True)
                final_host = urlsplit(r.url).hostname
                if final_host not in OFFICIAL_HOSTS:
                    return FetchRecord(url, "failed", detail=f"redirected off official host to {final_host}")
                if r.status_code == 404:
                    return self._fail(url, r.status_code, "HTTP 404")
                if r.status_code >= 500 or r.status_code == 429:
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                if r.status_code != 200:
                    return self._fail(url, r.status_code, f"HTTP {r.status_code}")
                payload = r.content
                declared = r.headers.get("Content-Length")
                if declared and declared.isdigit() and int(declared) != len(payload) and "gzip" not in r.headers.get("Content-Encoding", ""):
                    raise OSError(f"truncated transfer {len(payload)} of {declared}")
                got = sniff(payload)
                note = None
                if want and got != want:
                    # an HTML/unknown body where a document was expected is an error page: fail.
                    # a different *document* type (e.g. PDF bytes behind an .xls link) is kept and noted.
                    if got not in ("pdf", "zip", "ole") or want in ("json", "html"):
                        return self._fail(url, r.status_code, f"content mismatch: expected {want}, got {got}",
                                          content_type=r.headers.get("Content-Type"))
                    note = f"extension suggests {want}, content is {got}"
                digest = self._store(payload)
                rec = FetchRecord(url, "fetched", digest, len(payload), got, r.headers.get("Content-Type"),
                                  datetime.now(UTC).isoformat(timespec="seconds"), r.status_code, detail=note,
                                  final_url=r.url)
                with self._lock:
                    self.index[url] = asdict(rec)
                return rec
            except (requests.RequestException, OSError) as exc:
                detail = f"{type(exc).__name__}: {exc}"[:300]
                time.sleep(min(8.0, 0.8 * 2**attempt))
        return self._fail(url, None, detail or "unknown failure")

    def _fail(self, url, code, detail, content_type=None) -> FetchRecord:
        rec = FetchRecord(url, "failed", http_status=code, detail=detail, content_type=content_type,
                          retrieved_utc=datetime.now(UTC).isoformat(timespec="seconds"))
        with self._lock:
            # keep a prior good copy if one exists; only record the failure otherwise
            if url not in self.index or not self.index[url].get("sha256"):
                self.index[url] = asdict(rec)
        return rec

    def get_many(self, urls: list[str], workers: int = 4, kind: str | None = None) -> list[FetchRecord]:
        workers = max(1, min(workers, 6))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            out = list(pool.map(lambda u: self.get(u, kind=kind), urls))
        self.save_index()
        return out


def absolutize(base: str, link: str) -> str:
    return urljoin(base, link)
