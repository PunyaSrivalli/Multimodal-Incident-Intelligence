"""Generate the ``data/knowledge_base/`` tree from ``SCENARIOS``.

Layout produced::

    data/knowledge_base/
    ├── runbooks/
    │   ├── db_connection_pool_exhaustion.md
    │   ├── jvm_oom_and_memory_leak.md
    │   ├── upstream_rate_limiting.md
    │   ├── high_cpu_after_deploy.md
    │   └── host_disk_full.md
    ├── past_incidents/
    │   ├── INC-2025-0072.json
    │   ├── INC-2025-0119.json
    │   ├── INC-2025-0212.json
    │   ├── INC-2025-0288.json
    │   └── INC-2025-0301.json
    └── index.json   # lightweight catalogue for the future retriever

Usage::

    python -m scripts.generate_knowledge_base [--out data/knowledge_base]

Re-running is safe and produces byte-identical output.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from scripts.generators import (
    build_past_incident,
    build_runbook_markdown,
    ensure_dir,
    write_json,
    write_text,
)
from scripts.scenarios import SCENARIOS


DEFAULT_OUT = Path("data") / "knowledge_base"


def generate_runbooks(out_root: Path) -> list[dict]:
    """Write each scenario's runbook markdown under ``out_root/runbooks/``.

    Returns a list of catalogue entries for ``index.json``.
    """
    runbooks_dir = out_root / "runbooks"
    ensure_dir(runbooks_dir)

    entries: list[dict] = []
    seen_filenames: set[str] = set()
    for scenario in SCENARIOS:
        filename, content = build_runbook_markdown(scenario)
        if filename in seen_filenames:
            # Two scenarios pointing at the same runbook is fine in principle,
            # but the dataset is curated so this shouldn't happen yet. Surface
            # it loudly so authors notice.
            raise ValueError(f"duplicate runbook filename: {filename!r}")
        seen_filenames.add(filename)

        path = runbooks_dir / filename
        write_text(path, content)
        print(f"  wrote {path}")

        entries.append({
            "filename": filename,
            "title": scenario["runbook"]["title"],
            "tags": list(scenario["tags"]),
            "applies_to_services": [scenario["service"]],
            "source_incident_id": scenario["incident_id"],
        })

    return entries


def generate_past_incidents(out_root: Path) -> list[dict]:
    """Write each scenario's past_incident JSON under ``out_root/past_incidents/``.

    Returns a list of catalogue entries for ``index.json``.
    """
    past_dir = out_root / "past_incidents"
    ensure_dir(past_dir)

    entries: list[dict] = []
    seen_ids: set[str] = set()
    for scenario in SCENARIOS:
        filename, payload = build_past_incident(scenario)
        if payload["incident_id"] in seen_ids:
            raise ValueError(f"duplicate past_incident id: {payload['incident_id']!r}")
        seen_ids.add(payload["incident_id"])

        path = past_dir / filename
        write_json(path, payload)
        print(f"  wrote {path}")

        entries.append({
            "filename": filename,
            "incident_id": payload["incident_id"],
            "title": payload["title"],
            "service": payload["service"],
            "occurred_on": payload["occurred_on"],
            "tags": payload.get("tags", []),
            "related_runbooks": payload.get("related_runbooks", []),
        })

    return entries


def write_index(out_root: Path, runbooks: list[dict], past_incidents: list[dict]) -> Path:
    """Write a lightweight catalogue file for the future retriever to use."""
    index = {
        "version": "1.0",
        "runbooks": sorted(runbooks, key=lambda r: r["filename"]),
        "past_incidents": sorted(past_incidents, key=lambda p: p["incident_id"]),
    }
    path = out_root / "index.json"
    write_json(path, index)
    print(f"  wrote {path}")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the synthetic MII knowledge base (runbooks + past incidents)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output directory (default: {DEFAULT_OUT})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_dir(args.out)

    runbooks = generate_runbooks(args.out)
    past_incidents = generate_past_incidents(args.out)
    write_index(args.out, runbooks, past_incidents)

    print(
        f"generated {len(runbooks)} runbook(s) and "
        f"{len(past_incidents)} past incident(s) under {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
