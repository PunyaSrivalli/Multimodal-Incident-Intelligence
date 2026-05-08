# Runbook: Database connection pool exhaustion

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
