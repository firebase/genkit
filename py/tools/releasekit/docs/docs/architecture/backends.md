---
title: Backend System
description: How ReleaseKit abstracts external systems via Protocol-based backends.
---

# Backend System

ReleaseKit interacts with five categories of external systems. Each category
is defined by a **Python `Protocol`**, with concrete implementations that
can be swapped at construction time.

## Architecture

```mermaid
graph TB
    subgraph "Protocols (Abstract)"
        VCS_P["VCS Protocol"]
        PM_P["PackageManager Protocol"]
        FORGE_P["Forge Protocol"]
        REG_P["Registry Protocol"]
        WS_P["Workspace Protocol"]
    end

    subgraph "Concrete Implementations"
        GIT["GitBackend"]
        HG["MercurialBackend"]
        UV_PM["UvBackend"]
        PNPM_PM["PnpmBackend"]
        CARGO_PM["CargoBackend"]
        DART_PM["DartBackend"]
        GO_PM["GoBackend"]
        MVN_PM["MavenBackend"]
        BAZEL_PM["BazelBackend"]
        MATURIN_PM["MaturinBackend"]
        GH_CLI["GitHubCLIBackend"]
        GH_API["GitHubAPIBackend"]
        GL["GitLabCLIBackend"]
        BB["BitbucketAPIBackend"]
        PYPI["PyPIBackend"]
        NPM["NpmBackend"]
        CRATES["CratesIoBackend"]
        GOPROXY["GoProxyBackend"]
        MAVEN["MavenCentralBackend"]
        PUBDEV["PubDevBackend"]
        UV_WS["UvWorkspace"]
        PNPM_WS["PnpmWorkspace"]
        CARGO_WS["CargoWorkspace"]
        DART_WS["DartWorkspace"]
        GO_WS["GoWorkspace"]
        MVN_WS["MavenWorkspace"]
        BAZEL_WS["BazelWorkspace"]
    end

    VCS_P --> GIT & HG
    PM_P --> UV_PM & PNPM_PM & CARGO_PM & DART_PM & GO_PM & MVN_PM & BAZEL_PM & MATURIN_PM
    FORGE_P --> GH_CLI & GH_API & GL & BB
    REG_P --> PYPI & NPM & CRATES & GOPROXY & MAVEN & PUBDEV
    WS_P --> UV_WS & PNPM_WS & CARGO_WS & DART_WS & GO_WS & MVN_WS & BAZEL_WS

    style VCS_P fill:#90caf9,stroke:#1565c0,color:#0d47a1
    style PM_P fill:#90caf9,stroke:#1565c0,color:#0d47a1
    style FORGE_P fill:#90caf9,stroke:#1565c0,color:#0d47a1
    style REG_P fill:#90caf9,stroke:#1565c0,color:#0d47a1
    style WS_P fill:#90caf9,stroke:#1565c0,color:#0d47a1
```

## VCS Protocol

Abstracts version control operations. Used for git log, tagging,
diff computation, and working tree status.

```python
class VCS(Protocol):
    def log(self, *, since: str, paths: list[str]) -> list[Commit]: ...
    def tag_exists(self, tag: str) -> bool: ...
    def create_tag(self, tag: str, message: str) -> None: ...
    def delete_tag(self, tag: str, *, remote: bool) -> None: ...
    def push_tags(self) -> None: ...
    def is_clean(self) -> bool: ...
    def head_sha(self) -> str: ...
    def is_shallow(self) -> bool: ...
    def diff_files(self, since: str) -> list[str]: ...
    def current_branch(self) -> str: ...
```

| Implementation | Backend | Notes |
|---|---|---|
| `GitBackend` | Git | Shells out to `git` CLI |
| `MercurialBackend` | Mercurial | Shells out to `hg` CLI |

## PackageManager Protocol

Abstracts build and publish operations for language-specific package managers.

