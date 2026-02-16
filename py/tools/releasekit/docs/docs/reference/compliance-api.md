---
title: Compliance API Reference
description: API reference for the releasekit.compliance module.
---

# Compliance API Reference

The `releasekit.compliance` module evaluates your repository against the
[OpenSSF OSPS Baseline](https://best.openssf.org/Concise-Guide-for-Evaluating-Open-Source-Software)
framework and maps findings to NIST SSDF tasks.

## Classes

### `ComplianceStatus`

```python
class ComplianceStatus(str, enum.Enum):
    MET = 'met'
    PARTIAL = 'partial'
    GAP = 'gap'
```

Status of a compliance control evaluation.

- **`MET`** — The control is fully satisfied.
- **`PARTIAL`** — The control is partially satisfied (e.g., vuln scanning exists but is incomplete).
- **`GAP`** — The control is not satisfied.

### `OSPSLevel`

```python
class OSPSLevel(int, enum.Enum):
    L1 = 1
    L2 = 2
    L3 = 3
```

OSPS Baseline maturity levels:

- **L1** — Basic hygiene (LICENSE, SECURITY.md, SBOM, manifests).
- **L2** — Hardened (signed artifacts, provenance, lockfiles, vuln scanning).
- **L3** — Isolated (SLSA Build L3, signed provenance on hosted runners).

### `ComplianceControl`

```python
@dataclass(frozen=True)
class ComplianceControl:
    id: str
    control: str
    osps_level: OSPSLevel
    status: ComplianceStatus
    module: str = ''
    nist_ssdf: str = ''
    notes: str = ''
```

A single compliance control and its evaluation result.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Control identifier (e.g., `'OSPS-SCA-01'` or `'ECO-PY-01'`) |
| `control` | `str` | Human-readable control name |
| `osps_level` | `OSPSLevel` | OSPS Baseline level this control belongs to |
| `status` | `ComplianceStatus` | Whether the control is met, partial, or a gap |
| `module` | `str` | The releasekit module that implements this control |
| `nist_ssdf` | `str` | Corresponding NIST SSDF task ID (if any) |
| `notes` | `str` | Additional context about the evaluation |

## Functions

### `evaluate_compliance`

```python
def evaluate_compliance(
    repo_root: Path,
    *,
    has_signing: bool = True,
    has_provenance: bool = True,
    has_sbom: bool = True,
    has_vuln_scanning: bool = False,
    has_slsa_l3: bool = False,
    ecosystems: frozenset[str] | None = None,
) -> list[ComplianceControl]:
```

Evaluate compliance against OSPS Baseline controls.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repo_root` | `Path` | *(required)* | Path to the repository root |
| `has_signing` | `bool` | `True` | Whether Sigstore signing is enabled |
| `has_provenance` | `bool` | `True` | Whether SLSA provenance generation is enabled |
| `has_sbom` | `bool` | `True` | Whether SBOM generation is enabled |
| `has_vuln_scanning` | `bool` | `False` | Whether vulnerability scanning is configured |
| `has_slsa_l3` | `bool` | `False` | Whether SLSA Build L3 is achievable |
| `ecosystems` | `frozenset[str] \| None` | `None` | Explicit set of ecosystem names. Auto-detected if `None` |

**Returns:** `list[ComplianceControl]` — List of evaluated controls.

**Ecosystem names:** `'python'`, `'go'`, `'js'`, `'java'`, `'rust'`, `'dart'`

**Example:**

```python
from pathlib import Path
from releasekit.compliance import evaluate_compliance, ComplianceStatus

controls = evaluate_compliance(Path('.'))
for c in controls:
    if c.status == ComplianceStatus.GAP:
        print(f'{c.id}: {c.control} — GAP')
```

**Example with explicit ecosystems:**

```python
controls = evaluate_compliance(
    Path('.'),
    ecosystems=frozenset({'python', 'go'}),
)
```

### `format_compliance_table`

```python
def format_compliance_table(
    controls: list[ComplianceControl],
) -> str:
```

Format compliance results as a human-readable table with status icons.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `controls` | `list[ComplianceControl]` | List of evaluated compliance controls |

**Returns:** `str` — Multi-line table string with columns: ID, Control, Level, Status, Module, Notes.

### `compliance_to_json`

```python
def compliance_to_json(
    controls: list[ComplianceControl],
    *,
    indent: int = 2,
) -> str:
```

Serialize compliance results to JSON.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `controls` | `list[ComplianceControl]` | *(required)* | List of evaluated compliance controls |
| `indent` | `int` | `2` | JSON indentation level |

**Returns:** `str` — JSON string.

**JSON schema per control:**

```json
{
  "id": "OSPS-SCA-01",
  "control": "SBOM generation",
  "osps_level": "L1",
  "status": "met",
  "module": "sbom.py",
  "nist_ssdf": "PS.3.2",
  "notes": "CycloneDX 1.5 + SPDX 2.3"
}
```

## Internal Functions

### `_detect_ecosystems`

```python
def _detect_ecosystems(repo_root: Path) -> frozenset[str]:
```

Auto-detect which ecosystems are present by looking for canonical
manifest files. Returns a frozenset of ecosystem names.

**Detection markers:**

| Ecosystem | Files Checked |
|-----------|--------------|
| `python` | `pyproject.toml`, `setup.py`, `setup.cfg`, `uv.lock`, `Pipfile` |
| `go` | `go.mod`, `go.sum` |
| `js` | `package.json`, `pnpm-lock.yaml`, `package-lock.json`, `yarn.lock` |
| `java` | `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle` |
| `rust` | `Cargo.toml`, `Cargo.lock` |
| `dart` | `pubspec.yaml`, `pubspec.lock` |

### `_ecosystem_controls`

```python
def _ecosystem_controls(
    repo_root: Path,
    detected: frozenset[str],
) -> list[ComplianceControl]:
```

Generate ecosystem-specific security and compliance controls.
Only emits controls for ecosystems present in `detected`.

## Check Runner API

### `SkipMap`

```python
SkipMap = dict[str, frozenset[str]]
```

Type alias: package name to frozenset of check names to skip.

### `build_skip_map`

```python
def build_skip_map(
    ws: WorkspaceConfig,
    package_names: list[str],
) -> dict[str, frozenset[str]]:
```

Build a per-package check skip map from workspace + package configs.

For each package, the skip set is the union of:

- `ws.skip_checks` (workspace-level skips apply to all packages)
- `PackageConfig.skip_checks` for that package (per-package overrides)

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ws` | `WorkspaceConfig` | The workspace configuration |
| `package_names` | `list[str]` | List of discovered package names |

**Returns:** `dict[str, frozenset[str]]` — Only packages with at least one skip are included.

### `_filter_pkgs`

```python
def _filter_pkgs(
    packages: list[Package],
    check_name: str,
    skip_map: SkipMap | None,
) -> list[Package]:
```

Return packages that have not opted out of the given check name.
Used internally by the check runner to filter packages before
passing them to individual check functions.
