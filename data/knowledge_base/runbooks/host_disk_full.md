# Runbook: Host disk full / `No space left on device`

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
