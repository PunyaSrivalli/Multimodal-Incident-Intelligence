"""Source-of-truth definitions for MII synthetic incidents.

A scenario is a single Python dict that fully describes one incident plus the
knowledge-base artefacts (runbook + past incident) associated with that
failure mode. The generator scripts in this package are deliberately dumb
renderers over these dicts so adding a new failure mode is a matter of
appending one entry to ``SCENARIOS``.

Schema (per scenario)::

    {
        "incident_id": str,              # e.g. "INC-2026-0001"
        "title": str,
        "severity": "SEV-1" | "SEV-2" | "SEV-3",
        "service": str,
        "environment": str,
        "region": str,
        "started_at": datetime,          # t0 of the incident (UTC, tz-aware)
        "detected_at_offset_s": int,     # seconds after started_at
        "duration_minutes": int,         # length of the metrics/log window
        "tags": list[str],
        "reporter": str,
        "on_call": str,
        "customer_impact": str,
        "channels": dict,
        "alerts": list[dict],            # each dict described in generators.py
        "logs": list[dict],              # each dict: offset_s, level, component, request_id|None, message
        "metrics_series": dict,          # metric_name -> list[float], length == duration_minutes
        "expected_answer": dict,
        "runbook": {"filename": str, "title": str, "content_md": str},
        "past_incident": dict,
    }
"""
from __future__ import annotations

from datetime import datetime, timezone


