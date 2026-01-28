# Hot Reloading for Genkit Python: Recommendation

## Summary

For Hot Loading, you can feel free to use the file watcher of your choice.

They should all be compatible as long as you run it through `uv`. Genkit team used `watchdog` while working on internal samples for Python.

This guide demonstrates `watchdog` via `uv tool run`.

## Samle Command

```bash
genkit start -- \
  uv tool run --from watchdog watchmedo auto-restart \
    -d src \
    -p '*.py;*.prompt;*.json' \
    -R \
    -- uv run src/main.py
```

## Why This Approach

### Zero-Install Experience

`uv tool run --from watchdog` fetches watchdog on-demand to an isolated environment. Users don't need to:
- Add watchdog to `pyproject.toml`
- Run `pip install` or `uv add`
- Pollute their project dependencies

The only prerequisite is `uv`, which Genkit Python users already have.

### Clean Environment Isolation

| Component | Environment | Purpose |
|-----------|-------------|---------|
| `watchmedo` | uv's isolated tool cache (`~/.local/share/uv/tools/`) | File watching |
| `src/main.py` | Project's `.venv/` | App execution with genkit + plugins |

watchdog watches files and restarts a subprocess—it doesn't need access to project packages. The user's app runs in the correct project environment with all dependencies.

### Flexible Watch Patterns

Users can watch multiple file types relevant to Genkit apps:
- `*.py` — Python source
- `*.prompt` — Dotprompt templates  
- `*.json` — Configuration files
- `*.pdf`, `*.csv` — Data files (for RAG applications)

