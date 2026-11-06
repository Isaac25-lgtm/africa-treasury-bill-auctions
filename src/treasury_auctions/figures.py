"""Publication exhibits (PNG 300 dpi + PDF vector) with per-figure source data.

Colour: two validated categorical slots (blue = volume-driven shortfall D, orange =
unaccepted-bid remainder R); all other ink is neutral. Every bar is direct-labelled
so identity never relies on colour alone.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .config import Paths  # noqa: E402

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
NAMES = {"UG": "Uganda", "KE": "Kenya", "GH": "Ghana"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})


def _save(fig, paths: Paths, name: str) -> None:
    fig.savefig(paths.figures / f"{name}.png", dpi=300, bbox_inches="tight")
    fig.savefig(paths.figures / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_decomposition(paths: Paths) -> None:
    t = pd.read_csv(paths.tables / "T1_decomposition.csv")
    sel = t[(t.offer_version == "result") & (t.tol == 0) &
            (t.window.isin(["common_2023-01-13_2026-10-30", "recent_2025-01-01_2026-10-30"]))].copy()
    rows = []
    for _, r in sel.iterrows():
        if r.sum_S <= 0:
            continue
        rows.append(dict(window=r.window, country=r.country, level=r.level, n_events=r.n_events, n_miss=r.n_miss,
                         n_miss_B_ge_O=r.n_miss_B_ge_O, share_D=r.volume_share_D, share_R=1 - r.volume_share_D,
                         lo=r.ci95_lo_b8, hi=r.ci95_hi_b8))
    d = pd.DataFrame(rows)
    d.to_csv(paths.figures / "fig1_decomposition_source.csv", index=False)
    order = [("UG", "auction_wide"), ("UG", "tenor"), ("KE", "auction_wide"), ("KE", "tenor"), ("GH", "auction_wide")]
    labels = {"auction_wide": "auction-wide", "tenor": "by maturity"}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    for ax, (w, title) in zip(axes, [("common_2023-01-13_2026-10-30", "Common window\n13 Jan 2023 – 30 Oct 2026"),
                                     ("recent_2025-01-01_2026-10-30", "Recent window\n1 Jan 2025 – 30 Oct 2026")]):
        x = d[d.window == w]
        ys, ticks = [], []
        for i, (c, lev) in enumerate(order):
            r = x[(x.country == c) & (x.level == lev)]
            ticks.append(f"{NAMES[c]}\n{labels[lev]}")
            ys.append(i)
            if r.empty:
                continue
            r = r.iloc[0]
            ax.barh(i, r.share_D * 100, color=BLUE, height=0.62)
            ax.barh(i, r.share_R * 100, left=r.share_D * 100 + 0.6, color=ORANGE, height=0.62)
            if np.isfinite(r.lo):
                ax.errorbar(r.share_D * 100, i, xerr=[[max(r.share_D - r.lo, 0) * 100], [max(r.hi - r.share_D, 0) * 100]],
                            fmt="none", ecolor=INK, elinewidth=0.9, capsize=2.5)
            ax.text(101, i, f"{r.share_D * 100:.0f}%  (misses {int(r.n_miss)}/{int(r.n_events)})", va="center",
                    fontsize=7.5, color=INK2)
        ax.set_yticks(ys, ticks)
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        ax.set_xlabel("Share of shortfall volume (%)")
        ax.set_title(title, fontsize=9, color=INK, loc="left")
        ax.grid(axis="y", visible=False)
    axes[0].legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)],
                   labels=["Bids short of offer (D)", "Bids not accepted (R)"], loc="lower left",
                   bbox_to_anchor=(0, -0.42), ncol=2, frameon=False, fontsize=8)
    fig.text(0, -0.08, "Ratio of sums within country (native currency); whiskers: 95% moving-block bootstrap (8-auction blocks).\n"
             "Text: volume share from insufficient bids, then misses / auctions (auction-wide) or misses / auctions (maturity rows).",
             fontsize=7, color=INK2)
    fig.subplots_adjust(wspace=0.55)
    _save(fig, paths, "fig1_decomposition")


def fig_maturity(paths: Paths) -> None:
    ev = pd.read_csv(paths.tables / "maturity_events.csv")
    ev = ev[ev.met & ev.shift_nominal.notna() & (ev.held_date >= "2023-01-13") & (ev.held_date <= "2026-10-30")]
    ev[["country", "event_id", "held_date", "O_tot", "A_tot", "shift_nominal"]].to_csv(
        paths.figures / "fig2_maturity_source.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    rng = np.random.default_rng(3)
    for i, c in enumerate(["UG", "KE"]):
        v = ev[ev.country == c].shift_nominal.to_numpy()
        if not len(v):
            continue
        ax.boxplot(v, positions=[i], vert=False, widths=0.5, showfliers=False,
                   medianprops=dict(color=INK, linewidth=1.6), boxprops=dict(color=INK2),
                   whiskerprops=dict(color=INK2), capprops=dict(color=INK2))
        ax.scatter(v, i + rng.uniform(-0.18, 0.18, len(v)), s=9, color=BLUE, alpha=0.55, linewidths=0)
        ax.text(ax.get_xlim()[1] if False else 0, i + 0.38, f"n = {len(v)}, median {np.median(v):+.1f} days",
                fontsize=7.5, color=INK2, ha="center")
    ax.axvline(0, color=INK2, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_yticks([0, 1], ["Uganda", "Kenya"])
    ax.set_xlabel("Accepted minus offered face-value-weighted maturity (days, nominal 91/182/364)")
    ax.set_title("Maturity shift in auctions that met the overall offer, 13 Jan 2023 – 30 Oct 2026",
                 fontsize=9, loc="left")
    ax.grid(axis="y", visible=False)
    _save(fig, paths, "fig2_maturity_shift")


def fig_timeline(paths: Paths) -> None:
    ev = pd.read_csv(paths.tables / "maturity_events.csv")
    u = ev[(ev.country == "UG") & ev.shift_nominal.notna()].sort_values("held_date")
    u = u[u.held_date >= "2022-01-01"].copy()
    u["fill_pct"] = u.A_tot / u.O_tot * 100
    u.to_csv(paths.figures / "fig3_uganda_timeline_source.csv", index=False)
    if u.empty:
        return
    dates = pd.to_datetime(u.held_date)
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 4.2), sharex=True)
    axes[0].plot(dates, u.fill_pct, color=INK2, linewidth=1.2, marker="o", markersize=2.5)
    axes[0].axhline(100, color=INK2, linewidth=0.8, linestyle=(0, (3, 3)))
    axes[0].set_ylabel("Overall fill A/O (%)")
    axes[1].plot(dates, u.shift_nominal, color=BLUE, linewidth=1.2, marker="o", markersize=2.5)
    axes[1].axhline(0, color=INK2, linewidth=0.8, linestyle=(0, (3, 3)))
    axes[1].set_ylabel("Maturity shift (days)")
    ex = u[u.event_id == "UG-1237"]
    if not ex.empty:
        d0 = pd.to_datetime(ex.held_date.iloc[0])
        axes[0].annotate("#1237", (d0, ex.fill_pct.iloc[0]), xytext=(-40, 14), textcoords="offset points",
                         fontsize=7.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.7))
        axes[1].annotate(f"#1237: {ex.shift_nominal.iloc[0]:+.0f} days", (d0, ex.shift_nominal.iloc[0]),
                         xytext=(-80, -4), textcoords="offset points", fontsize=7.5, color=INK,
                         arrowprops=dict(arrowstyle="-", color=INK2, lw=0.7))
    axes[0].set_title("Uganda: overall fill and accepted maturity mix, each bill auction (2022 onward, observed)",
                      fontsize=9, loc="left")
    _save(fig, paths, "fig3_uganda_timeline")


def make_figures(paths: Paths) -> None:
    fig_decomposition(paths)
    fig_maturity(paths)
    fig_timeline(paths)
