"""Derive the Emerging Markets Review submission manuscript from manuscript_draft.md.

Writes, into <out_dir>:
  manuscript_EMR_full.md        title page + manuscript (for co-author review / single-anonymised review)
  manuscript_EMR_anonymised.md  no author-identifying text (for double-anonymised review)
  title_page_EMR.md             separate title page with declarations
  highlights_EMR.md             3-5 highlights, each <= 85 characters
"""
import re
import sys
from pathlib import Path

root, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
md = (root / "manuscript" / "manuscript_draft.md").read_text(encoding="utf-8").replace("\r\n", "\n")

TITLE = md.splitlines()[0].lstrip("# ").strip()
body = md.split("## 1. Introduction", 1)[1]
body = "## 1. Introduction" + body.split("## Declarations", 1)[0]

# ---- code paths -> replication-package table references
body = re.sub(r"\(`(?:outputs/tables/)?([A-Z]\d+[a-z]?)_[^`]*\.csv`\)", r"(replication package, Table \1)", body)
body = re.sub(r"`(?:outputs/tables/)?([A-Z]\d+[a-z]?)_[^`]*\.csv`", r"replication package Table \1", body)
body = body.replace("(`docs/audit_and_limitations.md`)", "(replication package, audit notes)")
body = body.replace("The versioned protocol and subsequent\nrevisions are in `docs/protocol.md`.",
                    "The versioned protocol and its dated\nrevisions are in the replication package.")
body = body.replace("(`F1`–`F6` and the delayed-publication tables)",
                    "(replication package, Tables F1–F6 and the delayed-publication tables)")
body = re.sub(r"Source: replication package Table (T\d+[a-z]?)", r"Source: authors' calculations from BoU, CBK and BoG notices (replication package, Table \1)", body)
assert "`" not in body.split("## 8. Reproducibility")[0], "code path left in main text"

# ---- limitations / conclusion / reproducibility
repro_old = body.split("## 8. Reproducibility", 1)[1]
body = body.split("## 8. Reproducibility", 1)[0]
CONCLUSION = """## 8. Conclusion and further research

Official notices from three African bill markets show that the same headline auction outcome can
describe different events. Uganda's shortfalls occurred with bids in hand. Kenya's and Ghana's arose
mainly because bids did not reach the offer, although Ghana's pattern weakened in 2025–26. Totals
masked maturity-level misses, and filled auctions moved the maturity of new issuance in opposite
directions in Uganda and Kenya. Publishing offer, bids and acceptances per maturity, the split of any
shortfall, the realised versus advertised maturity and a defined cover ratio would make these
differences visible to investors, analysts and debt managers.

Several extensions follow. First, bid-level or price-schedule data, where debt offices can share them,
would show whether unaccepted bids were priced above the yields the issuer accepted, turning the
accounting split into evidence on pricing decisions. Second, the framework applies directly to
Treasury bond auctions and to other markets that publish maturity-level auction notices, which would
give a wider view of how common each pattern is. Third, linking the maturity shift to redemption
profiles would show whether filled auctions ease or concentrate rollover pressure. Finally, an
operational warning claim requires a prospective record of forecasts written down before outcomes are
known; a protocol for such a record is registered in the replication package.
"""
body = body.rstrip() + "\n\n" + CONCLUSION

ABSTRACT = """Headline Treasury bill auction statistics, such as total accepted against total offered and the
published bid-to-cover ratio, do not show why an auction falls short or whether a filled auction
changes the maturity of new debt. Using 1,210 auction records from official notices of the central
banks of Uganda, Kenya and Ghana (2014–2026), we split each shortfall exactly into a part due to bids
falling short of the offer and a part due to bids not accepted, and compare the accepted maturity mix
with the offered mix. From January 2023 to October 2026, none of Uganda's shortfall volume reflects
insufficient bids: all 34 auctions that fell short had bids at least equal to the offer. In Kenya
81.1% (95% interval 70.8–89.5%) and in Ghana 74.5% (61.0–90.2%) of shortfall volume reflects
insufficient bids. Totals mask maturity-level misses in 85–88% of filled Ugandan and Kenyan auctions,
and filled auctions lengthened new-issue maturity in Uganda (median +26.9 days) but shortened it in
Kenya (−46.4 days). Uganda's published bid-to-cover ratio changed its denominator over time. A
release-aware forecasting evaluation does not support an operational warning rule. We propose
disclosures that let users tell these cases apart."""
n_abs = len(ABSTRACT.split())
assert n_abs <= 200, n_abs

KEYWORDS = "Treasury bills; sovereign debt auctions; primary market; debt management; maturity structure; Sub-Saharan Africa"
JEL = "H63; E43; G12; D44"

