"""Generate ``data/sample_incidents/<incident_id>/`` directories from ``SCENARIOS``.

Each generated incident folder contains exactly four files:

    incident_metadata.json   — ticket-level facts (id, service, severity, ...)
    app.log                  — timestamped multi-component log lines
    metrics_snapshot.json    — per-minute time series for golden + scenario metrics
    expected_answer.json     — ground-truth label used for evaluation

Usage::

    python -m scripts.generate_incidents [--out data/sample_incidents]

Re-running is safe and produces byte-identical output (assuming the same
scenario definitions). Existing files are overwritten in place.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.generators import (
    build_app_log,
    build_expected_answer,
    build_incident_metadata,
    build_metrics_snapshot,
    ensure_dir,
    write_json,
    write_text,
)
from scripts.scenarios import SCENARIOS


DEFAULT_OUT = Path("data") / "sample_incidents"


def generate_one(scenario: dict, out_root: Path) -> Path:
    """Generate a single incident folder and return its path."""
    inc_dir = out_root / scenario["incident_id"]
    ensure_dir(inc_dir)

    write_json(inc_dir / "incident_metadata.json", build_incident_metadata(scenario))
    write_text(inc_dir / "app.log", build_app_log(scenario))
    write_json(inc_dir / "metrics_snapshot.json", build_metrics_snapshot(scenario))
    write_json(inc_dir / "expected_answer.json", build_expected_answer(scenario))

    return inc_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic MII incident folders from scripts.scenarios.SCENARIOS",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output directory (default: {DEFAULT_OUT})",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="Generate only the specified incident_id(s); may be passed multiple times.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_dir(args.out)

    scenarios = SCENARIOS
    if args.only:
        wanted = set(args.only)
        scenarios = [s for s in SCENARIOS if s["incident_id"] in wanted]
        missing = wanted - {s["incident_id"] for s in scenarios}
        if missing:
            print(f"error: unknown incident_id(s): {sorted(missing)}", file=sys.stderr)
            return 2

    for scenario in scenarios:
        path = generate_one(scenario, args.out)
        print(f"  wrote {path}")

    print(f"generated {len(scenarios)} incident(s) under {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
