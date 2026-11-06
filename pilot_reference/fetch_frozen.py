"""Fetch public originals for replay, requiring a match to the pilot content hash."""
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from time import sleep
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parent
parser = ArgumentParser()
parser.add_argument("--group", action="append", choices=["UG", "UG_API", "KE", "GH", "UG_INV"])
parser.add_argument("--limit", type=int, help="Optional cap for smoke tests")
parser.add_argument("--workers", type=int, default=4)
args = parser.parse_args()
inventory = json.loads((root / "source_inventory.json").read_text(encoding="utf-8"))
items = [item for item in inventory if not args.group or item["group"] in args.group]
if args.limit is not None:
    items = items[:args.limit]

def fetch(item):
    dst = root / item["path"]
    if root not in dst.resolve().parents:
        return {"path": item["path"], "status": "failed", "detail": "unsafe path"}
    dst.parent.mkdir(exist_ok=True, parents=True)
    url = item["url"]
    host = urlsplit(url).hostname
    if host not in {"bou.or.ug", "www.centralbank.go.ke", "www.bog.gov.gh"}:
        return {"path": item["path"], "status": "failed", "detail": f"unexpected host {host}"}
    if dst.is_file():
        if sha256(dst.read_bytes()).hexdigest() == item["sha256"]:
            return {"path": item["path"], "status": "cached"}
        return {"path": item["path"], "status": "failed", "detail": "existing local hash mismatch"}
    parts = urlsplit(url)
    fetch_url = urlunsplit(parts._replace(path=quote(parts.path, safe="/%")))
    for attempt in range(3):
        try:
            req = Request(fetch_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=18) as response:
                if urlsplit(response.geturl()).hostname not in {"bou.or.ug", "www.centralbank.go.ke", "www.bog.gov.gh"}:
                    raise ValueError("Redirected off the expected official host")
                payload = response.read()
            actual = sha256(payload).hexdigest()
            if actual != item["sha256"]:
                return {"path": item["path"], "status": "failed", "detail": "remote hash mismatch", "observed_sha256": actual}
            temporary = dst.with_suffix(dst.suffix + ".part")
            temporary.write_bytes(payload)
            temporary.replace(dst)
            return {"path": item["path"], "status": "fetched"}
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            if attempt < 2:
                sleep(0.7 * 2 ** attempt)
    return {"path": item["path"], "status": "failed", "detail": detail}

with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 6))) as pool:
    results = list(pool.map(fetch, items))
(root / "last_fetch_report.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
failed = sum(row["status"] == "failed" for row in results)
print(f"{len(results) - failed}/{len(results)} originals verified")
raise SystemExit(1 if failed else 0)