# All scenarios anchor to this base date so output is reproducible across runs.
_BASE = datetime(2026, 5, 4, 14, 23, 11, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Scenario 1 — payments-api: HikariCP database pool exhaustion
# ---------------------------------------------------------------------------
_SCENARIO_PAYMENTS_DB_POOL = {
    "incident_id": "INC-2026-0001",
    "title": "Elevated 5xx errors and p99 latency on payments-api",
    "severity": "SEV-2",
    "service": "payments-api",
    "environment": "production",
    "region": "us-east-1",
    "started_at": _BASE,
    "detected_at_offset_s": 168,
    "duration_minutes": 20,
    "tags": ["database", "hikari", "latency", "5xx", "checkout"],
    "reporter": "pagerduty",
    "on_call": "alice.nguyen@example.com",
    "customer_impact": (
        "~12% of POST /charge requests returning 503; checkout client retries "
        "are succeeding for most users, but ~40 customers have reported "
        "failed payments via support."
    ),
    "channels": {
        "slack": "#inc-2026-0001",
        "war_room": "https://meet.example.com/inc-2026-0001",
        "status_page": "https://status.example.com/incidents/2026-0001",
    },
    "alerts": [
        {"alert_id": "alert-pa-001", "name": "PaymentsAPI_HighErrorRate",
         "severity": "warning", "fired_at_offset_s": 168,
         "dimensions": {"service": "payments-api", "env": "production"}},
        {"alert_id": "alert-pa-002", "name": "PaymentsAPI_HighLatencyP99",
         "severity": "warning", "fired_at_offset_s": 240,
         "dimensions": {"service": "payments-api", "env": "production"}},
        {"alert_id": "alert-pa-003", "name": "PaymentsAPI_DBPoolSaturated",
         "severity": "critical", "fired_at_offset_s": 480,
         "dimensions": {"service": "payments-api", "pool": "HikariPool-1"}},
    ],
    "logs": [
        {"offset_s": 5,   "level": "INFO",  "component": "payments-api",       "request_id": "req-7af2c1", "message": "POST /charge user_id=u-10231 amount=49.95 currency=USD"},
        {"offset_s": 12,  "level": "DEBUG", "component": "payments-api.db",    "request_id": "req-7af2c1", "message": "HikariPool-1 acquired connection (used=42/100, idle=58)"},
        {"offset_s": 18,  "level": "INFO",  "component": "payments-api",       "request_id": "req-7af2c1", "message": "POST /charge -> 200 in 87ms"},
        {"offset_s": 60,  "level": "INFO",  "component": "payments-api",       "request_id": "req-1c83de", "message": "POST /charge user_id=u-10288 amount=12.00 currency=USD"},
        {"offset_s": 90,  "level": "INFO",  "component": "payments-api.db",    "request_id": None,        "message": "background job 'reconcile_pending_charges' started (last_run=12h ago)"},
        {"offset_s": 240, "level": "WARN",  "component": "payments-api.db",    "request_id": "req-9b1e44", "message": "HikariPool-1 connection acquire took 1812ms (threshold=500ms, used=88/100)"},
        {"offset_s": 305, "level": "WARN",  "component": "payments-api.db",    "request_id": "req-44f0aa", "message": "HikariPool-1 connection acquire took 2940ms (threshold=500ms, used=94/100)"},
        {"offset_s": 360, "level": "WARN",  "component": "payments-api",       "request_id": "req-44f0aa", "message": "POST /charge -> 200 in 3105ms (slow)"},
        {"offset_s": 410, "level": "INFO",  "component": "payments-api.db",    "request_id": None,        "message": "long-running query observed: SELECT ... FROM charges WHERE status='pending' (running for 412s, pid=18821)"},
        {"offset_s": 470, "level": "WARN",  "component": "payments-api.db",    "request_id": "req-2e9c01", "message": "HikariPool-1 connection acquire took 7805ms (used=100/100, pending=14)"},
        {"offset_s": 482, "level": "ERROR", "component": "payments-api.db",    "request_id": "req-2e9c01", "message": "HikariPool-1 - Connection is not available, request timed out after 30000ms (active=100, idle=0, waiting=18)"},
        {"offset_s": 482, "level": "ERROR", "component": "payments-api",       "request_id": "req-2e9c01", "message": "POST /charge -> 503 in 30041ms (db connection timeout)"},
        {"offset_s": 511, "level": "ERROR", "component": "payments-api.db",    "request_id": "req-810b22","message": "HikariPool-1 - Connection is not available, request timed out after 30000ms"},
        {"offset_s": 540, "level": "ERROR", "component": "payments-api",       "request_id": "req-810b22","message": "POST /charge -> 503 in 30012ms (db connection timeout)"},
        {"offset_s": 612, "level": "ERROR", "component": "payments-api.db",    "request_id": None,        "message": "java.sql.SQLTransientConnectionException: HikariPool-1 - Connection is not available, request timed out after 30000ms\n\tat com.zaxxer.hikari.pool.HikariPool.createTimeoutException(HikariPool.java:686)\n\tat com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:179)\n\tat com.example.payments.ChargeRepository.insert(ChargeRepository.java:88)"},
        {"offset_s": 700, "level": "WARN",  "component": "payments-api.metrics","request_id": None,       "message": "metric db_pool_active=100 db_pool_idle=0 db_pool_waiting=22 over 60s window"},
        {"offset_s": 760, "level": "INFO",  "component": "payments-api.db",    "request_id": None,        "message": "long-running query still active: pid=18821, runtime=762s, query=SELECT ... FROM charges WHERE status='pending' ORDER BY created_at"},
        {"offset_s": 820, "level": "ERROR", "component": "payments-api",       "request_id": "req-554d10","message": "POST /charge -> 503 in 30008ms (db connection timeout)"},
        {"offset_s": 905, "level": "WARN",  "component": "payments-api.kafka", "request_id": None,        "message": "publish to topic 'charge.completed' lagging by 612 messages (consumer is healthy)"},
        {"offset_s": 980, "level": "ERROR", "component": "payments-api",       "request_id": "req-2210ff","message": "POST /charge -> 503 in 30019ms (db connection timeout)"},
        {"offset_s": 1080,"level": "ERROR", "component": "payments-api.db",    "request_id": None,        "message": "circuit breaker 'charges-write' transitioned CLOSED -> OPEN after 50 consecutive failures in 60s"},
        {"offset_s": 1150,"level": "WARN",  "component": "payments-api",       "request_id": "req-cc8801","message": "POST /charge -> 503 in 12ms (circuit-open: charges-write)"},
    ],
    # 20 per-minute samples for each metric. Index 0 = minute starting at t0.
    "metrics_series": {
        "request_rate_rps":     [118, 121, 119, 122, 124, 120, 117, 119, 116, 113, 109, 106, 101,  98,  92,  88,  85,  84,  82,  80],
        "error_rate_pct":       [0.1, 0.1, 0.2, 0.1, 0.1, 0.2, 0.3, 0.5, 1.4, 3.8, 7.9,12.4,18.6,24.1,29.5,33.0,34.2,35.0,35.4,35.8],
        "latency_p50_ms":       [ 45,  47,  46,  48,  49,  47,  52,  61,  88, 142, 220, 305, 410, 520, 610, 680, 720, 745, 760, 770],
        "latency_p95_ms":       [110, 115, 112, 118, 120, 117, 138, 175, 330, 880,2200,5800,11000,18000,24000,28000,29500,30000,30000,30000],
        "latency_p99_ms":       [180, 188, 184, 192, 196, 190, 240, 320, 720,2100,6800,15000,24000,29000,30000,30000,30000,30000,30000,30000],
        "cpu_usage_pct":        [ 32,  33,  31,  34,  33,  32,  31,  30,  28,  26,  24,  22,  20,  19,  18,  18,  17,  17,  17,  16],
        "memory_usage_pct":     [ 58,  58,  59,  59,  58,  59,  59,  60,  60,  61,  61,  62,  62,  62,  63,  63,  63,  63,  63,  63],
        "db_pool_active":       [ 38,  41,  40,  43,  42,  44,  52,  68,  84,  93,  98, 100, 100, 100, 100, 100, 100, 100, 100, 100],
        "db_pool_idle":         [ 62,  59,  60,  57,  58,  56,  48,  32,  16,   7,   2,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "db_pool_waiting":      [  0,   0,   0,   0,   0,   0,   0,   1,   3,   8,  14,  22,  26,  28,  29,  30,  30,  30,  30,  30],
        "db_pool_wait_ms_p95":  [  4,   5,   4,   6,   5,   6,  18,  92, 480,1500,4800,12000,22000,29000,30000,30000,30000,30000,30000,30000],
    },
    "expected_answer": {
        "root_cause_hypothesis": (
            "A long-running maintenance query against the `charges` table "
            "(pid=18821, started ~14:30 UTC) is holding a HikariCP connection "
            "and blocking concurrent inserts. As background reconciliation "
            "workers also borrow connections, the 100-connection pool "
            "saturates around 14:31:11 UTC. Subsequent /charge requests wait "
            "30s on `getConnection`, time out, and surface as 503s; the "
            "`charges-write` circuit breaker eventually opens, fast-failing "
            "the rest."
        ),
        "confidence": 0.86,
        "evidence": [
            "app.log @ +410s: 'long-running query observed: SELECT ... FROM charges WHERE status=pending (running for 412s, pid=18821)'",
            "app.log @ +482s: 'HikariPool-1 - Connection is not available, request timed out after 30000ms (active=100, idle=0, waiting=18)'",
            "metrics: db_pool_active hits 100/100 at minute 11 and stays saturated through end of window",
            "metrics: db_pool_wait_ms_p95 jumps from 18ms to 30000ms between minute 6 and minute 12",
            "metrics: error_rate_pct goes from 0.3% to 35% over the same window while request_rate_rps trends down (clients giving up / circuit open)",
            "app.log @ +1080s: 'circuit breaker charges-write transitioned CLOSED -> OPEN after 50 consecutive failures in 60s'",
        ],
        "remediation_steps": [
            "1. In a read replica, confirm the long-running query: SELECT pid, now()-query_start AS runtime, query FROM pg_stat_activity WHERE state='active' ORDER BY runtime DESC.",
            "2. Coordinate with the data team and `pg_cancel_backend(18821)` (or `pg_terminate_backend` if cancel is ignored).",
            "3. Watch `db_pool_active` recover toward baseline (~40). Pool should drain within 60s once the blocking query is killed.",
            "4. Manually close the `charges-write` circuit breaker via the admin endpoint once error rate drops below 1%.",
            "5. File a follow-up to add a `statement_timeout` on the maintenance role and to gate the `reconcile_pending_charges` job behind a connection-budget check.",
        ],
        "related_runbooks": ["db_connection_pool_exhaustion.md"],
        "related_past_incidents": ["INC-2025-0119"],
        "severity_assessment": "SEV-2",
        "estimated_time_to_mitigate_minutes": 15,
        "impacted_services": ["payments-api", "checkout-web", "orders-api"],
        "impacted_users_estimate": "1k-5k checkout attempts affected",
    },
    "runbook": {
        "filename": "db_connection_pool_exhaustion.md",
        "title": "Database connection pool exhaustion",
        "content_md": """# Runbook: Database connection pool exhaustion

**Applies to:** any service backed by HikariCP / pgbouncer / similar
connection pools (payments-api, orders-api, billing-api).

## Symptoms

- `error_rate_pct` climbing while `request_rate_rps` is flat or falling.
- p95 / p99 latency pinned near the pool acquire timeout (default 30s).
- Logs containing `HikariPool-...Connection is not available, request timed out`.
- Metric `db_pool_active` at or near `db_pool_max` and `db_pool_waiting > 0`.
- Circuit breakers for write paths flipping to OPEN.

## Diagnose

1. Confirm pool saturation in metrics:
   `db_pool_active / db_pool_max >= 0.95` for at least 2 consecutive minutes.
2. Find blocking sessions on the database:
   ```sql
   SELECT pid, usename, application_name, state,
          now() - query_start AS runtime, wait_event, query
   FROM pg_stat_activity
   WHERE state <> 'idle'
   ORDER BY runtime DESC NULLS LAST
   LIMIT 20;
   ```
3. Check for recently started maintenance / batch jobs that hold long
   transactions (e.g. reconciliation, ETL, schema migrations).
4. Rule out a traffic spike: if `request_rate_rps` is also up >2x baseline,
   the pool may simply be under-sized rather than blocked.

## Mitigate

1. **If a single long-running query is blocking the pool**, cancel it:
   `SELECT pg_cancel_backend(<pid>);` then `pg_terminate_backend(<pid>)` if
   it does not yield within 30s.
2. **If the cause is a runaway batch job**, pause the job (feature flag or
   scheduler) before killing connections so it does not retry immediately.
3. **If the cause is genuine load**, scale the pool *and* the database
   carefully — increasing pool size on an already-hot DB makes things worse.
4. Manually re-close any tripped circuit breakers via the admin endpoint
   once `error_rate_pct < 1%` for 2 minutes.

## Rollback / verify

- `db_pool_active` returns to baseline (typically 30-50% of max).
- `error_rate_pct < 0.5%` and `latency_p99_ms` back under SLO.
- No new `Connection is not available` errors for 5 minutes.

## Prevent

- Enforce `statement_timeout` on maintenance / reporting database roles.
- Cap concurrency on background jobs that touch hot tables.
- Alert on `db_pool_active / db_pool_max > 0.8` *before* it saturates.
- Track p95 of `db_pool_wait_ms` as a leading indicator.
""",
    },
    "past_incident": {
        "incident_id": "INC-2025-0119",
        "title": "payments-api 503s caused by stuck reconciliation query",
        "service": "payments-api",
        "occurred_on": "2025-11-18",
        "severity": "SEV-2",
        "duration_minutes": 28,
        "tags": ["database", "hikari", "5xx", "reconciliation"],
        "summary": (
            "A nightly reconciliation job ran during peak traffic after a "
            "scheduler change, took ~22 minutes, and held a connection "
            "blocking concurrent /charge inserts. HikariPool-1 saturated at "
            "100/100 and /charge began returning 503s for ~12 minutes."
        ),
        "resolution": (
            "Killed the reconciliation backend with pg_terminate_backend, "
            "manually re-closed the charges-write circuit breaker, and "
            "rolled back the scheduler change. Permanent fix: moved "
            "reconciliation to the read replica and added a "
            "statement_timeout of 5m on the maintenance role."
        ),
        "follow_ups": [
            "Add statement_timeout to maintenance DB role (DONE)",
            "Move reconciliation job to read replica (DONE)",
            "Alert on db_pool_active/max > 0.8 (DONE)",
        ],
        "related_runbooks": ["db_connection_pool_exhaustion.md"],
    },
}


# ---------------------------------------------------------------------------
# Scenario 2 — checkout-service: heap leak / OOMKilled pods
# ---------------------------------------------------------------------------
_SCENARIO_CHECKOUT_OOM = {
    "incident_id": "INC-2026-0002",
    "title": "checkout-service pods OOMKilled, intermittent 502s on /cart",
    "severity": "SEV-2",
    "service": "checkout-service",
    "environment": "production",
    "region": "us-west-2",
    "started_at": _BASE.replace(day=5, hour=9, minute=2, second=44),
    "detected_at_offset_s": 360,
    "duration_minutes": 20,
    "tags": ["memory", "oom", "kubernetes", "5xx", "deploy"],
    "reporter": "datadog-monitor",
    "on_call": "ben.okafor@example.com",
    "customer_impact": (
        "Intermittent 502s on /cart and /checkout during pod restarts. "
        "Each restart drops ~30s of in-flight requests; sticky sessions "
        "mitigate impact but ~3% of users see a blank cart."
    ),
    "channels": {
        "slack": "#inc-2026-0002",
        "war_room": "https://meet.example.com/inc-2026-0002",
        "status_page": "https://status.example.com/incidents/2026-0002",
    },
    "alerts": [
        {"alert_id": "alert-co-001", "name": "Checkout_PodOOMKilled",
         "severity": "critical", "fired_at_offset_s": 360,
         "dimensions": {"service": "checkout-service", "namespace": "checkout"}},
        {"alert_id": "alert-co-002", "name": "Checkout_HighGCPause",
         "severity": "warning", "fired_at_offset_s": 240,
         "dimensions": {"service": "checkout-service"}},
        {"alert_id": "alert-co-003", "name": "Checkout_5xxSpike",
         "severity": "warning", "fired_at_offset_s": 420,
         "dimensions": {"service": "checkout-service"}},
    ],
    "logs": [
        {"offset_s": 8,    "level": "INFO",  "component": "checkout-service",        "request_id": "req-aa01", "message": "GET /cart user_id=u-77810 -> 200 in 42ms"},
        {"offset_s": 30,   "level": "INFO",  "component": "checkout-service.deploy", "request_id": None,       "message": "rollout checkout-service v2026.05.04 (image sha=8a1c2d) reached 100% on canary"},
        {"offset_s": 90,   "level": "DEBUG", "component": "checkout-service.cache",  "request_id": None,       "message": "in-memory CartCache size=12483 entries"},
        {"offset_s": 180,  "level": "INFO",  "component": "checkout-service.jvm",    "request_id": None,       "message": "G1 GC young pause 48ms, heap 1.6GB/2.0GB"},
        {"offset_s": 240,  "level": "WARN",  "component": "checkout-service.jvm",    "request_id": None,       "message": "G1 GC mixed pause 312ms, heap 1.84GB/2.0GB (after=1.78GB)"},
        {"offset_s": 260,  "level": "DEBUG", "component": "checkout-service.cache",  "request_id": None,       "message": "in-memory CartCache size=58742 entries"},
        {"offset_s": 305,  "level": "WARN",  "component": "checkout-service.jvm",    "request_id": None,       "message": "G1 GC mixed pause 612ms, heap 1.93GB/2.0GB (after=1.89GB) - reclaim ratio low"},
        {"offset_s": 330,  "level": "WARN",  "component": "checkout-service",        "request_id": "req-bb22", "message": "GET /cart -> 200 in 1820ms (slow, gc-pause-correlated)"},
        {"offset_s": 355,  "level": "ERROR", "component": "checkout-service.jvm",    "request_id": None,       "message": "java.lang.OutOfMemoryError: Java heap space\n\tat com.example.checkout.cache.CartCache.put(CartCache.java:71)\n\tat com.example.checkout.handler.CartHandler.getCart(CartHandler.java:142)"},
        {"offset_s": 360,  "level": "ERROR", "component": "kubelet",                 "request_id": None,       "message": "container checkout-service-7c9d-xn4 OOMKilled (memory cgroup limit=2Gi, usage=2.0Gi)"},
        {"offset_s": 362,  "level": "INFO",  "component": "kubelet",                 "request_id": None,       "message": "restarting container checkout-service-7c9d-xn4 (restartCount=1)"},
        {"offset_s": 380,  "level": "WARN",  "component": "checkout-service",        "request_id": "req-cc33", "message": "GET /cart -> 502 in 12ms (upstream connection refused: pod terminating)"},
        {"offset_s": 410,  "level": "INFO",  "component": "checkout-service",        "request_id": None,       "message": "service starting on port 8080 (build=v2026.05.04, sha=8a1c2d)"},
        {"offset_s": 470,  "level": "DEBUG", "component": "checkout-service.cache",  "request_id": None,       "message": "in-memory CartCache size=24110 entries"},
        {"offset_s": 540,  "level": "WARN",  "component": "checkout-service.jvm",    "request_id": None,       "message": "G1 GC mixed pause 410ms, heap 1.79GB/2.0GB"},
        {"offset_s": 612,  "level": "DEBUG", "component": "checkout-service.cache",  "request_id": None,       "message": "in-memory CartCache size=61204 entries"},
        {"offset_s": 690,  "level": "ERROR", "component": "checkout-service.jvm",    "request_id": None,       "message": "java.lang.OutOfMemoryError: Java heap space"},
        {"offset_s": 695,  "level": "ERROR", "component": "kubelet",                 "request_id": None,       "message": "container checkout-service-7c9d-xn4 OOMKilled (memory cgroup limit=2Gi, usage=2.0Gi)"},
        {"offset_s": 700,  "level": "INFO",  "component": "kubelet",                 "request_id": None,       "message": "restarting container checkout-service-7c9d-xn4 (restartCount=2)"},
        {"offset_s": 820,  "level": "WARN",  "component": "checkout-service.cache",  "request_id": None,       "message": "CartCache eviction policy=NONE; consider bounding via maxSize or weakKeys (ref: PR #4421 reverted)"},
        {"offset_s": 920,  "level": "DEBUG", "component": "checkout-service.cache",  "request_id": None,       "message": "in-memory CartCache size=43890 entries"},
        {"offset_s": 1020, "level": "WARN",  "component": "checkout-service.jvm",    "request_id": None,       "message": "G1 GC mixed pause 740ms, heap 1.91GB/2.0GB (after=1.88GB)"},
        {"offset_s": 1100, "level": "ERROR", "component": "checkout-service.jvm",    "request_id": None,       "message": "java.lang.OutOfMemoryError: Java heap space"},
        {"offset_s": 1108, "level": "ERROR", "component": "kubelet",                 "request_id": None,       "message": "container checkout-service-7c9d-xn4 OOMKilled (restartCount=3, backoff=20s)"},
    ],
    "metrics_series": {
        "request_rate_rps":     [82,  84,  83,  85,  84,  86,  82,  72,  79,  80,  68,  74,  80,  79,  62,  73,  80,  78,  64,  72],
        "error_rate_pct":       [0.05,0.04,0.06,0.05,0.04,0.05,0.18,3.20,1.10,0.20,4.40,1.50,0.30,0.40,5.20,1.80,0.50,0.60,5.80,2.00],
        "latency_p50_ms":       [38,  39,  40,  38,  41,  40,  62,  88,  44,  43,  92,  60,  46,  47,  98,  64,  50,  51, 102,  66],
        "latency_p95_ms":       [110, 112, 115, 113, 118, 116, 320, 980, 230, 145, 1100, 410, 250, 260, 1180, 460, 280, 290, 1200, 480],
        "latency_p99_ms":       [180, 184, 188, 186, 192, 190, 720, 2400, 480, 280, 2600, 880, 520, 540, 2700, 920, 560, 580, 2800, 940],
        "cpu_usage_pct":        [44,  45,  44,  46,  45,  47,  62,  72,  50,  48,  68,  56,  50,  51,  70,  58,  52,  53,  71,  59],
        "memory_usage_pct":     [62,  68,  74,  80,  87,  93,  99,  35,  58,  74,  99,  40,  62,  78,  99,  44,  64,  80,  99,  48],
        "heap_used_bytes_mb":   [1240,1360,1480,1600,1740,1860,1990, 700,1160,1480,1990, 800,1240,1560,1990, 880,1280,1600,1990, 960],
        "gc_pause_ms_p95":      [60,  62,  68,  84, 145, 245, 415, 612, 220, 180, 480, 240, 200, 220, 540, 260, 220, 240, 580, 280],
        "pod_restarts_total":   [0,   0,   0,   0,   0,   0,   1,   1,   1,   1,   2,   2,   2,   2,   3,   3,   3,   3,   4,   4],
    },
    "expected_answer": {
        "root_cause_hypothesis": (
            "Build v2026.05.04 (sha=8a1c2d) shipped a regression in "
            "`CartCache` where the eviction policy was removed (see log "
            "@+820s: 'eviction policy=NONE; consider bounding ... ref: PR "
            "#4421 reverted'). Cache entries grow unbounded with traffic, "
            "the JVM heap fills, GC pauses lengthen, and the pod is "
            "OOMKilled by the kubelet at the 2Gi cgroup limit. Each restart "
            "starts the leak from scratch, producing the sawtooth pattern "
            "in `heap_used_bytes_mb` and `pod_restarts_total`."
        ),
        "confidence": 0.91,
        "evidence": [
            "app.log @ +30s: rollout checkout-service v2026.05.04 (sha=8a1c2d) reached 100%",
            "app.log @ +260s/+612s/+920s: CartCache size keeps climbing across restarts (12k -> 58k -> 61k -> 43k)",
            "app.log @ +355s: java.lang.OutOfMemoryError originating in CartCache.put",
            "app.log @ +360s/+695s/+1108s: kubelet OOMKilled events at restartCount 1, 2, 3",
            "metrics: heap_used_bytes_mb shows clear sawtooth (1990 -> drop -> climb) every ~5 minutes",
            "metrics: pod_restarts_total grows monotonically from 0 to 4 over the window",
            "app.log @ +820s explicitly references the responsible PR (#4421) being reverted from a guard",
        ],
        "remediation_steps": [
            "1. Roll back checkout-service to the previous green build (v2026.05.03) via the deploy tool: `deploy rollback checkout-service --to v2026.05.03`.",
            "2. Watch `pod_restarts_total` stop incrementing and `heap_used_bytes_mb` stabilize below 1.6GB.",
            "3. As a safety net while rollback propagates, raise the memory limit to 3Gi to give pods headroom (`kubectl set resources deploy/checkout-service --limits=memory=3Gi`).",
            "4. Open a P1 ticket against the checkout team to re-introduce the bounded cache (Caffeine maxSize or WeakHashMap) before re-rolling forward.",
            "5. Add a heap dump on OOM (`-XX:+HeapDumpOnOutOfMemoryError`) so future occurrences are diagnosable from artefacts, not logs.",
        ],
        "related_runbooks": ["jvm_oom_and_memory_leak.md"],
        "related_past_incidents": ["INC-2025-0072"],
        "severity_assessment": "SEV-2",
        "estimated_time_to_mitigate_minutes": 10,
        "impacted_services": ["checkout-service", "checkout-web"],
        "impacted_users_estimate": "~3% of active sessions during pod restarts",
    },
    "runbook": {
        "filename": "jvm_oom_and_memory_leak.md",
        "title": "JVM OutOfMemoryError / pods OOMKilled",
        "content_md": """# Runbook: JVM OOM / pods OOMKilled

**Applies to:** JVM services running on Kubernetes with a memory cgroup
limit (checkout-service, recommendations-service, search-api).

## Symptoms

- `kubelet` log lines: `container ... OOMKilled (memory cgroup limit=...)`.
- Application log: `java.lang.OutOfMemoryError: Java heap space`.
- `pod_restarts_total` increasing every few minutes.
- `heap_used_bytes_mb` shows a sawtooth that approaches the limit each
  cycle.
- `gc_pause_ms_p95` climbing in the run-up to each crash.

## Diagnose

1. Identify whether the issue started with a deploy:
   - Cross-reference `service.deploy` log lines or the deploy tool against
     the time `pod_restarts_total` first started growing.
2. Determine whether it is a leak or a single oversize allocation:
   - **Leak**: heap grows monotonically across requests; OOM occurs after
     N minutes of steady-state traffic; cache/queue size metrics correlate.
   - **Oversize allocation**: OOM occurs on a specific request type; heap
     was healthy seconds before the crash.
3. Look for unbounded data structures: `cache size`, `queue depth`,
   thread-locals, request-scoped buffers.
4. If a heap dump is available (`-XX:+HeapDumpOnOutOfMemoryError`), open it
   in Eclipse MAT or VisualVM to identify the dominator.

## Mitigate

1. **If a recent deploy is the cause**: roll back. Don't try to forward-fix
   in the middle of the incident.
2. **If rollback isn't possible**: temporarily raise the memory limit by
   ~50% to slow the crash loop. This buys time for diagnosis but does not
   solve the underlying leak.
3. **Drain affected pods gracefully** (don't `kubectl delete --force`)
   so in-flight requests finish or get retried by the load balancer.

## Rollback / verify

- `pod_restarts_total` flat for 10 minutes.
- `heap_used_bytes_mb` plateaus well below the limit (target <80%).
- `error_rate_pct < 0.5%` for 5 minutes.

## Prevent

- Enable `-XX:+HeapDumpOnOutOfMemoryError` and ship dumps to object
  storage with a TTL so future OOMs are diagnosable post-hoc.
- Bound any in-process cache with an eviction policy (Caffeine `maxSize`
  or `expireAfterWrite`).
- Alert on `heap_used_bytes_mb / heap_max_bytes_mb > 0.85` for 5 min as a
  leading indicator before OOM.
""",
    },
    "past_incident": {
        "incident_id": "INC-2025-0072",
        "title": "checkout-service OOM after recommendation cache change",
        "service": "checkout-service",
        "occurred_on": "2025-08-09",
        "severity": "SEV-2",
        "duration_minutes": 41,
        "tags": ["memory", "oom", "deploy", "cache"],
        "summary": (
            "A change to RecommendationCache replaced the bounded Caffeine "
            "cache with a plain ConcurrentHashMap. Heap grew steadily over "
            "~30 minutes until pods hit the 2Gi cgroup limit and the "
            "kubelet started OOMKilling them. Symptoms identical to "
            "INC-2026-0002: sawtooth heap, monotonically rising "
            "pod_restarts_total, GC pauses preceding each crash."
        ),
        "resolution": (
            "Rolled back the deploy and re-introduced the bounded Caffeine "
            "cache with maxSize=50_000. Added a heap-usage SLO alert."
        ),
        "follow_ups": [
            "Lint rule: forbid unbounded ConcurrentHashMap as a cache (DONE)",
            "Heap dump on OOM enabled cluster-wide (DONE)",
        ],
        "related_runbooks": ["jvm_oom_and_memory_leak.md"],
    },
}


# ---------------------------------------------------------------------------
# Scenario 3 — notifications-service: upstream provider rate limiting (429)
# ---------------------------------------------------------------------------
_SCENARIO_NOTIFICATIONS_429 = {
    "incident_id": "INC-2026-0003",
    "title": "notifications-service queue backlog from upstream 429s",
    "severity": "SEV-3",
    "service": "notifications-service",
    "environment": "production",
    "region": "eu-west-1",
    "started_at": _BASE.replace(day=6, hour=11, minute=47, second=2),
    "detected_at_offset_s": 300,
    "duration_minutes": 20,
    "tags": ["upstream", "rate-limit", "429", "queue", "email"],
    "reporter": "prometheus-alert",
    "on_call": "carla.silva@example.com",
    "customer_impact": (
        "Outbound transactional emails delayed by 5-15 minutes (order "
        "confirmations, password resets). No data loss; messages remain "
        "queued and will deliver. SMS path unaffected."
    ),
    "channels": {
        "slack": "#inc-2026-0003",
        "war_room": None,
        "status_page": "https://status.example.com/incidents/2026-0003",
    },
    "alerts": [
        {"alert_id": "alert-ns-001", "name": "Notifications_Upstream429Rate",
         "severity": "warning", "fired_at_offset_s": 300,
         "dimensions": {"service": "notifications-service", "upstream": "sendmail-pro"}},
        {"alert_id": "alert-ns-002", "name": "Notifications_QueueDepthHigh",
         "severity": "warning", "fired_at_offset_s": 540,
         "dimensions": {"service": "notifications-service", "queue": "email-outbound"}},
        {"alert_id": "alert-ns-003", "name": "Notifications_QueueAgeP95High",
         "severity": "warning", "fired_at_offset_s": 720,
         "dimensions": {"service": "notifications-service", "queue": "email-outbound"}},
    ],
    "logs": [
        {"offset_s": 4,    "level": "INFO",  "component": "notifications-service",            "request_id": "msg-aa01", "message": "dispatch email template=order_confirmation user=u-91002 -> sendmail-pro"},
        {"offset_s": 12,   "level": "INFO",  "component": "notifications-service.upstream",   "request_id": "msg-aa01", "message": "POST sendmail-pro/v1/messages -> 202 in 142ms"},
        {"offset_s": 60,   "level": "INFO",  "component": "notifications-service.queue",      "request_id": None,        "message": "queue email-outbound depth=48 age_p95=1.2s"},
        {"offset_s": 240,  "level": "INFO",  "component": "marketing-platform.webhook",       "request_id": None,        "message": "marketing campaign 'spring_promo_v3' triggered (~120k recipients)"},
        {"offset_s": 290,  "level": "WARN",  "component": "notifications-service.upstream",   "request_id": "msg-bb12", "message": "POST sendmail-pro/v1/messages -> 429 in 88ms (X-RateLimit-Remaining=0, retry-after=30)"},
        {"offset_s": 305,  "level": "WARN",  "component": "notifications-service.upstream",   "request_id": "msg-bb13", "message": "POST sendmail-pro/v1/messages -> 429 in 92ms (X-RateLimit-Remaining=0)"},
        {"offset_s": 330,  "level": "INFO",  "component": "notifications-service.retry",      "request_id": "msg-bb12", "message": "scheduled retry attempt=1 of 5 in 30s (msg-bb12)"},
        {"offset_s": 420,  "level": "WARN",  "component": "notifications-service.upstream",   "request_id": "msg-cc44", "message": "POST sendmail-pro/v1/messages -> 429 in 84ms (X-RateLimit-Remaining=0)"},
        {"offset_s": 480,  "level": "INFO",  "component": "notifications-service.queue",      "request_id": None,        "message": "queue email-outbound depth=812 age_p95=18s"},
        {"offset_s": 540,  "level": "WARN",  "component": "notifications-service.queue",      "request_id": None,        "message": "queue email-outbound depth=2104 age_p95=42s (alert: QueueDepthHigh)"},
        {"offset_s": 600,  "level": "INFO",  "component": "notifications-service.config",     "request_id": None,        "message": "current upstream config: sendmail-pro tier=standard limit=200rpm burst=400"},
        {"offset_s": 660,  "level": "WARN",  "component": "notifications-service.upstream",   "request_id": "msg-dd55", "message": "POST sendmail-pro/v1/messages -> 429 in 90ms"},
        {"offset_s": 720,  "level": "WARN",  "component": "notifications-service.queue",      "request_id": None,        "message": "queue email-outbound depth=4488 age_p95=4m12s (alert: QueueAgeP95High)"},
        {"offset_s": 780,  "level": "INFO",  "component": "notifications-service.retry",      "request_id": "msg-bb12", "message": "retry attempt=3 of 5 (msg-bb12, queued 7m30s ago)"},
        {"offset_s": 840,  "level": "WARN",  "component": "notifications-service.upstream",   "request_id": "msg-ee66", "message": "POST sendmail-pro/v1/messages -> 429 in 88ms"},
        {"offset_s": 900,  "level": "INFO",  "component": "notifications-service.queue",      "request_id": None,        "message": "queue email-outbound depth=6208 age_p95=7m45s"},
        {"offset_s": 960,  "level": "INFO",  "component": "notifications-service.upstream",   "request_id": "msg-ff77", "message": "POST sendmail-pro/v1/messages -> 202 in 138ms"},
        {"offset_s": 1020, "level": "WARN",  "component": "notifications-service.upstream",   "request_id": "msg-gg88", "message": "POST sendmail-pro/v1/messages -> 429 in 92ms"},
        {"offset_s": 1080, "level": "INFO",  "component": "notifications-service.queue",      "request_id": None,        "message": "queue email-outbound depth=7102 age_p95=10m12s"},
        {"offset_s": 1140, "level": "WARN",  "component": "notifications-service.upstream",   "request_id": "msg-hh99", "message": "POST sendmail-pro/v1/messages -> 429 in 86ms"},
        {"offset_s": 1180, "level": "INFO",  "component": "notifications-service.queue",      "request_id": None,        "message": "queue email-outbound depth=7884 age_p95=12m40s"},
    ],
    "metrics_series": {
        "request_rate_rps":         [12, 13, 12, 13, 14, 16, 22, 30, 35, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36, 36],  # outbound to upstream (rate-limited)
        "error_rate_pct":           [0.0,0.0,0.0,0.0,0.0,2.4,18.5,42.1,68.3,78.9,82.4,84.0,85.1,84.5,86.0,84.8,85.2,85.6,85.0,85.3],
        "upstream_429_rate_pct":    [0.0,0.0,0.0,0.0,0.0,2.0,18.0,42.0,68.0,79.0,82.0,84.0,85.0,84.0,86.0,85.0,85.0,85.0,85.0,85.0],
        "latency_p50_ms":           [120,118,122,124,121,128,135,140,142,144,141,140,142,144,143,142,141,140,141,142],
        "latency_p95_ms":           [220,218,225,228,222,260,310,340,360,372,368,365,372,376,374,370,368,365,368,370],
        "latency_p99_ms":           [340,338,344,346,342,420,610,680,720,742,738,732,742,748,744,738,734,730,734,738],
        "queue_depth":              [38, 42, 50, 56, 60, 180, 540, 1240, 2104, 3120, 4080, 4880, 5520, 6088, 6608, 7048, 7440, 7780, 8060, 8302],
        "queue_age_p95_seconds":    [1, 1, 1, 1, 1, 12, 42, 88, 158, 252, 372, 510, 660, 792, 924, 1044, 1162, 1276, 1392, 1508],
        "cpu_usage_pct":            [22, 21, 22, 23, 22, 24, 28, 31, 33, 34, 33, 32, 33, 34, 33, 32, 32, 31, 32, 32],
        "memory_usage_pct":         [54, 54, 55, 55, 55, 56, 58, 60, 62, 63, 64, 64, 65, 65, 66, 66, 66, 66, 67, 67],
    },
    "expected_answer": {
        "root_cause_hypothesis": (
            "The marketing platform triggered the 'spring_promo_v3' "
            "campaign at +240s (~120k recipients), which alone exceeds the "
            "200 requests-per-minute quota of our `sendmail-pro` standard "
            "tier. Layered on top of normal transactional traffic, this "
            "drives sustained 429 rate-limited responses; our retry policy "
            "queues messages and re-attempts, growing the email-outbound "
            "queue depth to ~8k with p95 age over 12 minutes. The system is "
            "behaving correctly — there is no bug — but customer impact is "
            "real (delayed transactional email)."
        ),
        "confidence": 0.83,
        "evidence": [
            "app.log @ +240s: 'marketing campaign spring_promo_v3 triggered (~120k recipients)' precedes the first 429 by ~50s",
            "app.log @ +290s and onward: sustained 429 responses from sendmail-pro with X-RateLimit-Remaining=0",
            "app.log @ +600s: current upstream config is tier=standard limit=200rpm — well below 120k recipients spread over a few minutes",
            "metrics: upstream_429_rate_pct climbs from 0% to ~85% and stays there (cap, not a bug)",
            "metrics: queue_depth grows monotonically from 60 to 8302; queue_age_p95_seconds reaches 25m+",
            "no 5xx from sendmail-pro and no errors on the SMS path — the issue is scoped to the email upstream's quota",
        ],
        "remediation_steps": [
            "1. Throttle the marketing campaign: have the marketing team pause 'spring_promo_v3' or move it to the dedicated 'bulk' upstream tier.",
            "2. Temporarily raise the `sendmail-pro` quota to the burst tier (1000rpm) via the provider portal; this is reversible within the SLA.",
            "3. Verify queue_depth starts shrinking and queue_age_p95_seconds turns over within 5 minutes.",
            "4. Communicate to support that order-confirmation emails are delayed but not lost — they are retrying.",
            "5. Long-term: route bulk/marketing email through a separate upstream client and credentials so transactional traffic is not co-located with bulk.",
        ],
        "related_runbooks": ["upstream_rate_limiting.md"],
        "related_past_incidents": ["INC-2025-0301"],
        "severity_assessment": "SEV-3",
        "estimated_time_to_mitigate_minutes": 12,
        "impacted_services": ["notifications-service", "marketing-platform"],
        "impacted_users_estimate": "~120k recipients see 5-15 min delay; no data loss",
    },
    "runbook": {
        "filename": "upstream_rate_limiting.md",
        "title": "Upstream provider rate limiting (HTTP 429)",
        "content_md": """# Runbook: Upstream provider rate limiting (HTTP 429)

**Applies to:** any service that calls a third-party API with a published
quota (notifications-service, payments-api/stripe, search-api/maps).

## Symptoms

- High `upstream_4xx_rate_pct` or specifically `upstream_429_rate_pct`.
- Provider response headers contain `Retry-After` or
  `X-RateLimit-Remaining: 0`.
- Internal queue depth and queue-age metrics rising while CPU/memory are
  fine.
- *No* 5xx from the upstream — the upstream is healthy, we are throttled.

## Diagnose

1. Confirm the limit is *external* (provider) not internal:
   - 429 response code with `X-RateLimit-*` headers => external.
   - Internal client-side rate limiter logs (e.g. token bucket exhausted)
     => internal config; tune the limiter, no provider call needed.
2. Identify the traffic source spike:
   - Bulk/marketing campaigns kicked off recently?
   - A retry storm from a downstream service?
   - A new feature flag enabled for 100% of users?
3. Check the contractual quota tier vs. the current rate. If the inbound
   rate exceeds the quota by design, this is a capacity issue, not a bug.

## Mitigate

1. **Reduce inbound rate**: pause or throttle the originating campaign /
   feature flag / sync job.
2. **Raise the quota** if the provider supports a burst tier or temporary
   uplift (most do, with a 1-hour SLA). Document the change in the
   incident channel so it is reverted afterwards.
3. **Avoid retry storms**: confirm the client uses exponential backoff
   with jitter. If the queue is healthy, *let it drain* — adding retries
   makes things worse.

## Rollback / verify

- `upstream_429_rate_pct < 1%` sustained for 5 minutes.
- `queue_depth` strictly decreasing.
- `queue_age_p95_seconds` falling toward baseline (<5s).

## Prevent

- Separate transactional from bulk traffic onto distinct provider
  credentials with independent quotas.
- Alert on `upstream_429_rate_pct > 5%` for 2 minutes (leading
  indicator).
- Cap retry attempts and use jittered exponential backoff capped by
  `Retry-After`.
""",
    },
    "past_incident": {
        "incident_id": "INC-2025-0301",
        "title": "notifications-service queue backlog during Black Friday email blast",
        "service": "notifications-service",
        "occurred_on": "2025-11-29",
        "severity": "SEV-3",
        "duration_minutes": 73,
        "tags": ["upstream", "rate-limit", "429", "queue"],
        "summary": (
            "Black-Friday marketing email caused sustained 429s from "
            "sendmail-pro for ~70 minutes. The email queue grew to ~22k "
            "and p95 message age peaked at 41 minutes. Transactional and "
            "marketing email shared the same upstream credentials."
        ),
        "resolution": (
            "Marketing pause + temporary provider quota uplift drained the "
            "queue. Permanent fix: split bulk traffic onto a separate "
            "sendmail-pro account with its own credentials and quota."
        ),
        "follow_ups": [
            "Separate bulk vs. transactional upstream credentials (DONE)",
            "Alert on upstream_429_rate_pct > 5% (DONE)",
            "Document campaign launch checklist with capacity check (DONE)",
        ],
        "related_runbooks": ["upstream_rate_limiting.md"],
    },
}


# ---------------------------------------------------------------------------
# Scenario 4 — auth-service: regex CPU saturation after deploy
# ---------------------------------------------------------------------------
_SCENARIO_AUTH_REGEX_CPU = {
    "incident_id": "INC-2026-0004",
    "title": "auth-service p95 latency spike and CPU saturation after deploy",
    "severity": "SEV-1",
    "service": "auth-service",
    "environment": "production",
    "region": "us-east-1",
    "started_at": _BASE.replace(day=7, hour=15, minute=8, second=22),
    "detected_at_offset_s": 210,
    "duration_minutes": 20,
    "tags": ["cpu", "regex", "deploy", "latency", "login"],
    "reporter": "pagerduty",
    "on_call": "diego.ramos@example.com",
    "customer_impact": (
        "Login p95 latency >2s; ~6% of /login requests timing out at the "
        "edge proxy after 5s. Existing sessions unaffected; net-new "
        "sign-ins and token refreshes are degraded."
    ),
    "channels": {
        "slack": "#inc-2026-0004",
        "war_room": "https://meet.example.com/inc-2026-0004",
        "status_page": "https://status.example.com/incidents/2026-0004",
    },
    "alerts": [
        {"alert_id": "alert-as-001", "name": "AuthService_HighCPU",
         "severity": "critical", "fired_at_offset_s": 210,
         "dimensions": {"service": "auth-service"}},
        {"alert_id": "alert-as-002", "name": "AuthService_LoginP95High",
         "severity": "critical", "fired_at_offset_s": 270,
         "dimensions": {"service": "auth-service", "endpoint": "/login"}},
        {"alert_id": "alert-as-003", "name": "EdgeProxy_5xxOnAuth",
         "severity": "warning", "fired_at_offset_s": 360,
         "dimensions": {"upstream": "auth-service"}},
    ],
    "logs": [
        {"offset_s": 0,    "level": "INFO",  "component": "auth-service.deploy", "request_id": None,        "message": "deploy auth-service v2026.05.07 (image sha=4f70b1) -> 100% (changes: stricter email validation regex, fix #C-3318)"},
        {"offset_s": 30,   "level": "INFO",  "component": "auth-service",        "request_id": "req-001",   "message": "POST /login email=alex@example.com -> 200 in 92ms"},
        {"offset_s": 90,   "level": "INFO",  "component": "auth-service",        "request_id": "req-002",   "message": "POST /login email=test@example.com -> 200 in 88ms"},
        {"offset_s": 145,  "level": "WARN",  "component": "auth-service",        "request_id": "req-018",   "message": "POST /login email=longuserwithlots...@subdomain.example.co.uk -> 200 in 1842ms"},
        {"offset_s": 180,  "level": "WARN",  "component": "auth-service",        "request_id": "req-024",   "message": "POST /login email=user.name+filter.tag.label@mail.subdomain.partnerexample.co -> 200 in 3120ms"},
        {"offset_s": 210,  "level": "WARN",  "component": "auth-service.metrics","request_id": None,        "message": "process cpu_usage=0.94 (1m avg), thread pool busy=24/32"},
        {"offset_s": 240,  "level": "WARN",  "component": "auth-service",        "request_id": "req-051",   "message": "POST /login email=very.long.username.with.many.dots@some.long.subdomain.example.org -> 200 in 4980ms"},
        {"offset_s": 270,  "level": "ERROR", "component": "edge-proxy",          "request_id": "req-073",   "message": "upstream auth-service exceeded 5000ms gateway timeout for POST /login -> 504"},
        {"offset_s": 305,  "level": "ERROR", "component": "edge-proxy",          "request_id": "req-088",   "message": "upstream auth-service exceeded 5000ms gateway timeout for POST /login -> 504"},
        {"offset_s": 360,  "level": "WARN",  "component": "auth-service.metrics","request_id": None,        "message": "process cpu_usage=0.99 (1m avg), thread pool busy=32/32 (saturated)"},
        {"offset_s": 410,  "level": "INFO",  "component": "auth-service.profiler","request_id": None,       "message": "async-profiler sample (60s): 92% CPU in java.util.regex.Pattern$Curly.match() <- com.example.auth.EmailValidator.isValid(EmailValidator.java:41)"},
        {"offset_s": 470,  "level": "ERROR", "component": "edge-proxy",          "request_id": "req-114",   "message": "upstream auth-service exceeded 5000ms gateway timeout for POST /login -> 504"},
        {"offset_s": 540,  "level": "INFO",  "component": "auth-service.profiler","request_id": None,       "message": "top hot method: java.util.regex.Pattern$Curly.match (catastrophic backtracking suspected on /login email field)"},
        {"offset_s": 600,  "level": "WARN",  "component": "auth-service",        "request_id": "req-141",   "message": "POST /login email=a.really.long.username.with.dots.and.dashes-here-and-there@sub.example.com -> 504 (timed-out by edge after 5s)"},
        {"offset_s": 660,  "level": "INFO",  "component": "auth-service.deploy", "request_id": None,        "message": "candidate rollback target: auth-service v2026.05.06 (image sha=f120ab) — last green build, deployed 18h ago"},
        {"offset_s": 720,  "level": "WARN",  "component": "auth-service.metrics","request_id": None,        "message": "process cpu_usage=0.98, thread pool busy=32/32, latency_p95=4180ms"},
        {"offset_s": 800,  "level": "ERROR", "component": "edge-proxy",          "request_id": "req-178",   "message": "upstream auth-service exceeded 5000ms gateway timeout for POST /login -> 504"},
        {"offset_s": 880,  "level": "WARN",  "component": "auth-service",        "request_id": "req-202",   "message": "POST /login email=corp.user+tag@subsidiary.parent-company.example.com -> 200 in 4760ms (slow)"},
        {"offset_s": 960,  "level": "INFO",  "component": "auth-service.metrics","request_id": None,        "message": "request_rate_rps=148 (down from baseline 165, clients giving up)"},
        {"offset_s": 1040, "level": "ERROR", "component": "edge-proxy",          "request_id": "req-241",   "message": "upstream auth-service exceeded 5000ms gateway timeout for POST /login -> 504"},
        {"offset_s": 1140, "level": "WARN",  "component": "auth-service.metrics","request_id": None,        "message": "process cpu_usage=0.97, latency_p95=4240ms — sustained for 14 minutes"},
    ],
    "metrics_series": {
        "request_rate_rps":     [165, 168, 166, 167, 169, 170, 162, 158, 152, 150, 148, 146, 145, 145, 144, 144, 143, 143, 142, 142],
        "error_rate_pct":       [0.05,0.05,0.06,0.05,0.04,0.20,1.10,2.40,4.20,5.40,6.20,6.80,7.10,7.20,7.10,7.30,7.20,7.30,7.20,7.30],
        "latency_p50_ms":       [82,  84,  85,  82,  88,  120, 240, 520, 880, 1180,1380,1520,1620,1680,1700,1720,1730,1740,1740,1750],
        "latency_p95_ms":       [180, 184, 188, 186, 200, 410, 1240,2480,3520,4080,4280,4380,4420,4460,4480,4490,4500,4500,4510,4510],
        "latency_p99_ms":       [340, 348, 352, 350, 380, 940, 2640,4480,5000,5000,5000,5000,5000,5000,5000,5000,5000,5000,5000,5000],
        "cpu_usage_pct":        [42,  44,  43,  45,  46,  62,  82,  91,  96,  98,  99,  99,  99,  99,  99,  99,  99,  99,  99,  99],
        "memory_usage_pct":     [58,  58,  59,  59,  59,  60,  61,  62,  63,  63,  64,  64,  64,  65,  65,  65,  65,  65,  65,  65],
        "thread_pool_busy_pct": [56,  58,  57,  60,  62,  72,  86,  94,  98, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
        "edge_504_rate_pct":    [0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.4, 1.6, 3.4, 4.6, 5.4, 6.0, 6.4, 6.6, 6.5, 6.7, 6.6, 6.7, 6.6, 6.7],
    },
    "expected_answer": {
        "root_cause_hypothesis": (
            "Build v2026.05.07 (sha=4f70b1) introduced a 'stricter email "
            "validation regex' (fix #C-3318). The new pattern is vulnerable "
            "to catastrophic backtracking on email addresses with many "
            "dots / repeated subdomain segments. The async-profiler sample "
            "at +410s confirms 92% of CPU is in `Pattern$Curly.match` from "
            "`EmailValidator.isValid(EmailValidator.java:41)`. CPU "
            "saturates around minute 9, the 32-thread request pool fills, "
            "and the edge proxy returns 504s after its 5s timeout."
        ),
        "confidence": 0.93,
        "evidence": [
            "app.log @ +0s: deploy v2026.05.07 explicitly mentions 'stricter email validation regex (fix #C-3318)'",
            "app.log @ +145s/+180s/+240s: latencies of 1.8s/3.1s/5.0s on /login requests with long, dotted email addresses (regex backtracking signature)",
            "app.log @ +410s/+540s: async-profiler attributes 92% of CPU to java.util.regex.Pattern$Curly.match called from EmailValidator.isValid(EmailValidator.java:41)",
            "metrics: cpu_usage_pct climbs from 42% to 99% within 9 minutes and stays pinned",
            "metrics: thread_pool_busy_pct hits 100% at minute 9, edge_504_rate_pct rises immediately after",
            "metrics: latency_p99_ms saturates at the edge proxy's 5000ms timeout — signature of a CPU-bound request, not a downstream dependency",
        ],
        "remediation_steps": [
            "1. Roll back auth-service to v2026.05.06 (sha=f120ab) — last green build, identified in app.log @ +660s.",
            "2. Confirm cpu_usage_pct returns to <50% within 2 minutes and edge_504_rate_pct drops to <0.5%.",
            "3. Open a P0 ticket against the auth team to fix the regex (atomic groups / possessive quantifiers, or replace with a parser library like Apache Commons Validator).",
            "4. Add a regression test with the failing email patterns from app.log (long dotted user, plus-tag, multi-level subdomain) before re-rolling forward.",
            "5. Enforce a request-level CPU budget in the auth-service so a single pathological request cannot pin a thread for 5s.",
        ],
        "related_runbooks": ["high_cpu_after_deploy.md"],
        "related_past_incidents": ["INC-2025-0212"],
        "severity_assessment": "SEV-1",
        "estimated_time_to_mitigate_minutes": 8,
        "impacted_services": ["auth-service", "edge-proxy", "checkout-web", "mobile-app"],
        "impacted_users_estimate": "~6% of net-new logins fail; existing sessions unaffected",
    },
    "runbook": {
        "filename": "high_cpu_after_deploy.md",
        "title": "High CPU / latency after a deploy (regex backtracking, hot-path regression)",
        "content_md": """# Runbook: High CPU / latency after a deploy

**Applies to:** any compiled or interpreted service where CPU saturates
shortly after a deploy (auth-service, search-api, recommendations-service).

## Symptoms

- `cpu_usage_pct` climbs to 95%+ shortly after a rollout completes.
- `latency_p95` / `latency_p99` saturate at an upstream timeout (5s edge,
  30s pool, etc.).
- `thread_pool_busy_pct` reaches 100%.
- `error_rate_pct` rises with timeouts (504/upstream timeout) rather than
  application errors (500).
- Profiler / flame graph shows a single hot method dominating samples.

## Diagnose

1. Correlate the CPU climb with the most recent deploy. If they line up
   within a few minutes, treat the deploy as the prime suspect.
2. Capture a 60s on-CPU profile (async-profiler / pprof / py-spy):
   - One method dominating samples => regression in that method.
   - Distributed CPU across many methods => genuine load increase.
3. Common regression signatures:
   - `Pattern$Curly.match` / regex internals => catastrophic backtracking.
   - `String.split` / `replaceAll` in a tight loop => N^2 string handling.
   - Crypto hash on a hot path => cost of an algorithm change.
   - JSON serializer => an `@JsonInclude` or similar change.

## Mitigate

1. **Roll back first, debug second.** Identify the last green build (its
   image SHA is in the deploy log) and roll back. Don't try to fix forward.
2. If a rollback isn't safe (e.g. data migration in flight), scale out the
   service horizontally to buy headroom while diagnosing.
3. Drain affected pods gracefully so in-flight requests finish.

## Rollback / verify

- `cpu_usage_pct` back to baseline (typically 30-50%).
- `thread_pool_busy_pct` < 80%.
- `latency_p95` / `latency_p99` back inside SLO.
- `edge_5xx_rate` back below 0.5% for 5 minutes.

## Prevent

- Pre-merge: add CPU-budget tests for hot-path methods (e.g. validators,
  parsers).
- Use atomic groups / possessive quantifiers in any regex on user input;
  prefer a real parser library over regex for structured data (emails,
  URLs, credit cards).
- Enforce a per-request CPU budget so one pathological input cannot pin a
  thread for the full upstream timeout.
- Add canary analysis on `cpu_usage_pct` and `latency_p95` before a deploy
  reaches 100%.
""",
    },
    "past_incident": {
        "incident_id": "INC-2025-0212",
        "title": "search-api CPU saturation from regex change in query parser",
        "service": "search-api",
        "occurred_on": "2025-09-21",
        "severity": "SEV-1",
        "duration_minutes": 22,
        "tags": ["cpu", "regex", "deploy"],
        "summary": (
            "search-api deploy introduced a regex change in the query "
            "parser. Long queries with repeating tokens triggered "
            "catastrophic backtracking, CPU pinned at 99%, edge 504 rate "
            "rose to ~9%. Profiler attributed >90% of CPU to "
            "Pattern$Curly.match in QueryNormalizer."
        ),
        "resolution": (
            "Rolled back to previous build, fixed regex with possessive "
            "quantifiers, added regression tests for the failing inputs."
        ),
        "follow_ups": [
            "CPU-budget unit test for QueryNormalizer (DONE)",
            "Per-request CPU budget enforcement (DONE)",
            "Canary analysis includes cpu_usage_pct (DONE)",
        ],
        "related_runbooks": ["high_cpu_after_deploy.md"],
    },
}


# ---------------------------------------------------------------------------
# Scenario 5 — orders-api: disk full / log rotation broken
# ---------------------------------------------------------------------------
_SCENARIO_ORDERS_DISK_FULL = {
    "incident_id": "INC-2026-0005",
    "title": "orders-api write errors and 5xx — host disk full",
    "severity": "SEV-2",
    "service": "orders-api",
    "environment": "production",
    "region": "ap-southeast-1",
    "started_at": _BASE.replace(day=8, hour=3, minute=15, second=10),
    "detected_at_offset_s": 240,
    "duration_minutes": 20,
    "tags": ["disk", "filesystem", "logs", "5xx", "infra"],
    "reporter": "node-exporter",
    "on_call": "elena.popescu@example.com",
    "customer_impact": (
        "Order placement intermittently failing for SEA region (~8% of "
        "POST /orders requests). Reads still serve from the read replica. "
        "No data loss confirmed; failed orders return a clear error and "
        "are not silently dropped."
    ),
    "channels": {
        "slack": "#inc-2026-0005",
        "war_room": "https://meet.example.com/inc-2026-0005",
        "status_page": "https://status.example.com/incidents/2026-0005",
    },
    "alerts": [
        {"alert_id": "alert-or-001", "name": "Node_DiskUsageHigh",
         "severity": "warning", "fired_at_offset_s": 120,
         "dimensions": {"host": "orders-api-i-0a3c", "mount": "/"}},
        {"alert_id": "alert-or-002", "name": "OrdersAPI_5xxRate",
         "severity": "critical", "fired_at_offset_s": 360,
         "dimensions": {"service": "orders-api"}},
        {"alert_id": "alert-or-003", "name": "Node_DiskUsageCritical",
         "severity": "critical", "fired_at_offset_s": 540,
         "dimensions": {"host": "orders-api-i-0a3c", "mount": "/"}},
    ],
    "logs": [
        {"offset_s": 6,    "level": "INFO",  "component": "orders-api",         "request_id": "req-o001", "message": "POST /orders user_id=u-50012 items=3 -> 201 in 76ms"},
        {"offset_s": 60,   "level": "INFO",  "component": "node-exporter",      "request_id": None,        "message": "filesystem / on host orders-api-i-0a3c: used=82.4%, inodes_used=44.1%"},
        {"offset_s": 130,  "level": "WARN",  "component": "node-exporter",      "request_id": None,        "message": "filesystem / on host orders-api-i-0a3c: used=92.1% (warning threshold=90%)"},
        {"offset_s": 180,  "level": "INFO",  "component": "orders-api.logging",  "request_id": None,        "message": "logrotate not invoked in last 7 days; /var/log/orders-api/app.log size=14.2GB"},
        {"offset_s": 240,  "level": "WARN",  "component": "orders-api.audit",   "request_id": "req-o042", "message": "audit-log write retry 1/3 (path=/var/log/orders-api/audit.log)"},
        {"offset_s": 300,  "level": "WARN",  "component": "node-exporter",      "request_id": None,        "message": "filesystem / on host orders-api-i-0a3c: used=96.8%"},
        {"offset_s": 340,  "level": "ERROR", "component": "orders-api.audit",   "request_id": "req-o061", "message": "java.io.IOException: No space left on device\n\tat java.io.FileOutputStream.writeBytes(Native Method)\n\tat com.example.orders.AuditLogger.append(AuditLogger.java:54)"},
        {"offset_s": 360,  "level": "ERROR", "component": "orders-api",         "request_id": "req-o061", "message": "POST /orders -> 500 in 412ms (audit log write failed; transaction rolled back)"},
        {"offset_s": 420,  "level": "ERROR", "component": "orders-api.audit",   "request_id": "req-o074", "message": "java.io.IOException: No space left on device"},
        {"offset_s": 460,  "level": "WARN",  "component": "node-exporter",      "request_id": None,        "message": "filesystem / on host orders-api-i-0a3c: used=98.3%"},
        {"offset_s": 510,  "level": "ERROR", "component": "orders-api",         "request_id": "req-o082", "message": "POST /orders -> 500 in 388ms (audit log write failed)"},
        {"offset_s": 560,  "level": "INFO",  "component": "orders-api.fs-scan", "request_id": None,        "message": "top consumers under /var: /var/log/orders-api/app.log=14.2GB, /var/log/orders-api/access.log=2.1GB, /var/cache/apt=1.4GB"},
        {"offset_s": 620,  "level": "WARN",  "component": "node-exporter",      "request_id": None,        "message": "filesystem / on host orders-api-i-0a3c: used=99.4%"},
        {"offset_s": 700,  "level": "ERROR", "component": "orders-api",         "request_id": "req-o119", "message": "POST /orders -> 500 in 402ms (audit log write failed)"},
        {"offset_s": 760,  "level": "INFO",  "component": "orders-api.deploy",  "request_id": None,        "message": "config audit: logrotate.d/orders-api last modified 2026-04-22 (recent change set rotate=0); compare to peer host orders-api-i-1f9e where logrotate runs daily"},
        {"offset_s": 840,  "level": "ERROR", "component": "orders-api.audit",   "request_id": "req-o141", "message": "java.io.IOException: No space left on device"},
        {"offset_s": 900,  "level": "WARN",  "component": "node-exporter",      "request_id": None,        "message": "filesystem / on host orders-api-i-0a3c: used=99.7%, free=512MB"},
        {"offset_s": 960,  "level": "ERROR", "component": "orders-api",         "request_id": "req-o168", "message": "POST /orders -> 500 in 410ms (audit log write failed)"},
        {"offset_s": 1040, "level": "ERROR", "component": "orders-api.audit",   "request_id": "req-o192", "message": "java.io.IOException: No space left on device"},
        {"offset_s": 1120, "level": "WARN",  "component": "node-exporter",      "request_id": None,        "message": "filesystem / on host orders-api-i-0a3c: used=99.9%, free=88MB (critical)"},
        {"offset_s": 1180, "level": "ERROR", "component": "orders-api",         "request_id": "req-o218", "message": "POST /orders -> 500 in 398ms (audit log write failed)"},
    ],
    "metrics_series": {
        "request_rate_rps":     [62,  64,  63,  65,  64,  66,  65,  64,  63,  62,  60,  58,  56,  55,  54,  53,  52,  52,  51,  51],
        "error_rate_pct":       [0.05,0.06,0.05,0.05,0.06,0.10,0.40,1.20,3.80,5.60,6.80,7.40,7.80,8.10,8.20,8.30,8.40,8.40,8.50,8.50],
        "latency_p50_ms":       [78,  80,  79,  82,  81,  83,  86,  92, 104, 118, 130, 142, 154, 162, 168, 172, 174, 175, 176, 176],
        "latency_p95_ms":       [180, 182, 184, 186, 188, 192, 220, 280, 360, 440, 510, 560, 600, 622, 638, 648, 656, 660, 662, 664],
        "latency_p99_ms":       [320, 322, 326, 330, 332, 348, 412, 520, 660, 780, 880, 940, 980, 1010,1030,1042,1050,1054,1058,1060],
        "cpu_usage_pct":        [28,  29,  28,  30,  29,  30,  31,  30,  29,  28,  27,  26,  26,  25,  25,  24,  24,  24,  23,  23],
        "memory_usage_pct":     [52,  52,  53,  53,  53,  54,  54,  54,  54,  55,  55,  55,  55,  55,  56,  56,  56,  56,  56,  56],
        "disk_usage_pct":       [82.4,84.6,86.8,89.0,91.0,92.1,94.4,96.8,97.6,98.3,98.8,99.1,99.3,99.4,99.5,99.6,99.7,99.8,99.85,99.9],
        "disk_free_mb":         [12800,11400,10000,8600,7200,5800,4200,2900,2200,1600,1200, 900, 700, 600, 520, 460, 400, 300, 200, 88],
        "inode_usage_pct":      [44.1,44.4,44.6,44.8,45.0,45.2,45.4,45.6,45.8,46.0,46.2,46.4,46.5,46.6,46.7,46.8,46.8,46.9,46.9,46.9],
    },
    "expected_answer": {
        "root_cause_hypothesis": (
            "The host `orders-api-i-0a3c` is out of disk space because "
            "logrotate is not rotating /var/log/orders-api/app.log — the "
            "config audit log @+760s shows /etc/logrotate.d/orders-api was "
            "modified 2026-04-22 with `rotate=0`, while the peer host "
            "orders-api-i-1f9e still rotates daily. The current app.log is "
            "14.2GB and free space is below 100MB. With no space, audit-log "
            "writes fail (`java.io.IOException: No space left on device`), "
            "and because audit logging is in the order-write transaction "
            "path, the whole order is rolled back as a 500."
        ),
        "confidence": 0.88,
        "evidence": [
            "app.log @ +180s: 'logrotate not invoked in last 7 days; /var/log/orders-api/app.log size=14.2GB'",
            "app.log @ +340s: 'java.io.IOException: No space left on device' from AuditLogger.append(AuditLogger.java:54)",
            "app.log @ +560s: top consumer is /var/log/orders-api/app.log=14.2GB",
            "app.log @ +760s: config audit indicates logrotate.d/orders-api was changed 2026-04-22 setting rotate=0; peer host still rotates daily",
            "metrics: disk_usage_pct climbs from 82% to 99.9% over the window; disk_free_mb drops from 12.8GB to 88MB",
            "metrics: error_rate_pct begins to climb only once disk_free_mb drops below ~3GB (~minute 7), which matches the timing of write failures",
            "metrics: cpu/memory are flat — this is not a load problem, it's a host-state problem",
        ],
        "remediation_steps": [
            "1. SSH to `orders-api-i-0a3c`, `truncate -s 0 /var/log/orders-api/app.log` to immediately free ~14GB without restarting the service (do *not* `rm` the open file).",
            "2. Verify disk_free_mb climbs back above 5GB and orders-api 5xx rate drops within 2 minutes.",
            "3. Restore the correct logrotate config (compare against orders-api-i-1f9e: `diff /etc/logrotate.d/orders-api /etc/logrotate.d/orders-api.peer`) and run `logrotate -f /etc/logrotate.d/orders-api`.",
            "4. Decommission and replace the host if the wrong logrotate config is part of an outdated AMI; confirm the image used by the orders-api ASG.",
            "5. Long-term: ship logs off-host (Fluent Bit -> S3/Datadog) so a logrotate failure cannot fill the disk, and alert on `disk_usage_pct > 85%` for 10m as a leading indicator (not just `> 95%`).",
        ],
        "related_runbooks": ["host_disk_full.md"],
        "related_past_incidents": ["INC-2025-0288"],
        "severity_assessment": "SEV-2",
        "estimated_time_to_mitigate_minutes": 5,
        "impacted_services": ["orders-api"],
        "impacted_users_estimate": "~8% of order placements in ap-southeast-1",
    },
    "runbook": {
        "filename": "host_disk_full.md",
        "title": "Host disk full / no space left on device",
        "content_md": """# Runbook: Host disk full / `No space left on device`

**Applies to:** any service whose nodes write to local disk for logs,
audit, temp files, or caches.

## Symptoms

- Application log: `java.io.IOException: No space left on device` /
  `OSError: [Errno 28] No space left on device`.
- `disk_usage_pct > 95%` from node-exporter or equivalent.
- `error_rate_pct` climbing while CPU and memory are flat.
- Writes failing while reads still succeed (especially obvious if reads
  are served from a replica or a cache).

## Diagnose

1. Confirm which mount is full and on which host:
   ```bash
   df -h
   df -i      # also check inodes — sometimes inodes are exhausted, not bytes
   ```
2. Find the largest consumers:
   ```bash
   du -h --max-depth=1 /var | sort -h | tail
   du -h --max-depth=1 /var/log | sort -h | tail
   ```
3. Check whether logrotate (or the equivalent) is healthy:
   ```bash
   systemctl status logrotate.timer
   ls -la /var/lib/logrotate/
   cat /etc/logrotate.d/<service>
   ```
4. Compare the offending host's config against a healthy peer in the same
   ASG / Deployment. Drift between hosts is the most common cause.

## Mitigate

1. **Free space without restarting the service.** Use `truncate -s 0` on a
   large log file, or compress old rotated logs. Do *not* `rm` a file
   that is still held open by a process — the inode stays allocated until
   the fd closes.
2. If the issue is inode exhaustion, find the directory with millions of
   small files and clear it (typically `/tmp`, `/var/cache/<thing>`).
3. Once disk pressure is relieved, re-run logrotate manually:
   `logrotate -f /etc/logrotate.d/<service>`.

## Rollback / verify

- `disk_usage_pct < 80%` and `disk_free_mb` comfortably above the largest
  expected log file.
- `error_rate_pct < 0.5%` for 5 minutes.
- Subsequent writes succeed (tail the application log briefly).

## Prevent

- Ship logs off-host (Fluent Bit / Vector / Filebeat -> S3, Loki, or
  Datadog). The local disk should be a buffer, not the destination.
- Alert on `disk_usage_pct > 85%` for 10 minutes (leading indicator) in
  addition to a critical `> 95%` page.
- Add a node-level smoke test that runs daily and confirms logrotate
  actually rotated something in the last 24h.
- Bake logrotate config into the AMI / image rather than letting it drift
  via post-bake configuration management.
""",
    },
    "past_incident": {
        "incident_id": "INC-2025-0288",
        "title": "billing-api hosts disk full from un-rotated audit logs",
        "service": "billing-api",
        "occurred_on": "2025-10-30",
        "severity": "SEV-2",
        "duration_minutes": 34,
        "tags": ["disk", "logs", "logrotate"],
        "summary": (
            "Two billing-api hosts ran out of disk because logrotate was "
            "removed from the AMI in a hardening change. Audit log writes "
            "failed with 'No space left on device', causing transactional "
            "writes to roll back as 500s. Symptoms identical to "
            "INC-2026-0005."
        ),
        "resolution": (
            "Truncated the open log file to free space, restored "
            "logrotate via configuration management, and re-baked the AMI "
            "with logrotate included by default."
        ),
        "follow_ups": [
            "AMI smoke test: logrotate present and ran in last 24h (DONE)",
            "Ship audit logs to S3 via Fluent Bit (DONE)",
            "Add disk_usage_pct > 85% leading-indicator alert (DONE)",
        ],
        "related_runbooks": ["host_disk_full.md"],
    },
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
SCENARIOS: list[dict] = [
    _SCENARIO_PAYMENTS_DB_POOL,
    _SCENARIO_CHECKOUT_OOM,
    _SCENARIO_NOTIFICATIONS_429,
    _SCENARIO_AUTH_REGEX_CPU,
    _SCENARIO_ORDERS_DISK_FULL,
]


def get_scenario(incident_id: str) -> dict:
    """Look up a single scenario by its incident_id, raising KeyError if missing."""
    for s in SCENARIOS:
        if s["incident_id"] == incident_id:
            return s
    raise KeyError(f"unknown incident_id: {incident_id!r}")
