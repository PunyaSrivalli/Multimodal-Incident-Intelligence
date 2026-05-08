"""Shared helpers used by ``generate_incidents`` and ``generate_knowledge_base``.

These functions take a scenario dict (see ``scripts.scenarios``) and produce
the concrete artefacts written to disk: incident metadata, app logs, metrics
snapshots, expected-answer ground truth, runbook markdown, and past-incident
JSON.

Everything here is pure (no I/O) except ``write_json`` and ``ensure_dir``.
That keeps the CLI scripts trivial — they just compose helpers and write the
result.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Time formatting
# ---------------------------------------------------------------------------
def fmt_iso_seconds(dt: datetime) -> str:
    """Format a tz-aware datetime as ``YYYY-MM-DDTHH:MM:SSZ`` (UTC)."""
    if dt.tzinfo is None:
        raise ValueError("expected tz-aware datetime")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt_iso_millis(dt: datetime) -> str:
    """Format a tz-aware datetime as ``YYYY-MM-DDTHH:MM:SS.mmmZ`` (UTC)."""
    if dt.tzinfo is None:
        raise ValueError("expected tz-aware datetime")
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{dt.microsecond // 1000:03d}Z"


def add_seconds(dt: datetime, offset_s: float) -> datetime:
    """Return ``dt + offset_s`` seconds, preserving tzinfo."""
    return dt + timedelta(seconds=offset_s)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def _seeded_rng(scenario: dict) -> random.Random:
    """Return a Random seeded deterministically from the scenario id.

    Used to add small jitter (e.g. log timestamp milliseconds) without making
    the output non-reproducible.
    """
    seed = int(hashlib.sha256(scenario["incident_id"].encode()).hexdigest(), 16)
    return random.Random(seed)


# ---------------------------------------------------------------------------
# Incident metadata
# ---------------------------------------------------------------------------
def build_incident_metadata(scenario: dict) -> dict[str, Any]:
    """Build the dict serialized to ``incident_metadata.json``."""
    started_at: datetime = scenario["started_at"]
    detected_at = add_seconds(started_at, scenario["detected_at_offset_s"])
    end_at = add_seconds(started_at, scenario["duration_minutes"] * 60)

    alerts = [
        {
            "alert_id": a["alert_id"],
            "name": a["name"],
            "severity": a["severity"],
            "fired_at": fmt_iso_seconds(add_seconds(started_at, a["fired_at_offset_s"])),
            "dimensions": a.get("dimensions", {}),
        }
        for a in scenario["alerts"]
    ]

    return {
        "incident_id": scenario["incident_id"],
        "title": scenario["title"],
        "severity": scenario["severity"],
        "status": "active",
        "service": scenario["service"],
        "environment": scenario["environment"],
        "region": scenario["region"],
        "started_at": fmt_iso_seconds(started_at),
        "detected_at": fmt_iso_seconds(detected_at),
        "window": {
            "start": fmt_iso_seconds(started_at),
            "end": fmt_iso_seconds(end_at),
            "duration_minutes": scenario["duration_minutes"],
        },
        "tags": list(scenario["tags"]),
        "reporter": scenario["reporter"],
        "on_call": scenario["on_call"],
        "customer_impact": scenario["customer_impact"],
        "channels": dict(scenario["channels"]),
        "alerts": alerts,
    }


# ---------------------------------------------------------------------------
# App log
# ---------------------------------------------------------------------------
_LEVEL_PAD = {"DEBUG": "DEBUG", "INFO": "INFO ", "WARN": "WARN ", "ERROR": "ERROR"}


def build_app_log(scenario: dict) -> str:
    """Render the ``app.log`` file contents for a scenario.

    Format per line::

        <ISO8601 millis>  <LEVEL>  [<component>]  [<request_id>]  <message>

    Multi-line messages (e.g. stack traces) are preserved as-is; the prefix
    is only emitted on the first line so the file remains valid for line-by-
    line parsing of normal entries while still capturing exception traces.
    """
    started_at: datetime = scenario["started_at"]
    rng = _seeded_rng(scenario)

    out_lines: list[str] = []
    for entry in scenario["logs"]:
        # Add a small deterministic millisecond jitter so timestamps look
        # realistic without breaking reproducibility.
        jitter_ms = rng.randint(0, 999)
        ts = add_seconds(started_at, entry["offset_s"]) + timedelta(milliseconds=jitter_ms)

        level = _LEVEL_PAD.get(entry["level"], entry["level"])
        component = entry["component"]
        request_id = entry.get("request_id")
        rid_part = f"[{request_id}] " if request_id else ""

        message = entry["message"]
        first, *rest = message.split("\n")
        prefix = f"{fmt_iso_millis(ts)}  {level}  [{component}]  {rid_part}"
        out_lines.append(prefix + first)
        # Keep trailing lines indented under the same record (no prefix). Many
        # log readers display them as continuation lines of the previous log
        # event, which is how stack traces look in production.
        for tail in rest:
            out_lines.append("\t" + tail)

    return "\n".join(out_lines) + "\n"


# ---------------------------------------------------------------------------
# Metrics snapshot
# ---------------------------------------------------------------------------
def _infer_unit(metric_name: str) -> str:
    name = metric_name.lower()
    if name.endswith("_rps"):
        return "rps"
    if name.endswith("_pct") or "_pct_" in name:
        return "percent"
    if name.endswith("_seconds"):
        return "seconds"
    if name.endswith("_ms") or "_ms_" in name or name.endswith("_ms_p95") or name.endswith("_ms_p99"):
        return "ms"
    if name.endswith("_bytes_mb"):
        return "MB"
    if name.endswith("_bytes"):
        return "bytes"
    if name.endswith("_total") or name.endswith("_count"):
        return "count"
    return "count"


def _series_summary(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "first": round(values[0], 4),
        "last": round(values[-1], 4),
        "delta": round(values[-1] - values[0], 4),
    }


def build_metrics_snapshot(scenario: dict) -> dict[str, Any]:
    """Build the dict serialized to ``metrics_snapshot.json``."""
    started_at: datetime = scenario["started_at"]
    duration_minutes: int = scenario["duration_minutes"]
    end_at = add_seconds(started_at, duration_minutes * 60)

    timestamps = [
        fmt_iso_seconds(add_seconds(started_at, i * 60))
        for i in range(duration_minutes)
    ]

    series_out: dict[str, dict[str, Any]] = {}
    for name, values in scenario["metrics_series"].items():
        if len(values) != duration_minutes:
            raise ValueError(
                f"scenario {scenario['incident_id']!r}: metric {name!r} has "
                f"{len(values)} points, expected {duration_minutes}"
            )
        series_out[name] = {
            "unit": _infer_unit(name),
            "values": list(values),
            "summary": _series_summary(values),
        }

    return {
        "service": scenario["service"],
        "environment": scenario["environment"],
        "region": scenario["region"],
        "window": {
            "start": fmt_iso_seconds(started_at),
            "end": fmt_iso_seconds(end_at),
            "step_seconds": 60,
            "num_points": duration_minutes,
        },
        "timestamps": timestamps,
        "series": series_out,
    }


# ---------------------------------------------------------------------------
# Expected answer (ground truth)
# ---------------------------------------------------------------------------
def build_expected_answer(scenario: dict) -> dict[str, Any]:
    """Build the dict serialized to ``expected_answer.json``."""
    answer = dict(scenario["expected_answer"])
    return {
        "incident_id": scenario["incident_id"],
        "ground_truth_version": "1.0",
        **answer,
    }


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
def build_runbook_markdown(scenario: dict) -> tuple[str, str]:
    """Return ``(filename, markdown_content)`` for a scenario's runbook."""
    rb = scenario["runbook"]
    return rb["filename"], rb["content_md"]


def build_past_incident(scenario: dict) -> tuple[str, dict[str, Any]]:
    """Return ``(filename, json_dict)`` for a scenario's past-incident record."""
    p = dict(scenario["past_incident"])
    filename = f"{p['incident_id']}.json"
    return filename, p


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------
def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: Any) -> None:
    """Write ``obj`` as pretty-printed JSON with a trailing newline."""
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_text(path: Path, text: str) -> None:
    """Write a UTF-8 text file, ensuring it ends with a single newline."""
    ensure_dir(path.parent)
    if not text.endswith("\n"):
        text = text + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