REPO = "https://github.com/Isaac25-lgtm/africa-treasury-bill-auctions"
DATA_FULL = (f"The official notices are public on the websites of the Bank of Uganda, the Central Bank of Kenya "
             f"and the Bank of Ghana. Source URLs, SHA-256 hashes, the correction ledger, derived tables and all "
             f"code are in the replication package ({REPO}); a release tag and archive DOI will be added on "
             f"acceptance. Source PDFs are not redistributed.")
DATA_ANON = ("The official notices are public on the websites of the Bank of Uganda, the Central Bank of Kenya "
             "and the Bank of Ghana. Source URLs, SHA-256 hashes, the correction ledger, derived tables and all "
             "code are in a public replication package (link withheld for anonymised review). Source PDFs are not "
             "redistributed.")

AI_STATEMENT = ("During the preparation of this work the authors used Claude (Anthropic), an AI assistant, to "
                "write and test data-processing code, check extracted values against source documents and draft "
                "and edit text. After using this tool, the authors reviewed and edited the content as needed and "
                "take full responsibility for the content of the publication.")

AUTHORS = """**Omoding Isaac** (corresponding author)
[Department], Ministry of Health, [City, postcode], [Country]
Email: omodingisaac111@gmail.com · Telephone: [+country code number]

**Kakande Alex**
Financial Advisor, [Organisation or "Independent"], [City, postcode], [Country]
Email: [to be added]"""

DECLARATIONS = f"""## Declarations

**CRediT authorship contribution statement.** Omoding Isaac: Conceptualization, Methodology, Software,
Validation, Formal analysis, Investigation, Data curation, Visualization, Project administration,
Writing – original draft, Writing – review & editing. Kakande Alex: Conceptualization, Validation,
Writing – review & editing. [Proposed by the lead author; to be confirmed by Kakande Alex.]

**Declaration of competing interest.** The authors declare that they have no known competing financial
interests or personal relationships that could have appeared to influence the work reported in this
paper.

**Funding.** This research did not receive any specific grant from funding agencies in the public,
commercial, or not-for-profit sectors.

**Data availability.** {{DATA}}

**Declaration of generative AI and AI-assisted technologies in the writing process.** {AI_STATEMENT}
[Authors: confirm or edit this statement so that it matches how you used the tool.]

**Acknowledgements.** [To be added by the authors, or delete.]
"""

FIGS = """## Figures

Figure 1. Share of shortfall volume from bids short of the offer (D) versus bids not accepted (R).
"""  # the docx builder replaces this section with the embedded figures

REFS = "## References\n"


def front(with_authors: bool) -> str:
    parts = [f"# {TITLE}", ""]
    if with_authors:
        parts += [AUTHORS, ""]
    parts += ["---", "", "## Abstract", "", ABSTRACT, "", f"**Keywords:** {KEYWORDS}", "", f"**JEL classification:** {JEL}", "", "---", ""]
    return "\n".join(parts)


full = front(True) + body + "\n" + DECLARATIONS.replace("{DATA}", DATA_FULL) + "\n" + FIGS + "\n" + REFS
anon = front(False) + body + "\n" + DECLARATIONS.replace("{DATA}", DATA_ANON) + "\n" + FIGS + "\n" + REFS
# anonymised: drop author-identifying declarations (they go on the title page)
anon = re.sub(r"\*\*CRediT authorship contribution statement\.\*\*.*?\n\n", "", anon, flags=re.S)
anon = re.sub(r"\*\*Acknowledgements\.\*\*.*?\n", "", anon)
for ident in ("Omoding", "Kakande", "Isaac25", "omodingisaac"):
    assert ident not in anon, ident

title_page = "\n".join([f"# {TITLE}", "", AUTHORS, "", "---", "",
                        DECLARATIONS.replace("{DATA}", DATA_FULL).replace("## Declarations", "## Declarations (title page)")])

HIGHLIGHTS = [
    "Each T-bill auction shortfall is split into missing bids and unaccepted bids",
    "Uganda's shortfalls all had enough bids; Kenya's and Ghana's mostly did not",
    "Auctions that meet their total often miss individual maturities",
    "Filled auctions lengthened new-debt maturity in Uganda, shortened it in Kenya",
    "Public pre-auction data do not support a reliable shortfall warning rule",
]
for h in HIGHLIGHTS:
    assert len(h) <= 85, (len(h), h)
highlights = "# Highlights\n\n" + "\n".join(f"* {h}" for h in HIGHLIGHTS) + "\n"

(out / "manuscript_EMR_full.md").write_text(full, encoding="utf-8")
(out / "manuscript_EMR_anonymised.md").write_text(anon, encoding="utf-8")
(out / "title_page_EMR.md").write_text(title_page, encoding="utf-8")
(out / "highlights_EMR.md").write_text(highlights, encoding="utf-8")

words = len(re.findall(r"\S+", body))
print(f"abstract {n_abs} words; main text {words} words; highlights max {max(map(len, HIGHLIGHTS))} chars")
print("unused reproducibility text (now in data availability):", repro_old.strip()[:80], "...")
