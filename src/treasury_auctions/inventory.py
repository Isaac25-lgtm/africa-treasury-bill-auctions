"""Build and freeze source inventories before any parsing (handoff Phase A.4).

Outputs (``data/frozen/``):
* ``inventory_<country>.csv`` - one row per discovered asset, with scope decision
* ``ghana_posts.csv``         - every BoG archive post, including posts without a PDF
* ``inventory_meta.json``     - endpoint hashes, retrieval times, counts
After ``fetch``: ``fetch_manifest.csv`` adds hash, bytes, media kind and status.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import SNAPSHOT_CUTOFF, Paths
from .discovery import bog_attachments, discover_bog, discover_bou, discover_cbk
from .fetch import SourceCache

INVENTORY_COLUMNS = [
    "asset_id", "country", "issuer", "kind", "category", "family_hint", "url", "referrer", "title", "file_name",
    "ext", "folder_year", "folder_month", "auction_no_hint", "tender_no_hint", "issue_91", "issue_182", "issue_364",
    "dated_hint", "listed_sections", "posted_local", "posted_utc", "modified_utc", "asset_created", "asset_updated",
    "post_id", "discovery_status", "discovered_utc", "in_scope", "scope_reason",
]


def _scope_ug(r: dict) -> tuple[bool, str]:
    year = int(r["folder_year"]) if str(r.get("folder_year") or "").isdigit() else 0
    if r["kind"] == "result":
        return True, "auction results folder (content classification decides bill/bond/matrix)"
    if r["kind"] == "invitation":
        if year >= 2016:
            return True, "invitation within result-coverage window (2016+)"
        return False, "invitation predates available results archive (pre-2016)"
    return False, "guidelines/other category"


def build_inventory(paths: Paths, cache: SourceCache, sources=("UG", "KE", "GH"), workers: int = 4) -> dict:
    paths.ensure()
    meta: dict = {"snapshot_cutoff": SNAPSHOT_CUTOFF}
    out: dict[str, pd.DataFrame] = {}
    if "UG" in sources:
        rows, m = discover_bou(cache)
        for r in rows:
            r["in_scope"], r["scope_reason"] = _scope_ug(r)
        out["UG"], meta["UG"] = pd.DataFrame(rows), m
    if "KE" in sources:
        rows, m = discover_cbk(cache)
        for r in rows:
            r["in_scope"], r["scope_reason"] = True, "weekly Treasury bill results notice"
            r["listed_sections"] = ";".join(str(s) for s in r["listed_sections"])
        out["KE"], meta["KE"] = pd.DataFrame(rows), m
    if "GH" in sources:
        posts, m = discover_bog(cache)
        pd.DataFrame(posts).sort_values("posted_local").to_csv(paths.frozen / "ghana_posts.csv", index=False)
        rows = bog_attachments(cache, posts, workers=workers)
        for r in rows:
            ok = r.get("url") is not None
            r["in_scope"], r["scope_reason"] = ok, ("tender results attachment" if ok else r["discovery_status"])
        m["attachments"] = sum(1 for r in rows if r.get("url"))
        m["posts_without_pdf"] = sum(1 for r in rows if not r.get("url"))
        out["GH"], meta["GH"] = pd.DataFrame(rows), m
    cache.save_index()
    for country, df in out.items():
        for c in INVENTORY_COLUMNS:
            if c not in df.columns:
                df[c] = None
        df = df[INVENTORY_COLUMNS].sort_values(["kind", "url"], na_position="last")
        df.to_csv(paths.frozen / f"inventory_{country}.csv", index=False)
        meta[country]["rows"] = len(df)
        meta[country]["in_scope"] = int(df.in_scope.sum())
    prior = {}
    mp = paths.frozen / "inventory_meta.json"
    if mp.is_file():
        prior = json.loads(mp.read_text(encoding="utf-8"))
    prior.update(meta)
    mp.write_text(json.dumps(prior, indent=2, default=str), encoding="utf-8")
    return meta


def load_inventory(paths: Paths, countries=("UG", "KE", "GH")) -> pd.DataFrame:
    frames = [pd.read_csv(paths.frozen / f"inventory_{c}.csv", dtype=str) for c in countries
              if (paths.frozen / f"inventory_{c}.csv").is_file()]
    df = pd.concat(frames, ignore_index=True)
    df["in_scope"] = df.in_scope.str.lower().eq("true")
    return df


def fetch_inventory(paths: Paths, cache: SourceCache, countries=("UG", "KE", "GH"), workers: int = 4,
                    limit: int | None = None) -> pd.DataFrame:
    inv = load_inventory(paths, countries)
    todo = inv[inv.in_scope & inv.url.notna()].drop_duplicates("url")
    if limit:
        todo = todo.groupby("country").head(limit)
    recs = cache.get_many(todo.url.tolist(), workers=workers)
    man = pd.DataFrame([r.__dict__ for r in recs]).rename(columns={"status": "fetch_status"})
    man = todo[["asset_id", "country", "kind", "url"]].merge(man, on="url", how="left")
    target = paths.frozen / "fetch_manifest.csv"
    if target.is_file() and limit is None:
        pass
    if target.is_file():
        old = pd.read_csv(target, dtype=str)
        old = old[~old.url.isin(man.url)]
        man = pd.concat([old, man.astype(str)], ignore_index=True)
    man.sort_values(["country", "url"]).to_csv(target, index=False)
    return man


def fetch_summary(man: pd.DataFrame) -> pd.DataFrame:
    return man.groupby(["country", "fetch_status"]).size().unstack(fill_value=0)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
