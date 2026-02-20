# Scripts

Utility scripts for development and maintenance of releasekit.
These are **not** part of the published package — they are developer tools.

## `verify_license_data.py`

Verifies `src/releasekit/data/licenses.toml` against two authoritative
upstream sources:

1. **SPDX License List** — checks that every SPDX ID is valid and that
   `osi_approved` matches the official list.
2. **Google licenseclassifier** — checks that every `google_category`
   matches `license_type.go` in `google/licenseclassifier`.

Run after editing `licenses.toml` to catch typos, stale data, or
misclassifications before they ship.

```shell
# Run both checks (default).
python scripts/verify_license_data.py

# Run only the SPDX check.
python scripts/verify_license_data.py --spdx

# Run only the Google classifier check.
python scripts/verify_license_data.py --google
```

**Requires network access** — fetches the latest data from GitHub on
each run.

## Integration test: `tests/rk_license_data_integ_test.py`

The same checks are also available as a pytest integration test marked
with `@pytest.mark.network`.  These are **deselected by default** (via
`-m 'not network'` in `pyproject.toml` `addopts`) so they never run in
offline CI or local `pytest` invocations.

```shell
# Run the network integration tests explicitly.
pytest -m network tests/rk_license_data_integ_test.py --no-cov

# Run everything including network tests.
pytest -m '' --no-cov
```

If the machine has no internet, the tests skip automatically via a
socket probe.

## `dump_diagnostics.py`

Dumps diagnostic information about the current releasekit environment
(Python version, installed packages, platform, etc.) for bug reports.

```shell
python scripts/dump_diagnostics.py
```