```python
class PackageManager(Protocol):
    async def build(self, package_dir: Path, *, output_dir: Path, no_sources: bool, dry_run: bool) -> CommandResult: ...
    async def publish(self, dist_dir: Path, *, check_url: str, index_url: str, dist_tag: str, publish_branch: str, provenance: bool, dry_run: bool) -> CommandResult: ...
    async def lock(self, *, check_only: bool, cwd: Path, dry_run: bool) -> CommandResult: ...
    async def version_bump(self, package_dir: Path, new_version: str, *, dry_run: bool) -> CommandResult: ...
    async def smoke_test(self, package_dir: Path, *, dry_run: bool) -> CommandResult: ...
```

| Implementation | Tool | Ecosystem | Status |
|---|---|---|---|
| `UvBackend` | uv | Python | ✅ Shipped |
| `PnpmBackend` | pnpm | JavaScript | ✅ Shipped |
| `CargoBackend` | cargo | Rust | ✅ Shipped |
| `DartBackend` | dart pub | Dart | ✅ Shipped |
| `GoBackend` | go | Go | ✅ Shipped |
| `MavenBackend` | mvn / gradle | Java / Kotlin | ✅ Shipped |
| `BazelBackend` | bazel | Polyglot (Bazel) | ✅ Shipped |
| `MaturinBackend` | maturin | Rust + Python | ✅ Shipped |
| `KotlinBackend` | gradle (KMP) | Kotlin Multiplatform | 🔜 Planned |
| `SwiftBackend` | swift / pod | Swift / CocoaPods | 🔜 Planned |
| `RubyBackend` | gem / bundler | Ruby | 🔜 Planned |
| `DotnetBackend` | dotnet | .NET (C#/F#) | 🔜 Planned |
| `PhpBackend` | composer | PHP | 🔜 Planned |
| `VscodeBackend` | vsce | VS Code Extension | 🔜 Planned |
| `IntelliJBackend` | gradle | IntelliJ Plugin | 🔜 Planned |
| `BrowserExtBackend` | web-ext / zip | Chrome / Firefox | 🔜 Planned |

## Forge Protocol

Abstracts code forge operations (PRs, releases, labels). Features
**graceful degradation** — operations not supported by a forge are
logged as warnings rather than errors.

```python
class Forge(Protocol):
    def create_pr(self, *, title: str, body: str, head: str, base: str) -> str: ...
    def update_pr(self, pr_number: int, *, title: str, body: str) -> None: ...
    def list_prs(self, *, label: str, state: str) -> list[PrInfo]: ...
    def pr_data(self, pr_number: int) -> PrInfo: ...
    def add_label(self, pr_number: int, label: str) -> None: ...
    def remove_label(self, pr_number: int, label: str) -> None: ...
    def create_release(self, *, tag: str, title: str, body: str, draft: bool) -> str: ...
    def upload_release_asset(self, release_url: str, path: Path) -> None: ...
    def publish_release(self, release_url: str) -> None: ...
    def delete_release(self, tag: str) -> None: ...
```

| Implementation | Forge | Transport | Draft Releases | Labels |
|---|---|---|---|---|
| `GitHubCLIBackend` | GitHub | `gh` CLI | ✅ | ✅ |
| `GitHubAPIBackend` | GitHub | REST API | ✅ | ✅ |
| `GitLabCLIBackend` | GitLab | `glab` CLI | ❌ | ✅ (on MRs) |
| `BitbucketAPIBackend` | Bitbucket | REST API | ❌ | ❌ (no-op) |

!!! info "Choosing a forge backend"
    Use `--forge-backend cli` (default) for local development with `gh`
    installed. Use `--forge-backend api` in CI where only `GITHUB_TOKEN`
    is available.

## Registry Protocol

Abstracts package registry queries for version existence checks and
post-publish checksum verification.

```python
class Registry(Protocol):
    def version_exists(self, name: str, version: str) -> bool: ...
    def checksum(self, name: str, version: str, filename: str) -> ChecksumResult: ...
    def poll_version(self, name: str, version: str, *, timeout: float) -> bool: ...
```

| Implementation | Registry | Notes | Status |
|---|---|---|---|
| `PyPIBackend` | PyPI | Uses JSON API, async `httpx` | ✅ Shipped |
| `NpmRegistry` | npm | Uses npm registry API | ✅ Shipped |
| `CratesIoBackend` | crates.io | Uses crates.io API | ✅ Shipped |
| `GoProxyBackend` | Go module proxy | Uses `/@v/list` API | ✅ Shipped |
| `MavenCentralBackend` | Maven Central | Uses Solr search API | ✅ Shipped |
| `PubDevBackend` | pub.dev | Uses pub.dev API | ✅ Shipped |
| `NuGetBackend` | NuGet Gallery | Uses NuGet v3 API | 🔜 Planned |
| `RubyGemsBackend` | RubyGems.org | Uses RubyGems API | 🔜 Planned |
| `PackagistBackend` | Packagist | Uses Packagist API | 🔜 Planned |
| `SwiftRegistry` | Swift Package Index | Git-tag-based | 🔜 Planned |
| `CocoaPodsRegistry` | CocoaPods trunk | Uses trunk API | 🔜 Planned |
| `VscodeMarketplace` | VS Code Marketplace | Uses Gallery API | 🔜 Planned |
| `JetBrainsMarketplace` | JetBrains Marketplace | Uses plugins API | 🔜 Planned |
| `ChromeWebStore` | Chrome Web Store | Uses CWS API | 🔜 Planned |
| `FirefoxAddons` | Firefox Add-ons | Uses AMO API | 🔜 Planned |

## Workspace Protocol

Abstracts workspace discovery — scanning the workspace definition file
to enumerate all packages with their metadata.

```python
class Workspace(Protocol):
    async def discover(self) -> list[Package]: ...
```

| Implementation | Tool | Discovery Source | Status |
|---|---|---|---|
| `UvWorkspace` | uv | `pyproject.toml` `[tool.uv.workspace]` | ✅ Shipped |
| `PnpmWorkspace` | pnpm | `pnpm-workspace.yaml` | ✅ Shipped |
| `CargoWorkspace` | cargo | `Cargo.toml` `[workspace]` | ✅ Shipped |
| `DartWorkspace` | dart/melos | `pubspec.yaml` files | ✅ Shipped |
| `GoWorkspace` | go | `go.work` / `go.mod` | ✅ Shipped |
| `MavenWorkspace` | mvn/gradle | `pom.xml` / `settings.gradle.kts` | ✅ Shipped |
| `BazelWorkspace` | bazel | `MODULE.bazel` / `BUILD` files | ✅ Shipped |
| `KotlinWorkspace` | gradle | `settings.gradle.kts` with KMP targets | 🔜 Planned |
| `SwiftWorkspace` | swift | `Package.swift` files | 🔜 Planned |
| `CocoaPodsWorkspace` | cocoapods | `*.podspec` files | 🔜 Planned |
| `RubyWorkspace` | bundler | `*.gemspec` + `Gemfile` | 🔜 Planned |
| `DotnetWorkspace` | dotnet | `*.sln` / `Directory.Build.props` | 🔜 Planned |
| `PhpWorkspace` | composer | `composer.json` files | 🔜 Planned |
| `BrowserExtWorkspace` | — | `manifest.json` files | 🔜 Planned |

## Testing with Fake Backends

All protocols have simple implementations that can be used in tests:

```python
class FakeVCS:
    """In-memory VCS for tests."""
    def __init__(self):
        self.tags: dict[str, str] = {}
        self.commits: list[Commit] = []
        self._clean = True

    def tag_exists(self, tag: str) -> bool:
        return tag in self.tags

    def is_clean(self) -> bool:
        return self._clean
    # ... etc
```

See `tests/conftest.py` and individual test files for complete fake
backend implementations.
