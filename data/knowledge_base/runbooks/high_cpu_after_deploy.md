# Runbook: High CPU / latency after a deploy

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
