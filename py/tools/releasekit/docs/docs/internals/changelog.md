---
title: Changelog Generation
description: How ReleaseKit generates per-package changelogs from git history.
---

# Changelog Generation

ReleaseKit generates per-package changelogs by reading commits since the
last tag, grouping them by type, and rendering into Markdown.

## Data Flow

```mermaid
graph LR
    VCS["Git Log"]
    PARSE["Parse Conventional<br/>Commits"]
    GROUP["Group by Type"]
    RENDER["Render Markdown"]
    OUT["CHANGELOG.md"]

    VCS --> PARSE --> GROUP --> RENDER --> OUT

    style VCS fill:#90caf9,stroke:#1565c0,color:#0d47a1
    style OUT fill:#a5d6a7,stroke:#2e7d32,color:#1b5e20
```

## Algorithm

```
┌─────────────────────────────────────────────────────────────────┐
│ generate_changelog(vcs, since_tag, paths)                       │
│                                                                 │
│  1. vcs.log(since=since_tag, paths=paths)                      │
│     → list of commits touching this package                     │
│                                                                 │
│  2. parse_conventional_commit(msg) for each commit              │
│     → ConventionalCommit with type, scope, description          │
│                                                                 │
│  3. Group by commit type:                                       │
│     ┌──────────────┬────────────────────────────┐               │
│     │ Group        │ Commit Types               │               │
│     ├──────────────┼────────────────────────────┤               │
│     │ ⚠ Breaking   │ BREAKING CHANGE, !          │               │
│     │ ✨ Features   │ feat                        │               │
│     │ 🐛 Bug Fixes  │ fix                         │               │
│     │ ⚡ Performance│ perf                        │               │
│     │ 📚 Docs       │ docs                        │               │
│     │ 🔧 Chores     │ chore, ci, build, test      │               │
│     └──────────────┴────────────────────────────┘               │
│                                                                 │
│  4. render_changelog(changelog)                                 │
│     → Markdown string grouped by section                        │
└─────────────────────────────────────────────────────────────────┘
```

## Output Format

```markdown
## 0.6.0 (2026-02-11)

### ⚠ BREAKING CHANGES

* **auth**: Redesign authentication API (#123)

### Features

* **core**: Add streaming support (#456)
* **plugins**: New Ollama embedding model (#789)

### Bug Fixes

* **google-genai**: Fix null pointer in response parser (#101) (closes #42)
* Handle edge case in version calculation (#102)
```

## Linked Issues

Changelog entries automatically extract issue references from commit
messages. Keywords `Fixes`, `Closes`, `Resolves` (and their past-tense
variants) followed by `#N` are parsed and rendered as `(closes #N)` in
the output:

```
fix(auth): handle token expiry. Fixes #42, closes #99
→  * **auth**: handle token expiry (#123) (closes #42, #99)
```

The `closes` keyword is used in the rendered output because it works as
an auto-close keyword on both GitHub and GitLab.

## Filtering

Exclude specific commit types from changelogs:

```python
changelog = generate_changelog(
    vcs=vcs,
    since_tag='genkit-v0.5.0',
    paths=['packages/genkit/'],
    exclude_types=frozenset({'docs', 'chore', 'ci', 'test'}),
)
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant PREP as prepare.py
    participant CL as changelog.py
    participant VCS as VCS Backend

    PREP->>CL: generate_changelog(vcs, since_tag, paths)
    CL->>VCS: log(since=tag, paths=package_paths)
    VCS-->>CL: list[Commit]

    loop For each commit
        CL->>CL: parse_conventional_commit(msg)
    end

    CL->>CL: Group by type
    CL->>CL: Sort within groups

    PREP->>CL: render_changelog(changelog)
    CL-->>PREP: Markdown string
    PREP->>PREP: Write to CHANGELOG.md
```

## Integration with Prepare

During `releasekit prepare`, changelogs are:

1. Generated for each bumped package
2. Prepended to the package's `CHANGELOG.md`
3. Embedded in the Release PR body
4. Committed on the release branch

## Data Types

```python
@dataclass
class ChangelogEntry:
    sha: str
    type: str
    scope: str
    description: str
    breaking: bool
    linked_issues: list[int]  # Issue numbers from Fixes/Closes/Resolves

@dataclass
class Changelog:
    version: str
    date: str
    entries: list[ChangelogEntry]
    breaking_entries: list[ChangelogEntry]
```
