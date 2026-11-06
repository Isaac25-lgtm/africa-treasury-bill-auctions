from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from dateutil.parser import parse
import re, json, subprocess, sys
import pandas as pd
root=Path(__file__).resolve().parent
d=root/'GH';d.mkdir(exist_ok=True)
def parse_doc(args):
    t,url,post,posted=args
    body=subprocess.run(['pdftotext','-layout',str(t),'-'],capture_output=True,text=True,timeout=10).stdout
    date_raw=re.search(r'HELD ON\s+(\d{1,2}(?:ST|ND|RD|TH)?\s+[A-Z]+\.?\s+20\d{2})',body,re.I)
    if not date_raw:return
    held=parse(date_raw.group(1).replace('.',''),dayfirst=True).date().isoformat()
    body=re.split(r'\bSUMMARY OF TENDER\b|\bTARGET FOR TENDER\b',body,maxsplit=1,flags=re.I)[0]
    target=re.search(r'TARGET FOR 91.*?[:\s]+GH[¢₵C]\s*([\d,.]+)(?:[ \t]+MILLION)?',body,re.I)
    if not target or 'GH¢ (M)' not in re.sub(r'[ \t]+',' ',body) and 'MILLION' not in target.group(0).upper():return
    tenors=[]
    for m in (91,182,364):
        z=re.search(rf'\b{m}\s*[- ]?\s*DAY\s+(?:T\s*[/-]\s*)?BILLS?\s+GH[¢₵C]\s*([\d,.]+)\s+GH[¢₵C]\s*([\d,.]+)',body,re.I)
        if not z:return
        try: tenors.append([float(z.group(i).replace(',','')) for i in (1,2)])
        except ValueError:return
    offer=float(target.group(1).replace(',',''))
    b,a=map(sum,zip(*tenors))
    if not (0<a<=b+.1 and offer>0):return
    return {'country':'GH','date':held,'tenor':'total','offered':offer,'bids':b,'accepted':a,'source':url,'posted':posted,'post':post}

if __name__ == "__main__":
    inventory = json.loads((root / "source_inventory.json").read_text(encoding="utf-8"))
    jobs = []
    for item in inventory:
        if item["group"] != "GH":
            continue
        path = root / item["path"]
        if path.is_file():
            jobs.append((path, item["url"], item["post"], item["posted"]))
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(filter(None, pool.map(parse_doc, jobs)))
    print(f"Parsed {len(rows)} candidates from {len(jobs)} present source documents")
    if not rows:
        raise SystemExit("No records parsed")
    df = pd.DataFrame(rows)
    ambiguous = df.loc[df.duplicated("date", keep=False), ["date", "source"]]
    if not ambiguous.empty:
        print("Legacy date collisions, to audit in the new pipeline:")
        print(ambiguous.to_string(index=False))
    # Retain original pilot tie handling for exact replay only.
    reference = pd.read_csv(root / "cached_exploratory" / "ghana.csv", usecols=["date", "source"])
    retained = set(zip(reference.date, reference.source))
    df["legacy_preferred"] = [(date, source) in retained for date, source in zip(df.date, df.source)]
    df = df.sort_values(["date", "legacy_preferred", "source"], ascending=[True, False, True])
    df = df.drop_duplicates("date").drop(columns="legacy_preferred")
    df.to_csv(root / "ghana.csv", index=False)
    print(df.groupby(df.date.str[:4]).size().to_dict())
