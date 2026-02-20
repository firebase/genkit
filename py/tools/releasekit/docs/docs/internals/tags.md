---
title: Tags & Releases
description: Git tag creation, GitHub Release management, and CI-mode draft releases.
---

# Tags & Releases

After publishing, ReleaseKit creates git tags and GitHub Releases for
each bumped package.

## Tag Types

```
┌─────────────────┬──────────────────┬──────────────────────────────┐
│ Tag Type        │ Format           │ Example                      │
├─────────────────┼──────────────────┼──────────────────────────────┤
│ Per-package     │ {name}-v{version}│ genkit-v0.6.0                │
│ Umbrella        │ v{version}       │ v0.6.0                       │
└─────────────────┴──────────────────┴──────────────────────────────┘
```

## Tag Creation Flow

```mermaid
graph TD
    MFST["Release Manifest"]
    LOOP["For each bumped package"]
    TAG["Create per-package tag"]
    CHECK{"Tag exists?"}
    SKIP["Skip (idempotent)"]
    UMBTAG["Create umbrella tag"]
    PUSH["Push all tags"]
    REL["Create GitHub Release"]

    MFST --> LOOP
    LOOP --> TAG
    TAG --> CHECK
    CHECK -->|yes| SKIP
    CHECK -->|no| TAG
    LOOP -->|done| UMBTAG
    UMBTAG --> PUSH
    PUSH --> REL

    style MFST fill:#90caf9,stroke:#1565c0,color:#0d47a1
    style REL fill:#a5d6a7,stroke:#2e7d32,color:#1b5e20
```

## Local vs CI Mode

ReleaseKit supports two publishing modes:

```mermaid
graph LR
    subgraph "Local Mode (publish_from=local)"
        L1["publish packages"]
        L2["create tags"]
        L3["create GitHub Release<br/>(published)"]
        L1 --> L2 --> L3
    end

    subgraph "CI Mode (publish_from=ci)"
        C1["create tags"]
        C2["create draft Release<br/>+ manifest.json asset"]
        C3["CI downloads manifest"]
        C4["publish packages"]
        C5["promote Release<br/>(draft → published)"]
        C1 --> C2 --> C3 --> C4 --> C5
    end

    style L3 fill:#a5d6a7,stroke:#2e7d32,color:#1b5e20
    style C5 fill:#a5d6a7,stroke:#2e7d32,color:#1b5e20
```

### CI Mode Details

In CI mode, the tag step creates a **draft** GitHub Release with the
release manifest attached as an asset. A downstream CI workflow then:

1. Downloads the manifest from the draft release
2. Publishes packages based on the manifest
3. Promotes the release from draft to published

This decouples version tagging from package publishing.

## Forge Compatibility

| Feature | GitHub | GitLab | Bitbucket |
|---------|--------|--------|-----------|
| Per-package tags | ✅ | ✅ | ✅ |
| Umbrella tag | ✅ | ✅ | ✅ |
| Releases | ✅ (draft → published) | ✅ (no draft) | ❌ (tags only) |
| Release assets | ✅ | ✅ | ❌ |
| Labels | ✅ | ✅ (on MRs) | ❌ (no-op) |

## Rollback

Delete tags and releases for a given manifest:

```bash
releasekit rollback --tag v0.6.0
```

```mermaid
sequenceDiagram
    participant CLI
    participant VCS as Git
    participant FORGE as GitHub

    CLI->>VCS: delete_tag("v0.6.0", remote=true)
    VCS->>VCS: git tag -d v0.6.0
    VCS->>VCS: git push origin :refs/tags/v0.6.0

    CLI->>FORGE: delete_release("v0.6.0")
    FORGE-->>CLI: Release deleted

    loop For each package tag
        CLI->>VCS: delete_tag("genkit-v0.6.0", remote=true)
        CLI->>FORGE: delete_release("genkit-v0.6.0")
    end
```

## Sequence Diagram: Full Release

```mermaid
sequenceDiagram
    participant CLI
    participant REL as release.py
    participant TAGS as tags.py
    participant NOTES as release_notes.py
    participant FORGE as Forge
    participant VCS as VCS

    CLI->>REL: tag_release(vcs, forge, config)

    alt From merged PR
        REL->>FORGE: list_prs(label="autorelease: pending", state="merged")
        FORGE-->>REL: PR with manifest
        REL->>REL: extract_manifest(pr_body)
    else From manifest file
        REL->>REL: Load manifest from path
    end

    REL->>NOTES: generate_release_notes(manifest, vcs)
    NOTES-->>REL: ReleaseNotes

    REL->>TAGS: create_tags(manifest, vcs, forge, config)

    loop For each bumped package
        TAGS->>VCS: create_tag(name-v{version})
    end

    TAGS->>VCS: create_tag(v{version})
    TAGS->>VCS: push_tags()

    TAGS->>FORGE: create_release(tag, title, body)
    FORGE-->>TAGS: release_url

    REL->>FORGE: remove_label(pr, "autorelease: pending")
    REL->>FORGE: add_label(pr, "autorelease: tagged")

    REL-->>CLI: ReleaseResult
```

## Data Types

```python
@dataclass
class TagResult:
    created: list[str]           # Tags created
    skipped: list[str]           # Tags that already existed
    failed: dict[str, str]       # Tag name → error
    pushed: bool = False         # Whether tags were pushed
    release_url: str = ''        # GitHub Release URL

    def ok(self) -> bool:
        return len(self.failed) == 0

@dataclass
class ReleaseResult:
    manifest: ReleaseManifest | None
    tag_result: TagResult | None
    pr_number: int = 0
    release_url: str = ''
    errors: dict[str, str] = field(default_factory=dict)
```
