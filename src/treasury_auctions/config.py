"""Project paths, profiles and fixed study constants.

Nothing here depends on the user's machine: every path is resolved relative to a
project root that is either given explicitly, taken from ``TBA_ROOT`` or found by
walking up from the current working directory to the folder holding ``pyproject.toml``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Historical snapshot cutoff fixed by the handoff (Section 4). Documents published
# after this date are excluded from the confirmatory research freeze.
SNAPSHOT_CUTOFF = "2026-11-06"

# Native time zones of the three issuers (IANA names).
TIMEZONES = {"UG": "Africa/Kampala", "KE": "Africa/Nairobi", "GH": "Africa/Accra"}
CURRENCY = {"UG": "UGX", "KE": "KES", "GH": "GHS"}
# Reporting unit used for normalized quantities in each market.
UNIT = {"UG": "UGX_bn", "KE": "KES_m", "GH": "GHS_m"}
TENORS = (91, 182, 364)

OFFICIAL_HOSTS = {"bou.or.ug", "www.centralbank.go.ke", "www.bog.gov.gh"}

# An honest, generic client name. No personal contact details are sent.
USER_AGENT = "treasury-auctions-research/0.1 (public-document research client)"


def find_root(start: Path | None = None) -> Path:
    env = os.environ.get("TBA_ROOT")
    if env:
        return Path(env).resolve()
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "src" / "treasury_auctions").is_dir():
            return candidate
    return here


@dataclass
class Paths:
    root: Path
    cache: Path = field(init=False)
    interim: Path = field(init=False)
    frozen: Path = field(init=False)
    outputs: Path = field(init=False)
    tables: Path = field(init=False)
    figures: Path = field(init=False)
    reports: Path = field(init=False)
    review: Path = field(init=False)

    def __post_init__(self) -> None:
        self.root = Path(self.root).resolve()
        cache = os.environ.get("TBA_CACHE")
        self.cache = Path(cache).resolve() if cache else self.root / "data" / "cache"
        self.interim = self.root / "data" / "interim"
        self.frozen = self.root / "data" / "frozen"
        self.review = self.root / "data" / "review"
        self.outputs = self.root / "outputs"
        self.tables = self.outputs / "tables"
        self.figures = self.outputs / "figures"
        self.reports = self.outputs / "reports"

    def ensure(self) -> Paths:
        for p in (self.cache, self.interim, self.frozen, self.review, self.tables, self.figures, self.reports):
            p.mkdir(parents=True, exist_ok=True)
        return self


def get_paths(root: Path | None = None) -> Paths:
    return Paths(root or find_root())
