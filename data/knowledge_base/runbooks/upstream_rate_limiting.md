# Runbook: Upstream provider rate limiting (HTTP 429)

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
