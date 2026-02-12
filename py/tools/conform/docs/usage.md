# Usage

## Running conformance tests

### All plugins

```bash
conform check-model --all
```

### Specific plugins

```bash
conform check-model anthropic deepseek google-genai
```

### With increased concurrency

```bash
conform check-model --all -j 8
```

### With verbose output

Shows full stdout/stderr for every failure:

```bash
conform check-model --all -v
```

## Checking plugin files

Verify every model plugin has the required conformance files
(`model-conformance.yaml` + `conformance_entry.py`):

```bash
conform check-plugin
```

This is also called automatically by `bin/check_consistency` during
`bin/lint`.

## Listing plugins

```bash
conform list
```

Shows a table with:

- **Green ●** — all environment variables set
- **Red ○** — some environment variables missing
- **Blue VAR** — variable is set
- **Red VAR** — variable is not set

## Using the wrapper script

The `py/bin/conform` wrapper avoids needing to be in the right directory:

```bash
# From anywhere
py/bin/conform check-model --all
py/bin/conform list
```

## Using with just

```bash
just test-conformance --all          # = conform check-model --all
just check-conformance               # = conform check-plugin
just list-conformance                # = conform list
```
