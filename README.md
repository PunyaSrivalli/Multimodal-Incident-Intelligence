# Multimodal Incident Intelligence (MII)

## What this project does

MII is an AI-powered incident response assistant for engineering and on-call
teams. The end-state system will ingest mixed signals from a live incident
(application logs, metrics snapshots, alerts, runbooks, past postmortems)
and use an LLM to:

1. Triage active incidents and assess severity.
2. Generate root-cause hypotheses backed by cited evidence.
3. Retrieve the most relevant runbooks and similar past incidents.
4. Draft remediation steps the on-call can act on immediately.
5. Support evaluation and observability of the assistant itself.

## Why we start with synthetic data

We don't have access to real production logs, audio recordings of incident
calls, or screenshots of customer-impacting dashboards. Building the AI
pipeline against nothing — or against unrealistic toy data — would lead to
a system that demos well and fails in practice.

So Phase 0 deliberately ships **before** the AI: a small, hand-crafted,
realistic synthetic dataset that the rest of the system will be developed
and evaluated against. Each scenario covers a distinct, common failure
mode (database pool exhaustion, JVM out-of-memory, upstream rate limiting,
CPU saturation, host disk full) and ships with a ground-truth answer so
later AI components can be scored without human relabeling.

## What each incident package contains

Every folder under `data/sample_incidents/<INC-ID>/` is a self-contained
incident package with exactly four files:

| File | Purpose |
| --- | --- |
| `incident_metadata.json` | Ticket-level facts: id, title, severity, service, region, timestamps, on-call, alerts, customer impact, comms channels. |
| `app.log` | Timestamped multi-component log lines (`INFO` / `WARN` / `ERROR`) spanning the incident window, with realistic request IDs and stack traces. |
| `metrics_snapshot.json` | Per-minute time series for the golden signals (request rate, error rate, latency p50/p95/p99) plus scenario-specific metrics (DB pool, heap, queue depth, disk usage, …). |
| `expected_answer.json` | Ground-truth label used for evaluation: root-cause hypothesis, evidence citations, remediation steps, related runbooks, related past incidents, time-to-mitigate. |

The retrieval corpus lives separately under `data/knowledge_base/`:

- `runbooks/*.md` — reusable operational playbooks (symptoms, diagnostics,
  mitigation, rollback) that the retriever will rank.
- `past_incidents/*.json` — resolved incidents with postmortem-style notes,
  used to answer "have we seen this before?".
- `index.json` — lightweight catalogue across both, for the future
  retriever.

## What's coming next (LLM phase)

Once the synthetic dataset is stable, the next milestone wires in
**[Groq](https://groq.com/)** as the LLM inference provider. Groq is
chosen for its low-latency hosted inference of open-weight models, which
matters for an on-call assistant where time-to-first-suggestion is part of
the user experience. The pipeline will read the four files in an incident
package, retrieve the most relevant items from the knowledge base, and
prompt a Groq-hosted model to produce an `expected_answer.json`-shaped
response — which can then be scored against the ground-truth label that
ships with each scenario.

## Repository layout (current)

```
mii-platform/
├── README.md
├── requirements.txt
├── scripts/
│   ├── scenarios.py                # Hand-authored incident scenarios (source of truth)
│   ├── generators.py               # Shared helpers: timestamps, log lines, metric series
│   ├── generate_incidents.py       # Builds data/sample_incidents/<INC-ID>/
│   └── generate_knowledge_base.py  # Builds data/knowledge_base/{runbooks,past_incidents}/
└── data/
    ├── sample_incidents/
    │   └── INC-2026-0001/
    │       ├── incident_metadata.json
    │       ├── app.log
    │       ├── metrics_snapshot.json
    │       └── expected_answer.json
    └── knowledge_base/
        ├── runbooks/
        │   └── *.md
        └── past_incidents/
            └── *.json
```

The `backend/` and `frontend/` directories will be added in later phases —
they intentionally do not exist yet so this milestone can be reviewed and
merged on its own.

## Usage

```bash
# (Optional) create a venv
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt

# Regenerate everything under data/
python -m scripts.generate_incidents
python -m scripts.generate_knowledge_base
```

Both scripts are idempotent and seeded — re-running produces byte-identical
output. To add a new scenario, append a dict to `SCENARIOS` in
`scripts/scenarios.py` and re-run the generators.
