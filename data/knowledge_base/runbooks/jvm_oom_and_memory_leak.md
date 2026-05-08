# Runbook: JVM OOM / pods OOMKilled

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
