import requests

from treasury_auctions.fetch import SourceCache, expected_kind, safe_url, sniff


class FakeResp:
    def __init__(self, content, status=200, url=None, headers=None):
        self.content = content
        self.status_code = status
        self.url = url
        self.headers = headers or {"Content-Type": "application/pdf"}


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.headers = {}

    def get(self, url, timeout=None, allow_redirects=True):
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        r.url = r.url or url
        return r


PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF"
U = "https://bou.or.ug/uploads/x.pdf"


def make(tmp_path, responses, **kw):
    c = SourceCache(tmp_path, min_interval=0, **kw)
    c.session = FakeSession(responses)
    return c


def test_clean_fetch_checksum_and_cache_reuse(tmp_path):
    c = make(tmp_path, [FakeResp(PDF)])
    r = c.get(U)
    assert r.status == "fetched" and r.media_kind == "pdf" and r.bytes == len(PDF)
    c.save_index()
    c2 = make(tmp_path, [])
    r2 = c2.get(U)  # no network call needed
    assert r2.status == "cached" and r2.sha256 == r.sha256 and c2.session.calls == 0


def test_html_masquerading_as_pdf_is_failure(tmp_path):
    c = make(tmp_path, [FakeResp(b"<!DOCTYPE html><html><body>Not found</body></html>", headers={"Content-Type": "text/html"})])
    r = c.get(U)
    assert r.status == "failed" and "content mismatch" in r.detail
    assert c.read(U) is None


def test_offline_miss_is_explicit(tmp_path):
    c = make(tmp_path, [], offline=True)
    assert c.get(U).status == "missing_offline"


def test_non_official_host_and_redirect_rejected(tmp_path):
    c = make(tmp_path, [FakeResp(PDF, url="https://evil.example.com/x.pdf")])
    assert c.get("https://example.com/x.pdf").status == "failed"
    r = c.get(U)
    assert r.status == "failed" and "redirected" in r.detail


def test_bounded_retry_then_success(tmp_path):
    c = make(tmp_path, [requests.ConnectionError("reset"), FakeResp(b"", status=503), FakeResp(PDF)], retries=3)
    import treasury_auctions.fetch as f

    orig = f.time.sleep
    f.time.sleep = lambda s: None
    try:
        r = c.get(U)
    finally:
        f.time.sleep = orig
    assert r.status == "fetched" and c.session.calls == 3


def test_retries_exhausted_reports_failure(tmp_path):
    import treasury_auctions.fetch as f

    c = make(tmp_path, [requests.Timeout("t")] * 3, retries=3)
    orig = f.time.sleep
    f.time.sleep = lambda s: None
    try:
        r = c.get(U)
    finally:
        f.time.sleep = orig
    assert r.status == "failed" and "Timeout" in r.detail


def test_truncated_transfer_retried(tmp_path):
    import treasury_auctions.fetch as f

    c = make(tmp_path, [FakeResp(PDF[:10], headers={"Content-Length": str(len(PDF))}), FakeResp(PDF)], retries=2)
    orig = f.time.sleep
    f.time.sleep = lambda s: None
    try:
        r = c.get(U)
    finally:
        f.time.sleep = orig
    assert r.status == "fetched" and r.bytes == len(PDF)


def test_kind_detection_and_url_encoding():
    assert expected_kind("https://x/a/b.XLSX.pdf") == "pdf"  # mixed extension: final suffix wins
    assert expected_kind("https://x/a.docx") == "zip"
    assert sniff(PDF) == "pdf" and sniff(b"PK\x03\x04....") == "zip" and sniff(b"\xd0\xcf\x11\xe0") == "ole"
    u = safe_url("https://www.centralbank.go.ke/uploads/91_day/123_RESULTS 2601-091 DATED 28.10. 2024.pdf")
    assert " " not in u and "%20" in u


def test_duplicate_content_stored_once(tmp_path):
    c = make(tmp_path, [FakeResp(PDF), FakeResp(PDF)])
    a = c.get(U)
    b = c.get("https://bou.or.ug/uploads/y.pdf")
    assert a.sha256 == b.sha256
    assert len(list((tmp_path / "blobs").rglob("*"))) == 2  # one shard dir + one blob
