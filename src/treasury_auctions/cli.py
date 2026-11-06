"""Command-line entry point.

    python -m treasury_auctions inventory   # discover + freeze source inventories (network)
    python -m treasury_auctions fetch       # download in-scope documents into the cache (network)
    python -m treasury_auctions parse       # extract + parse cached bytes -> normalized tables
    python -m treasury_auctions audit       # reconciliation, coverage, discrepancy reports
    python -m treasury_auctions measure     # confirmatory measurement tables + figures
    python -m treasury_auctions evaluate    # chronological forecast evaluation
    python -m treasury_auctions report      # README story figures, verify tables, write run record
    python -m treasury_auctions story       # README story figures only (outputs/figures/readme)
    python -m treasury_auctions build       # parse -> audit -> measure -> evaluate -> report (offline)
    python -m treasury_auctions fixtures    # fixture-only integration run (no network, no cache)

Exit codes: 0 success, 1 stage failure, 2 usage error, 3 incomplete sources (strict mode).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import SNAPSHOT_CUTOFF, get_paths


def _cache(args, paths):
    from .fetch import SourceCache

    return SourceCache(paths.cache, offline=args.offline)


def cmd_inventory(args, paths) -> int:
    from .inventory import build_inventory

    meta = build_inventory(paths, _cache(args, paths), sources=tuple(args.source), workers=args.workers)
    print(json.dumps(meta, indent=1, default=str))
    return 0


def cmd_fetch(args, paths) -> int:
    from .inventory import fetch_inventory, fetch_summary

    man = fetch_inventory(paths, _cache(args, paths), countries=tuple(args.source), workers=args.workers,
                          limit=args.limit)
    summ = fetch_summary(man)
    print(summ.to_string())
    failed = int((man.fetch_status == "failed").sum() + (man.fetch_status == "missing_offline").sum())
    if failed:
        print(f"WARNING: {failed} documents not available; see data/frozen/fetch_manifest.csv", file=sys.stderr)
        return 3 if args.strict else 0
    return 0


def cmd_parse(args, paths) -> int:
    from .pipeline import run_parse

    cache = _cache(args, paths)
    if args.frozen:
        from .inventory import verify_frozen_sources

        print(f"Verified {verify_frozen_sources(paths, cache, args.workers)} frozen source URLs")
    run_parse(paths, cache, cutoff=args.cutoff, workers=args.workers)
    return 0


def cmd_audit(args, paths) -> int:
    from .audit import run_audit

    run_audit(paths, cutoff=args.cutoff)
    return 0


def cmd_measure(args, paths) -> int:
    from .analysis import run_measure

    run_measure(paths, offer_version=args.offer_version, seed=args.seed)
    return 0


def cmd_evaluate(args, paths) -> int:
    from .forecast import run_evaluate

    run_evaluate(paths, seed=args.seed, strict_timing=not args.lenient_timing,
                 reuse_predictions=args.reuse_predictions, publication_delay=args.publication_delay_weekdays)
    return 0


def cmd_story(args, paths) -> int:
    from .story_figures import make_story_figures

    print("\n".join(make_story_figures(paths)))
    return 0


def cmd_report(args, paths) -> int:
    from .report import run_report
    from .story_figures import make_story_figures

    make_story_figures(paths)

    ok = run_report(paths)
    return 0 if ok else 1


def cmd_build(args, paths) -> int:
    for fn in (cmd_parse, cmd_audit, cmd_measure, cmd_evaluate, cmd_report):
        t0 = time.time()
        rc = fn(args, paths)
        print(f"[{fn.__name__[4:]}] rc={rc} {time.time() - t0:.1f}s")
        if rc:
            return rc
    return 0


def cmd_rebuild_outputs(args, paths) -> int:
    """Regenerate analysis products from the released derived tables."""
    from .audit import offer_reconciliation

    offer_reconciliation(paths)
    for fn in (cmd_measure, cmd_evaluate, cmd_report):
        rc = fn(args, paths)
        if rc:
            return rc
    return 0


def cmd_fixtures(args, paths) -> int:
    from .fixtures_run import run_fixtures

    return 0 if run_fixtures(paths) else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="treasury_auctions", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", type=Path, help="project root (default: auto-detect / TBA_ROOT)")
    p.add_argument("--offline", action="store_true", help="never contact the network; use cache only")
    p.add_argument("--frozen", action="store_true",
                   help="parse/build: verify or recover the exact manifest bytes without refreshing the inventory")
    p.add_argument("--workers", type=int, default=4, help="bounded concurrency (max 6)")
    p.add_argument("--cutoff", default=SNAPSHOT_CUTOFF, help="research snapshot cutoff date (YYYY-MM-DD)")
    p.add_argument("--seed", type=int, default=20261106)
    p.add_argument("--source", nargs="+", default=["UG", "KE", "GH"], choices=["UG", "KE", "GH"])
    p.add_argument("--limit", type=int, help="fetch at most N documents per country (smoke tests)")
    p.add_argument("--strict", action="store_true", help="exit 3 if any source document is unavailable")
    p.add_argument("--offer-version", default="announced_or_result",
                   choices=["result", "announced", "announced_or_result"])
    p.add_argument("--lenient-timing", action="store_true",
                   help="exploratory: allow date-only availability proxies in forecasting")
    p.add_argument("--publication-delay-weekdays", type=int, default=0, choices=range(0, 6),
                   help="evaluate: delay result availability and offer publicity in the weekday sensitivity")
    p.add_argument("--reuse-predictions", action="store_true",
                   help="evaluate: rescore saved walk-forward predictions instead of refitting")
    p.add_argument("command", choices=["inventory", "fetch", "parse", "audit", "measure", "evaluate", "report",
                                       "story", "build", "rebuild-outputs", "fixtures"])
    args = p.parse_args(argv)
    if args.publication_delay_weekdays and (args.command != "evaluate" or args.lenient_timing):
        p.error("--publication-delay-weekdays requires evaluate with strict timing")
    paths = get_paths(args.root).ensure()
    fn = globals()[f"cmd_{args.command.replace('-', '_')}"]
    try:
        return fn(args, paths)
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"stage {args.command} failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
