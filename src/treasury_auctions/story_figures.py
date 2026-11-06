"""README story charts. Each chart's title states its takeaway; every number is read from the
generated tables (``outputs/tables``, ``data/derived``, ``outputs/reports``), so the charts cannot
drift from the analysis.

Saved as PNG on a white background (readable in GitHub light and dark themes) in
``outputs/figures/readme/``. Usage: ``python -m treasury_auctions story`` (also run by ``report``).
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .config import Paths  # noqa: E402

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRAY, LIGHT, INK, INK2, RULE = "#898781", "#e1e0d9", "#0b0b0b", "#52514e", "#c3c2b7"
COUNTRY = {"UG": "Uganda", "KE": "Kenya", "GH": "Ghana"}
COMMON = "common_2023-01-13_2026-10-30"
RECENT = "recent_2025-01-01_2026-10-30"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "font.size": 10, "axes.edgecolor": RULE, "axes.labelcolor": INK2, "xtick.color": INK2,
    "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "legend.frameon": False,
})


class Story:
    def __init__(self, paths: Paths):
        self.p = paths
        self.out = paths.figures / "readme"
        self.out.mkdir(parents=True, exist_ok=True)
        self.derived = paths.root / "data" / "derived"

    # ------------------------------------------------------------------ helpers
    def t(self, name: str, **kw) -> pd.DataFrame:
        return pd.read_csv(self.p.tables / f"{name}.csv", **kw)

    @staticmethod
    def header(fig, title: str, subtitle: str, top: float = 0.80) -> None:
        fig.text(0.012, 0.975, title, fontsize=13.5, fontweight="bold", color=INK, va="top")
        fig.text(0.012, 0.975 - 0.42 * (1 - top), subtitle, fontsize=9.5, color=INK2, va="top")
        fig.subplots_adjust(top=top)

    def save(self, fig, name: str) -> None:
        fig.savefig(self.out / f"{name}.png", dpi=200, bbox_inches="tight", pad_inches=0.12)
        plt.close(fig)

    @staticmethod
    def clean(ax, keep_x: bool = False) -> None:
        for sp in ("left", "right", "top") + (() if keep_x else ("bottom",)):
            ax.spines[sp].set_visible(False)
        ax.tick_params(axis="y", length=0)

    def t1(self, window: str, level: str) -> pd.DataFrame:
        t = self.t("T1_decomposition")
        return t[(t.offer_version == "result") & (t.window == window) & (t.tol == 0) & (t.level == level)]

    # ------------------------------------------------------------------ 0 hero
    def hero(self) -> None:
        rows = []
        for c in ("UG", "KE", "GH"):
            r = self.t1(COMMON, "auction_wide").set_index("country").loc[c]
            rows.append((c, r.n_events, r.n_miss, r.n_miss_B_ge_O, r.volume_share_D))
        fig, ax = plt.subplots(figsize=(9.2, 3.0))
        for y, (_c, n, miss, ge, share) in enumerate(rows):
            d, r = share, 1 - share
            if d > 0.004:
                ax.barh(y, d - 0.004, color=BLUE, height=0.6, lw=0)
                ax.text(d / 2, y, f"{d:.0%}", ha="center", va="center", color="white", fontsize=11,
                        fontweight="bold")
            ax.barh(y, r, left=d, color=ORANGE, height=0.6, lw=0)
            ax.text(d + r / 2, y, f"{r:.0%}", ha="center", va="center", color="white", fontsize=11,
                    fontweight="bold")
            ax.text(1.02, y, f"{miss} of {n} auctions fell short\n{ge} of them with enough bids",
                    va="center", fontsize=9.3, color=INK2, linespacing=1.15)
        ax.set_yticks(range(3), [COUNTRY[c] for c, *_ in rows], fontsize=11.5)
        ax.invert_yaxis()
        ax.set_xlim(0, 1)
        ax.xaxis.set_visible(False)
        self.clean(ax)
        h = [plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)]
        ax.legend(h, ["bids fell short of the offer", "enough bids, but not accepted"], ncol=2,
                  loc="upper left", bbox_to_anchor=(0, -0.02), fontsize=9.5, handlelength=1.2)
        self.header(fig, "Same headline, different failure: why Treasury bill auctions fell short",
                    "Share of shortfall volume, auctions that missed their overall offer, 13 Jan 2023 – 30 Oct 2026. "
                    "Ratio of sums within each country.", top=0.74)
        self.save(fig, "0_why_auctions_fall_short")

    # ------------------------------------------------------------------ 1 coverage
    def coverage(self) -> None:
        ev = pd.read_csv(self.derived / "auction_events.csv")
        ev["year"] = ev.held_date.str[:4].astype(int)
        years = list(range(2014, 2027))
        tab = ev.groupby(["country", "year"]).size().unstack(fill_value=0).reindex(columns=years, fill_value=0)
        fig, ax = plt.subplots(figsize=(9.2, 2.9))
        colors = {"UG": BLUE, "KE": ORANGE, "GH": AQUA}
        for y, c in enumerate(("UG", "KE", "GH")):
            vals = tab.loc[c] if c in tab.index else pd.Series(0, index=years)
            mx = max(tab.max().max(), 1)
            for x, yr in enumerate(years):
                v = int(vals[yr])
                if v:
                    ax.scatter(x, y, s=60 + 560 * v / mx, color=colors[c], alpha=0.9, lw=0)
                    if v >= 0.35 * mx:  # label inside large circles, below small ones
                        ax.text(x, y, str(v), ha="center", va="center", fontsize=8, color="white",
                                fontweight="bold")
                    else:
                        ax.text(x, y + 0.33, str(v), ha="center", va="center", fontsize=7.6, color=INK2)
            ax.text(len(years) - 0.3, y, f"{int(vals.sum()):,}", va="center", fontsize=10.5,
                    fontweight="bold", color=INK)
        ax.set_yticks(range(3), ["Uganda", "Kenya", "Ghana"], fontsize=11)
        ax.set_xticks(range(len(years)), [str(y) for y in years], fontsize=9)
        ax.set_ylim(2.75, -0.55)
        ax.set_xlim(-0.6, len(years) + 0.4)
        self.clean(ax, keep_x=True)
        ax.text(len(years) - 0.3, -0.5, "auctions", fontsize=8.5, color=INK2, va="bottom")
        n = len(ev)
        self.header(fig, f"{n:,} auctions rebuilt from the central banks' own notices",
                    "Bill auctions per year in the audited panel. Gaps are real archive gaps (Uganda 2019; "
                    "Kenya before 2017), not parsing failures.", top=0.74)
        self.save(fig, "1_coverage")

    # ------------------------------------------------------------------ 2 example #1237
    def example(self) -> None:
        o = pd.read_csv(self.derived / "auction_outcomes.csv", dtype={"tenor": str})
        x = o[o.event_id == "UG-1237"].set_index("tenor").loc[["91", "182", "364"]]
        fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.2), gridspec_kw={"width_ratios": [1, 1, 1]})
        labels = {"91": "91-day bill", "182": "182-day bill", "364": "364-day bill"}
        for ax, (tenor, r) in zip(axes, x.iterrows()):
            vals = [r.O_result, r.B, r.A]
            cols = [GRAY, LIGHT, BLUE if r.A >= r.O_result else ORANGE]
            ax.bar(range(3), vals, color=cols, width=0.68, lw=0)
            for i, v in enumerate(vals):
                ax.text(i, v, f"{v:,.1f}", ha="center", va="bottom", fontsize=9, color=INK)
            ax.set_xticks(range(3), ["offered", "bids", "accepted"], fontsize=9)
            ax.set_yticks([])
            self.clean(ax, keep_x=True)
            verdict = "over-filled" if r.A > r.O_result else "under-filled"
            ax.set_title(f"{labels[tenor]}: {verdict}", fontsize=10.5, color=INK, loc="left", fontweight="bold")
        tot = x[["O_result", "B", "A"]].sum()
        self.header(fig, "Auction #1237 filled its total, yet missed two of three maturities",
                    f"Bank of Uganda, 4 Nov 2026, UGX bn. Total offered {tot.O_result:,.0f}, bids {tot.B:,.1f}, "
                    f"accepted {tot.A:,.1f}. Bids exceeded the offer at every maturity.", top=0.72)
        self.save(fig, "2_example_1237")

    # ------------------------------------------------------------------ 3 auction-wide vs maturity
    def levels(self) -> None:
        aw, tn = self.t1(COMMON, "auction_wide").set_index("country"), self.t1(COMMON, "tenor").set_index("country")
        rows = [("UG", "auction-wide", aw.loc["UG"]), ("UG", "by maturity", tn.loc["UG"]),
                ("KE", "auction-wide", aw.loc["KE"]), ("KE", "by maturity", tn.loc["KE"]),
                ("GH", "auction-wide", aw.loc["GH"])]
        fig, ax = plt.subplots(figsize=(9.2, 3.6))
        for y, (_c, lev, r) in enumerate(rows):
            s = r.volume_share_D
            ax.plot([0, 1], [y, y], color=LIGHT, lw=6, solid_capstyle="round", zorder=1)
            if np.isfinite(r.ci95_lo_b8):
                ax.plot([r.ci95_lo_b8, r.ci95_hi_b8], [y, y], color=INK2, lw=2, zorder=2)
            ax.scatter(s, y, s=95, color=BLUE if s > 0.5 else ORANGE, zorder=3, lw=0)
            unit = "maturity misses" if lev == "by maturity" else "auction misses"
            ax.text(1.03, y, f"{s:.1%}   {int(r.n_miss)} {unit}, {int(r.n_miss_B_ge_O)} with enough bids",
                    va="center", fontsize=9.3, color=INK2)
        ax.set_yticks(range(len(rows)), [f"{COUNTRY[c]}, {lev}" for c, lev, _ in rows], fontsize=10.5)
        ax.invert_yaxis()
        ax.set_xlim(-0.02, 1.0)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"], fontsize=9)
        self.clean(ax, keep_x=True)
        self.header(fig, "The contrast holds within maturities too, with tight intervals",
                    "Share of shortfall volume caused by bids short of the offer. Line: 95% moving-block "
                    "bootstrap (8-auction blocks). Common window 2023–2026.", top=0.78)
        self.save(fig, "3_auction_vs_maturity")

    # ------------------------------------------------------------------ 4 over time
    def over_time(self) -> None:
        t2 = self.t("T2_decomposition_by_year")
        fig, ax = plt.subplots(figsize=(9.2, 3.4))
        colors = {"UG": BLUE, "KE": ORANGE, "GH": AQUA}
        for c in ("UG", "KE", "GH"):
            x = t2[(t2.country == c) & (t2.n_miss > 0)].copy()
            x["year"] = x.year.astype(int)
            ax.plot(x.year, x.share, color=colors[c], lw=2.4, marker="o", ms=5.5)
            last = x.iloc[-1]
            ax.text(last.year + 0.18, last.share, f"{COUNTRY[c]}  {last.share:.0%}", va="center",
                    fontsize=10, color=colors[c], fontweight="bold")
        gh = t2[(t2.country == "GH") & (t2.year == 2026)]
        if not gh.empty:
            g = gh.iloc[0]
            ax.annotate(f"Ghana 2026: {int(g.n_miss_B_ge_O)} of {int(g.n_miss)} misses\nhad enough bids",
                        (2026, g.share), xytext=(2023.1, 0.28), fontsize=9, color=INK2,
                        arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
        ax.set_ylim(-0.04, 1.08)
        ax.set_yticks([0, 0.5, 1], ["0%", "50%", "100%"])
        ax.set_xticks(range(2017, 2027))
        ax.set_xlim(2016.6, 2027.6)
        self.clean(ax, keep_x=True)
        ax.axhline(0.5, color=LIGHT, lw=1, zorder=0)
        self.header(fig, "Uganda near zero since 2020; Ghana's share fell sharply in 2025–26",
                    "Share of shortfall volume from bids short of the offer, by year (years with at least one "
                    "shortfall). Auction-wide, result-side offer.", top=0.78)
        self.save(fig, "4_over_time")

    # ------------------------------------------------------------------ 5 masking
    def masking(self) -> None:
        m = self.t("T3_masking")
        m = m[m.window == COMMON].set_index("country")
        fig, ax = plt.subplots(figsize=(9.2, 2.5))
        for y, c in enumerate(("UG", "KE")):
            r = m.loc[c]
            met, hid = int(r.n_overall_met), int(r.n_met_with_tenor_miss)
            ax.barh(y, met, color=LIGHT, height=0.58, lw=0)
            ax.barh(y, hid, color=ORANGE, height=0.58, lw=0)
            ax.text(hid / 2, y, f"{hid} ({hid / met:.0%})", ha="center", va="center", color="white",
                    fontsize=10.5, fontweight="bold")
            ax.text(met + 2, y, f"{met} auctions met the total", va="center", fontsize=9.3, color=INK2)
        ax.set_yticks([0, 1], ["Uganda", "Kenya"], fontsize=11.5)
        ax.invert_yaxis()
        ax.xaxis.set_visible(False)
        self.clean(ax)
        ax.set_xlim(0, m.n_overall_met.max() * 1.35)
        self.header(fig, "Most auctions that met their total still missed at least one maturity",
                    "Orange: auctions that filled the overall offer but under-filled one or more of the 91-, 182- "
                    "or 364-day bills. 2023–2026.", top=0.70)
        self.save(fig, "5_totals_hide_misses")

    # ------------------------------------------------------------------ 6 maturity shift
    def maturity(self) -> None:
        me = self.t("maturity_events")
        me = me[me.met & me.shift_nominal.notna() & (me.held_date >= "2023-01-13") & (me.held_date <= "2026-10-30")]
        fig, ax = plt.subplots(figsize=(9.2, 3.2))
        rng = np.random.default_rng(5)
        for y, (c, col) in enumerate((("UG", BLUE), ("KE", ORANGE))):
            v = me[me.country == c].shift_nominal.to_numpy()
            ax.scatter(v, y + rng.uniform(-0.17, 0.17, len(v)), s=16, color=col, alpha=0.55, lw=0)
            med = float(np.median(v))
            ax.plot([med, med], [y - 0.3, y + 0.3], color=INK, lw=2.4)
            ax.text(med, y - 0.36, f"median {med:+.0f} days", ha="center", va="bottom", fontsize=9.5,
                    color=INK, fontweight="bold")
            ax.text(155, y, f"{len(v)} auctions", va="center", fontsize=9.3, color=INK2)
        ax.axvline(0, color=INK2, lw=0.9, ls=(0, (3, 3)))
        ax.text(2, 1.62, "longer than advertised →", fontsize=8.8, color=INK2)
        ax.text(-2, 1.62, "← shorter than advertised", fontsize=8.8, color=INK2, ha="right")
        ax.set_yticks([0, 1], ["Uganda", "Kenya"], fontsize=11.5)
        ax.set_ylim(1.75, -0.65)
        ax.set_xlim(-150, 200)
        ax.set_xticks([-150, -100, -50, 0, 50, 100, 150])
        ax.set_xlabel("accepted minus offered face-value-weighted maturity (days)", fontsize=9)
        self.clean(ax, keep_x=True)
        self.header(fig, "When the total is met, new debt comes out longer in Uganda and shorter in Kenya",
                    "Each dot is an auction that met its overall offer, 13 Jan 2023 – 30 Oct 2026. "
                    "Nominal 91/182/364-day weights.", top=0.76)
        self.save(fig, "6_maturity_shift")

    # ------------------------------------------------------------------ 7 cover ratio
    def cover_ratio(self) -> None:
        o = pd.read_csv(self.derived / "auction_outcomes.csv", dtype={"tenor": str})
        x = o[(o.country == "UG") & o.cover_formula.notna()].copy()
        x["year"] = x.held_date.astype(str).str[:4].astype(int)
        x["f"] = x.cover_formula.str.replace(r"ambiguous.*", "amb", regex=True)
        tab = x.groupby(["year", "f"]).size().unstack(fill_value=0)
        for k in ("B/O", "B/A", "amb", "inconsistent"):
            if k not in tab:
                tab[k] = 0
        share = tab.div(tab.sum(axis=1), axis=0)
        fig, ax = plt.subplots(figsize=(9.2, 3.0))
        cols = {"B/O": ORANGE, "B/A": BLUE, "amb": LIGHT, "inconsistent": GRAY}
        names = {"B/O": "bids ÷ offered", "B/A": "bids ÷ accepted",
                 "amb": "cannot tell (auction exactly filled)", "inconsistent": "matches neither"}
        bottom = np.zeros(len(share))
        for k in ("B/O", "B/A", "amb", "inconsistent"):
            ax.bar(share.index, share[k], bottom=bottom, color=cols[k], width=0.72, lw=0, label=names[k])
            bottom += share[k].to_numpy()
        ax.set_yticks([0, 0.5, 1], ["0%", "50%", "100%"])
        ax.set_xticks(share.index)
        self.clean(ax, keep_x=True)
        ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, -0.1), fontsize=9, handlelength=1.1)
        self.header(fig, "Uganda's published \"bid to cover\" changed what it divides by",
                    "Bank of Uganda bill releases: which formula the printed ratio matches at its quoted precision, "
                    "share of maturity rows per year. Kenya's matches bids ÷ accepted throughout.", top=0.76)
        self.save(fig, "7_cover_ratio_definition")

    # ------------------------------------------------------------------ 8 forecasting
    def forecasting(self) -> None:
        g = self.t("F6_gate4_strict")
        g = g[g.model == "logit_full"]
        order = [("tenor", "KE", "Kenya, by maturity"), ("auction", "KE", "Kenya, auction-wide"),
                 ("tenor", "UG", "Uganda, by maturity"), ("auction", "UG", "Uganda, auction-wide"),
                 ("auction", "GH", "Ghana, auction-wide")]
        fig, ax = plt.subplots(figsize=(9.2, 3.8))
        cols = {"holdout": BLUE, "replication": ORANGE}
        off = {"holdout": -0.17, "replication": 0.17}
        for y, (lev, c, _lab) in enumerate(order):
            for per in ("holdout", "replication"):
                r = g[(g.level == lev) & (g.country == c) & (g.period == per)]
                if r.empty:
                    continue
                r = r.iloc[0]
                yy = y + off[per]
                ax.plot([r.ci95_lo_b8, r.ci95_hi_b8], [yy, yy], color=cols[per], lw=2)
                ax.scatter(r.logloss_diff, yy, color=cols[per], s=46, zorder=3, lw=0)
        ax.axvline(0, color=INK2, lw=0.9)
        ax.axvline(-0.02, color=INK2, lw=0.8, ls=(0, (2, 3)))
        ax.text(-0.022, -0.75, "pre-set bar: −0.02", fontsize=8.5, color=INK2, ha="right")
        ax.text(0.01, -0.75, "worse than the simple rule →", fontsize=8.5, color=INK2)
        ax.set_yticks(range(len(order)), [lab for *_, lab in order], fontsize=10.5)
        ax.set_ylim(len(order) - 0.45, -0.95)
        ax.set_xlabel("change in log loss vs the strongest simple rule (negative = better)", fontsize=9)
        self.clean(ax, keep_x=True)
        h = [plt.Line2D([], [], color=cols[p], marker="o", lw=2) for p in ("holdout", "replication")]
        ax.legend(h, ["locked holdout 2023–24", "next period 2025–26"], loc="lower right", fontsize=9)
        self.header(fig, "A forecasting gain appeared in Kenya in 2023–24, then disappeared",
                    "Logistic model with public pre-auction information vs the strongest simple baseline. "
                    "Lines: 95% moving-block intervals. Pre-registered test.", top=0.78)
        self.save(fig, "8_forecasting")

    # ------------------------------------------------------------------ 9 audit scorecard
    def audit(self) -> None:
        a = json.loads((self.p.reports / "audit_summary.json").read_text(encoding="utf-8"))
        se = a["second_extraction"]
        pil = a["pilot_comparison"]
        rec = a["offer_reconciliation"]
        pil_match = sum(v for k, v in pil.items() if k.endswith("|match"))
        pil_diff = sum(v for k, v in pil.items() if k.endswith("|value difference"))
        rec_agree = sum(v for k, v in rec.items() if k.endswith("|agree"))
        rec_mis = sum(v for k, v in rec.items() if k.endswith("|mismatch"))
        rows = [("Second, independent extraction", se["cells_agree"], se["cells"], "values agree"),
                ("Pilot replay cells recovered", pil_match, pil_match + pil_diff,
                 f"match ({pil_diff} differ: all pilot errors)"),
                ("Pre-auction vs published offers", rec_agree, rec_agree + rec_mis,
                 f"agree ({rec_mis} reported, not corrected)")]
        fig, ax = plt.subplots(figsize=(9.2, 2.6))
        for y, (_lab, ok, n, note) in enumerate(rows):
            ax.barh(y, 1, color=LIGHT, height=0.55, lw=0)
            ax.barh(y, ok / n, color=AQUA, height=0.55, lw=0)
            ax.text(0.015, y, f"{ok:,} of {n:,} {note}", va="center", fontsize=9.8, color="white",
                    fontweight="bold")
        ax.set_yticks(range(3), [r[0] for r in rows], fontsize=10.5)
        ax.invert_yaxis()
        ax.xaxis.set_visible(False)
        self.clean(ax)
        ax.set_xlim(0, 1)
        self.header(fig, "The data check out before any result is read",
                    "Audit of the rebuilt panel. Every value links to the official document, its SHA-256 hash and "
                    "the raw line of text it came from.", top=0.70)
        self.save(fig, "9_audit")

    def all(self) -> list[str]:
        for f in (self.hero, self.coverage, self.example, self.levels, self.over_time, self.masking,
                  self.maturity, self.cover_ratio, self.forecasting, self.audit):
            f()
        return sorted(p.name for p in self.out.glob("*.png"))


def make_story_figures(paths: Paths) -> list[str]:
    return Story(paths).all()
