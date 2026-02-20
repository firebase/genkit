---
title: Concurrency & Locking
description: Prevent concurrent releases and understand parallel publishing.
---

# Concurrency & Locking

ReleaseKit protects against two classes of concurrency issues:

1. **Concurrent release processes** — two CI jobs trying to release
   at the same time.
2. **Parallel package publishing** — publishing independent packages
   simultaneously for faster releases.

---

## Advisory Locking

ReleaseKit uses advisory lock files to prevent concurrent release
processes from interfering with each other.

### How It Works

```text
releasekit publish
  │
  ├── Acquire lock (.releasekit.lock)
  │     ├── File exists? → check staleness
  │     │     ├── Stale (>30 min)? → steal lock
  │     │     └── Fresh? → abort with error
  │     └── File missing? → create lock (O_CREAT|O_EXCL)
  │
  ├── Run publish pipeline...
  │
  └── Release lock (delete file)
```

### Lock File Contents

The lock file contains metadata for debugging:

```json
{
  "pid": 12345,
  "hostname": "ci-runner-7",
  "started_at": "2026-02-15T12:00:00Z",
  "command": "releasekit publish --group core"
}
```

### Staleness

A lock is considered **stale** if it is older than 30 minutes (default).
Stale locks are automatically stolen — this prevents abandoned CI jobs
from permanently blocking releases.

Configure the stale threshold:

```toml
[publish]
lock_stale_timeout_minutes = 30  # Default.
```

### Force-Overriding a Lock

```bash
# Break an existing lock (use with caution).
releasekit publish --force-lock
```

---

## Parallel Publishing

Independent packages (no dependency relationship) are published in
parallel for faster releases. ReleaseKit uses the dependency graph
to determine which packages can run concurrently.

### Concurrency Levels

```text
Level 0:  genkit                    (no deps — publishes first)
Level 1:  genkit-plugin-google-genai, genkit-plugin-firebase  (parallel)
Level 2:  sample-chat               (depends on L1 packages)
```

Packages at the same level publish **concurrently**. Each level waits
for the previous level to complete before starting.

### Concurrency Limit

```toml
[publish]
# Maximum number of concurrent publish operations (default: 4).
max_concurrency = 4
```

Setting `max_concurrency = 1` forces **sequential** publishing, which
is useful for debugging.

---

## Crash Safety

If a release is interrupted (e.g. CI runner killed), ReleaseKit
records state to a crash-safe journal file:

```bash
# Resume a crashed release.
releasekit publish --resume

# View the state of a crashed release.
cat .releasekit-state.json | python -m json.tool
```

The state file uses atomic writes (`mkstemp` + `os.replace`) to
prevent corruption from partial writes.
