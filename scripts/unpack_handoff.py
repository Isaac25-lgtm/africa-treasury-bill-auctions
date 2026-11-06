"""Extract the embedded pilot replay bundle from the handoff Markdown (verbatim from handoff Section 16)."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

handoff = Path(sys.argv[1]).read_text(encoding="utf-8")
out = Path(sys.argv[2]).resolve()
match = re.search(
    r"(?ms)^<!-- PILOT_BUNDLE_START -->\s*\n```text\s*\n(.*?)^\s*```\s*\n<!-- PILOT_BUNDLE_END -->",
    handoff,
)
if match is None:
    raise SystemExit("Embedded replay bundle not found")
blob = gzip.decompress(base64.b64decode("".join(match[1].split()), validate=True))
header = re.search(r"(?m)^Bundle JSON SHA256: `([a-f0-9]{64})`$", handoff)
if header is None or hashlib.sha256(blob).hexdigest() != header[1]:
    raise SystemExit("Embedded replay bundle SHA256 mismatch")
bundle = json.loads(blob)
out.mkdir(parents=True, exist_ok=True)
for name, value in bundle["files"].items():
    destination = (out / name).resolve()
    if out not in destination.parents:
        raise ValueError(name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_text(encoding="utf-8") != value:
        raise FileExistsError(destination)
    destination.write_text(value, encoding="utf-8")
print(f"Extracted {len(bundle['files'])} files into {out}")
