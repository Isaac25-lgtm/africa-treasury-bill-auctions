"""Format manuscript/references.bib as a sorted author-year reference list (JSON for the docx builder)."""
import json
import re
import sys

bib_path, out_path = sys.argv[1], sys.argv[2]
t = open(bib_path, encoding="utf-8").read()


def clean(s: str) -> str:
    s = s.replace(r"{\c{c}}", "ç").replace(r"\c{c}", "ç").replace(r"\&", "&")
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\s+", " ", s)
    return re.sub(r"[{}]", "", s).strip()


def fields(body: str) -> dict:
    out, i = {}, 0
    for m in re.finditer(r"(\w+)\s*=\s*\{", body):
        if m.start() < i:
            continue
        depth, j = 1, m.end()
        while depth and j < len(body):
            depth += {"{": 1, "}": -1}.get(body[j], 0)
            j += 1
        out[m.group(1).lower()] = clean(body[m.end():j - 1])
        i = j
    return out


def authors(a: str) -> str:
    out = []
    for p in [x.strip() for x in a.split(" and ")]:
        if "," in p:
            last, first = [x.strip() for x in p.split(",", 1)]
            ini = " ".join(w[0] + "." for w in re.split(r"[\s-]+", first) if w)
            out.append(f"{last}, {ini}")
        else:
            out.append(p)
    return out[0] if len(out) == 1 else ", ".join(out[:-1]) + " and " + out[-1]


def join(*xs):
    return ", ".join(x for x in xs if x)


refs = []
for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", t, re.S):
    typ, _, body = m.groups()
    f = fields(body)
    a, y, ti = authors(f.get("author", "")), f.get("year", "n.d."), f.get("title", "")
    pages = f.get("pages", "").replace("--", "–")
    if typ == "article":
        vol = f.get("volume", "") + (f"({f['number']})" if f.get("number") else "")
        r = dict(pre=f"{a} ({y}). {ti}. ", ital=f.get("journal", ""), post=", " + join(vol, pages) + ".")
    elif typ == "incollection":
        r = dict(pre=f"{a} ({y}). {ti}. In ", ital=f.get("booktitle", ""),
                 post=". " + join(f.get("series", ""), f.get("number", ""), pages and "pp. " + pages,
                                  f.get("publisher", "")) + ".")
    elif typ == "book":
        r = dict(pre=f"{a} ({y}). ", ital=ti,
                 post=". " + join(f.get("series", ""), f.get("publisher", ""), f.get("address", "")) + ".")
    elif typ == "techreport":
        r = dict(pre=f"{a} ({y}). ", ital=ti,
                 post=". " + join(f.get("institution", ""), (f.get("type", "") + " " + f.get("number", "")).strip()) + ".")
    else:
        r = dict(pre=f"{a} ({y}). ", ital=ti, post=". " + join(f.get("howpublished", ""), f.get("note", "")) + ".")
    if f.get("doi"):
        r["post"] += f" https://doi.org/{f['doi']}"
    elif f.get("url"):
        r["post"] += f" {f['url']}"
    r["post"] = re.sub(r"\.\s*\.", ".", r["post"].replace(", .", "."))
    if r["post"] in (". .", "."):
        r["post"] = "."
    r["sort"] = (a + y).lower()
    refs.append(r)
refs.sort(key=lambda r: r["sort"])
json.dump(refs, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in refs:
    print(r["pre"] + r["ital"] + r["post"])
