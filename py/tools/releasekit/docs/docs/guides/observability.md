---
title: Observability
description: Distributed tracing and pipeline profiling for release operations.
---

# Observability

ReleaseKit provides two observability mechanisms:

1. **OpenTelemetry tracing** — distributed traces for every release
   operation, viewable in Jaeger, Grafana Tempo, or any OTel backend.
2. **Pipeline profiling** — wall-clock timing of every step for
   identifying bottlenecks.

---

## OpenTelemetry Tracing

### Setup

Tracing is always available but only emits real spans when a
`TracerProvider` is configured:

```bash
# Send traces to a local Jaeger instance.
releasekit publish --otel-endpoint http://localhost:4318

# Or use environment variables.
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
releasekit publish
```

### What Gets Traced

Every major operation creates a span:

```text
releasekit.publish
├── releasekit.preflight
├── releasekit.compute_bumps
├── releasekit.build_graph
├── releasekit.scheduler
│   ├── releasekit.publish_package (genkit)
│   │   ├── pin_dependencies
│   │   ├── build
│   │   ├── upload
│   │   ├── poll_registry
│   │   └── verify_checksum
│   ├── releasekit.publish_package (genkit-plugin-google-genai)
│   └── ...
├── releasekit.create_tags
└── releasekit.create_releases
```

### Using the `@span` Decorator

In custom hooks or extensions:

```python
from releasekit.tracing import span

@span('custom_validation')
async def validate_artifacts(paths: list[Path]) -> None:
    ...
```

---

## Pipeline Profiling

### Enable Profiling

```bash
# Show profiling summary after publish.
releasekit publish --profile

# Output:
# ┌──────────────────────┬──────────┐
# │ Step                 │ Duration │
# ├──────────────────────┼──────────┤
# │ compute_bumps        │   0.12s  │
# │ build_graph          │   0.03s  │
# │ publish:genkit       │  12.45s  │
# │ publish:genkit-*     │   8.32s  │
# │ poll:genkit          │  45.21s  │
# │ verify:genkit        │   2.10s  │
# ├──────────────────────┼──────────┤
# │ Critical path        │  68.23s  │
# │ Total (parallel)     │ 142.50s  │
# │ Speedup              │   2.09x  │
# └──────────────────────┴──────────┘
```

### JSON Output

For CI analysis:

```bash
releasekit publish --profile --profile-format json > profile.json
```

The JSON includes:

| Field | Description |
|-------|-------------|
| `total_steps` | Number of timed steps |
| `total_duration_s` | Sum of all step durations |
| `critical_path_s` | Wall-clock elapsed time |
| `slowest_step` | Name of the slowest step |
| `slowest_duration_s` | Duration of the slowest step |

---

## Live Progress UI

During publishing, the observer protocol provides a live terminal UI
showing per-package pipeline progress:

```text
Level 0
  ✅ genkit                    published (12.4s)
Level 1
  📤 genkit-plugin-google-genai publishing...
  🔨 genkit-plugin-firebase     building...
  ⏳ genkit-plugin-ollama       waiting
Level 2
  ⏳ sample-chat               waiting (blocked by L1)
```

The UI supports three view modes:

| Mode | Key | Description |
|------|-----|-------------|
| **ALL** | `a` | Show every package |
| **WINDOW** | `w` | Sliding window (active + recent + failed) |
| **LOG** | `l` | Structured log lines per stage transition |
