# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Configuration reader for releasekit.

Reads ``releasekit.toml`` from the workspace root and returns a validated
:class:`ReleaseConfig` dataclass. The config file uses flat top-level keys
(no ``[tool.releasekit]`` nesting) so it works for any ecosystem — Python,
JS, Go, etc.

Key Concepts (ELI5)::

    ┌─────────────────────────┬────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ ReleaseConfig           │ A settings object for the release tool.   │
    │                         │ Like the control panel on a washing       │
    │                         │ machine — knobs for how to run.           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ load_config()           │ Read releasekit.toml + validate settings. │
    │                         │ Like reading and checking the recipe      │
    │                         │ before you start cooking.                 │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Fuzzy key matching      │ If you typo a config key, we suggest the  │
    │                         │ closest valid key. Like "did you mean?"   │
    │                         │ in a search engine.                       │
    └─────────────────────────┴────────────────────────────────────────────┘

Validation Pipeline::

    releasekit.toml
    ┌──────────────────┐
    │ tag_fromat = ...  │  ← typo!
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐     ┌──────────────────────────────┐
    │ 1. Unknown key   │────→│ RK-CONFIG-INVALID-KEY:       │
    │    detection     │     │ hint: "Did you mean          │
    └────────┬─────────┘     │       'tag_format'?"         │
             │               └──────────────────────────────┘
             ▼
    ┌──────────────────┐     ┌──────────────────────────────┐
    │ 2. Type check    │────→│ RK-CONFIG-INVALID-VALUE:     │
    │    each value    │     │ Expected str, got int        │
    └────────┬─────────┘     └──────────────────────────────┘
             │
             ▼
    ┌──────────────────┐     ┌──────────────────────────────┐
    │ 3. Value check   │────→│ RK-CONFIG-INVALID-VALUE:     │
    │    (enums, etc.) │     │ publish_from must be         │
    └────────┬─────────┘     │ "local" or "ci"              │
             │
             ▼
    ┌──────────────────┐
    │ ReleaseConfig()  │  ← frozen dataclass, ready to use
    └──────────────────┘

Supported keys in ``releasekit.toml``::

    tag_format         = "{name}-v{version}"     # per-package tag format
    umbrella_tag       = "v{version}"            # umbrella tag format
    publish_from       = "local"                 # "local" or "ci"
    groups             = { core = ["genkit"], plugins = ["genkit-plugin-*"] }
    exclude            = ["sample-*"]            # glob patterns to exclude
    exclude_publish    = ["genkit-plugin-xai"]     # discovered + bumped but not published
    exclude_bump       = ["group:samples"]         # discovered + checked but not bumped
    changelog          = true                    # generate CHANGELOG.md
    prerelease_mode    = "rollup"                # "rollup" or "separate"
    http_pool_size     = 10                      # httpx connection pool
    smoke_test         = true                    # run install smoke test

Usage::

    from releasekit.config import load_config

    cfg = load_config(Path('/path/to/workspace'))
    print(cfg.tag_format)  # "{name}-v{version}"
"""

from __future__ import annotations

import difflib
import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomlkit
import tomlkit.exceptions

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)

# The config file name at the workspace root.
CONFIG_FILENAME = 'releasekit.toml'

# Regex for valid workspace labels: lowercase letter followed by lowercase
# letters, digits, or hyphens.
_LABEL_RE = re.compile(r'[a-z][a-z0-9-]*')

# All recognized top-level keys in releasekit.toml.
VALID_KEYS: frozenset[str] = frozenset({
    'ai',
    'announcements',
    'branches',
    'calver_format',
    'default_branch',
    'forge',
    'hooks',
    'http_pool_size',
    'pr_title_template',
    'publish_from',
    'release_mode',
    'repo_name',
    'repo_owner',
    'schedule',
    'versioning_scheme',
    'workspace',
})

# Recognized keys inside each [workspace.<label>] section.
VALID_WORKSPACE_KEYS: frozenset[str] = frozenset({
    'ai',
    'announcements',
    'auto_merge',
    'bootstrap_sha',
    'branches',
    'calver_format',
    'changelog',
    'changelog_template',
    'changeset_dir',
    'core_package',
    'dist_tag',
    'ecosystem',
    'exclude',
    'exclude_bump',
    'exclude_publish',
    'extra_files',
    'groups',
    'hooks',
    'hooks_replace',
    'library_dirs',
    'major_on_zero',
    'max_commits',
    'namespace_dirs',
    'oci_cosign_sign',
    'oci_push_target',
    'oci_remote_tags',
    'oci_repository',
    'oci_sbom_attest',
    'sbom',
    'sbom_formats',
    'osv_severity_threshold',
    'packages',
    'pep740_attestations',
    'skip_checks',
    'plugin_dirs',
    'plugin_prefix',
    'prerelease_label',
    'prerelease_mode',
    'propagate_bumps',
    'provenance',
    'publish_branch',
    'registry_url',
    'sign_provenance',
    'slsa_provenance',
    'release_mode',
    'root',
    'schedule',
    'secondary_tag_format',
    'smoke_test',
    'synchronize',
    'tag_format',
    'tool',
    'umbrella_tag',
    'versioning_scheme',
})

# Allowed ecosystem values for the ``ecosystem`` field.
ALLOWED_ECOSYSTEMS: frozenset[str] = frozenset({
    'bazel',
    'clojure',
    'dart',
    'go',
    'java',
    'js',
    'jvm',
    'kotlin',
    'python',
    'rust',
})

# Default versioning scheme per ecosystem (used when ``versioning_scheme``
# is not specified).
#
# - **python** → ``pep440``: PyPI requires PEP 440 (``1.0.0a1``, ``1.0.0rc1``).
# - All others → ``semver``: npm, Go modules, Cargo/crates.io, Maven/Gradle,
#   pub.dev, Leiningen/Clojars, and BCR all use Semantic Versioning 2.0.0.
DEFAULT_VERSIONING_SCHEMES: dict[str, str] = {
    'bazel': 'semver',
    'clojure': 'semver',
    'dart': 'semver',
    'go': 'semver',
    'java': 'semver',
    'js': 'semver',
    'jvm': 'semver',
    'kotlin': 'semver',
    'python': 'pep440',
    'rust': 'semver',
}

# Default tool for each ecosystem (used when ``tool`` is not specified).
DEFAULT_TOOLS: dict[str, str] = {
    'bazel': 'bazel',
    'clojure': 'lein',
    'dart': 'pub',
    'go': 'go',
    'java': 'gradle',
    'js': 'pnpm',
    'jvm': 'gradle',
    'kotlin': 'gradle',
    'python': 'uv',
    'rust': 'cargo',
}

# Allowed values for enum-like config fields.
ALLOWED_PUBLISH_FROM: frozenset[str] = frozenset({'local', 'ci'})
ALLOWED_FORGES: frozenset[str] = frozenset({'github', 'gitlab', 'bitbucket', 'none'})
ALLOWED_PRERELEASE_MODES: frozenset[str] = frozenset({'rollup', 'separate'})
ALLOWED_RELEASE_MODES: frozenset[str] = frozenset({'pr', 'continuous'})
ALLOWED_VERSIONING_SCHEMES: frozenset[str] = frozenset({'semver', 'calver', 'pep440'})
ALLOWED_CADENCES: frozenset[str] = frozenset({
    'daily',
    'weekly:monday',
    'weekly:tuesday',
    'weekly:wednesday',
    'weekly:thursday',
    'weekly:friday',
    'biweekly',
    'on-push',
})
ALLOWED_MIN_BUMPS: frozenset[str] = frozenset({'patch', 'minor', 'major'})
ALLOWED_HOOK_EVENTS: frozenset[str] = frozenset({
    'after_publish',
    'after_tag',
    'before_prepare',
    'before_publish',
})

# Valid pre-release labels.
ALLOWED_PRERELEASE_LABELS: frozenset[str] = frozenset({
    'alpha',
    'beta',
    'dev',
    'rc',
})

# Valid keys inside a [workspace.<label>.packages.<name>] section.
VALID_PACKAGE_KEYS: frozenset[str] = frozenset({
    'calver_format',
    'changelog',
    'changelog_template',
    'dist_tag',
    'extra_files',
    'major_on_zero',
    'prerelease_label',
    'provenance',
    'registry_url',
    'skip_checks',
    'smoke_test',
    'versioning_scheme',
})

# Valid keys inside an [announcements] section.
VALID_ANNOUNCEMENT_KEYS: frozenset[str] = frozenset({
    'custom_webhooks',
    'discord_webhook',
    'enabled',
    'irc_webhook',
    'linkedin_access_token',
    'linkedin_org_id',
    'overrides',
    'rollback_template',
    'slack_webhook',
    'teams_webhook',
    'template',
    'twitter_bearer_token',
})

# Valid keys inside a [schedule] or [workspace.<label>.schedule] section.
VALID_SCHEDULE_KEYS: frozenset[str] = frozenset({
    'cadence',
    'cooldown_minutes',
    'min_bump',
    'release_window',
})

# Valid keys inside an [ai] section.
VALID_AI_KEYS: frozenset[str] = frozenset({
    'blocklist_file',
    'codename_theme',
    'enabled',
    'features',
    'max_output_tokens',
    'models',
    'plugins',
    'temperature',
})

# Valid keys inside [ai.features].
VALID_AI_FEATURES_KEYS: frozenset[str] = frozenset({
    'ai_hints',
    'announce',
    'classify',
    'codename',
    'detect_breaking',
    'draft_advisory',
    'enhance',
    'migration_guide',
    'scope',
    'summarize',
    'tailor_announce',
})

# Default model fallback chain: local Ollama first, then Google GenAI cloud.
_DEFAULT_AI_MODELS: list[str] = [
    'ollama/gemma3:4b',
    'ollama/gemma3:1b',
    'google-genai/gemini-3.0-flash-preview',
]


@dataclass(frozen=True)
class AiFeaturesConfig:
    """Per-feature AI toggles.

    Controls which AI features are active. Features default to the
    values shown below. All features respect the global ``--no-ai``
    kill switch regardless of their individual setting.

    Attributes:
        summarize: AI release note summarization (Phase 10).
        codename: AI-generated release codename (Phase 10).
        enhance: Changelog entry enhancement (Phase 11a).
        detect_breaking: Breaking change detection (Phase 11b).
        classify: Semantic version classification (Phase 11c).
        scope: Commit scoping (Phase 11d).
        migration_guide: Migration guide generation (Phase 12a).
        tailor_announce: Announcement tailoring (Phase 12b).
        announce: AI-generated per-channel announcements (Phase 12b).
            When enabled, AI generates tailored messages for each
            channel (Slack, Discord, Twitter, LinkedIn, etc.) from
            the release notes.  Falls back to templates when disabled
            or when AI fails.
        draft_advisory: Security advisory drafting (Phase 12c).
        ai_hints: Contextual error hints (Phase 12d).
    """

    summarize: bool = True
    codename: bool = True
    enhance: bool = True
    detect_breaking: bool = True
    classify: bool = False
    scope: bool = False
    migration_guide: bool = True
    tailor_announce: bool = False
    announce: bool = False
    draft_advisory: bool = False
    ai_hints: bool = False


@dataclass(frozen=True)
class AiConfig:
    """AI configuration for Genkit-powered features.

    Controls model selection, generation parameters, and feature
    toggles. AI is **on by default**. Disable globally via
    ``--no-ai`` CLI flag, ``RELEASEKIT_NO_AI=1`` env var, or
    ``ai.enabled = false`` in ``releasekit.toml``.

    The ``models`` list is a **fallback chain**: each model is tried
    in order. If a model is unavailable (not pulled, provider down,
    API key missing), the next one is tried. If ALL models fail,
    the feature falls back to non-AI behavior and logs a warning.

    Model strings use ``provider/model`` format (e.g.
    ``"ollama/gemma3:4b"``, ``"google-genai/gemini-3.0-flash-preview"``).

    Attributes:
        enabled: Master switch for all AI features.
        models: Ordered list of ``provider/model`` strings to try.
        temperature: Generation temperature (0.0-1.0). Lower is
            more factual.
        max_output_tokens: Maximum tokens in the generated response.
        codename_theme: Theme for AI-generated release codenames.
            Built-in themes: ``"mountains"``, ``"animals"``,
            ``"space"``, ``"mythology"``, ``"gems"``,
            ``"weather"``, ``"cities"``. Any custom string is
            also accepted (e.g. ``"deep sea creatures"``). Empty
            string means no codename generation.
        blocklist_file: Path or URL to a custom blocked-words file
            that **extends** the built-in ``data/blocked_words.txt``.
            Local paths are resolved relative to the workspace root.
            HTTP/HTTPS URLs are fetched asynchronously at runtime.
            When set, words from both the built-in and custom files
            are merged into a single filter.  Empty string (default)
            means only the built-in list is used.
        plugins: Explicit list of Genkit plugin names to load (e.g.
            ``["ollama", "google-genai"]``).  When empty (default),
            plugins are auto-discovered from model string prefixes.
            Use this to force-load a plugin that doesn't match a
            model prefix, or to restrict which plugins are loaded.
        features: Per-feature toggles.
    """

    enabled: bool = True
    models: list[str] = field(default_factory=lambda: list(_DEFAULT_AI_MODELS))
    temperature: float = 0.2
    max_output_tokens: int = 4096
    codename_theme: str = 'mountains'
    blocklist_file: str = ''
    plugins: list[str] = field(default_factory=list)
    features: AiFeaturesConfig = field(default_factory=AiFeaturesConfig)


@dataclass(frozen=True)
class ScheduleConfig:
    """Scheduled release configuration.

    Used by ``releasekit should-release`` to decide whether a release
    should happen based on cadence, time window, and cooldown.

    Attributes:
        cadence: Release cadence: ``"on-push"``, ``"daily"``,
            ``"weekly:monday"`` through ``"weekly:friday"``,
            or ``"biweekly"``.
        release_window: UTC time range during which releases are
            allowed (e.g. ``"14:00-16:00"``). Empty means any time.
        cooldown_minutes: Minimum minutes between releases.
        min_bump: Minimum bump level to trigger a release:
            ``"patch"``, ``"minor"``, or ``"major"``. Empty means
            any releasable commit triggers a release.
    """

    cadence: str = 'on-push'
    release_window: str = ''
    cooldown_minutes: int = 0
    min_bump: str = ''


@dataclass(frozen=True)
class HooksConfig:
    """Lifecycle hooks configuration.

    Shell commands executed at specific points in the release pipeline.
    Template variables: ``${version}``, ``${name}``, ``${tag}``.

    Hooks **concatenate** across tiers (root → workspace → package)
    unless ``hooks_replace`` is set at the workspace or package level.

    Attributes:
        before_prepare: Commands to run before ``prepare`` (version bump).
        before_publish: Commands to run before ``publish``.
        after_publish: Commands to run after ``publish``.
        after_tag: Commands to run after git tagging.
    """

    before_prepare: list[str] = field(default_factory=list)
    before_publish: list[str] = field(default_factory=list)
    after_publish: list[str] = field(default_factory=list)
    after_tag: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnnouncementConfig:
    """Release announcement configuration.

    Webhook URLs can contain environment variable references prefixed
    with ``$`` (e.g. ``$SLACK_WEBHOOK_URL``), which are expanded at
    send time.

    Attributes:
        slack_webhook: Slack incoming webhook URL.
        discord_webhook: Discord webhook URL.
        teams_webhook: Microsoft Teams incoming webhook URL.
        irc_webhook: IRC webhook/bridge URL. Supports ``ircs://`` scheme
            for TLS connections (e.g.
            ``ircs://irc.libera.chat:6697/#channel``) or HTTP bridge
            URLs (e.g. ``$IRC_BRIDGE_URL``).
        twitter_bearer_token: Twitter/X API v2 OAuth 2.0 Bearer token
            (requires ``tweet.write`` scope).
        linkedin_access_token: LinkedIn API OAuth 2.0 access token
            (requires ``w_organization_social`` scope).
        linkedin_org_id: LinkedIn organization ID for posting.
        custom_webhooks: List of custom webhook URLs.
        template: Message template with ``${version}``, ``${packages}``,
            ``${count}``, ``${url}`` placeholders.
        rollback_template: Template used for rollback announcements.
            Falls back to ``template`` if empty.
        enabled: Whether announcements are enabled.
        overrides: Per-group or per-package announcement overrides.
            Keys are group names (matching ``groups`` in
            ``WorkspaceConfig``) or exact package names. Values are
            partial ``AnnouncementConfig`` dicts that are merged on
            top of the base config when announcing that group/package.
    """

    slack_webhook: str = ''
    discord_webhook: str = ''
    teams_webhook: str = ''
    irc_webhook: str = ''
    twitter_bearer_token: str = ''
    linkedin_access_token: str = ''
    linkedin_org_id: str = ''
    custom_webhooks: list[str] = field(default_factory=list)
    template: str = '\U0001f680 Released ${version}: ${packages}'
    rollback_template: str = '\u26a0\ufe0f Rolled back ${version}: ${packages}'
    enabled: bool = True
    overrides: dict[str, AnnouncementConfig] = field(default_factory=dict)


@dataclass(frozen=True)
class PackageConfig:
    """Per-package configuration overrides.

    Fields that are set (non-empty / non-default) override the
    corresponding workspace-level value for a specific package.
    Use :func:`resolve_package_config` to merge workspace defaults
    with per-package overrides.

    Configured via ``[workspace.<label>.packages.<name>]`` sections
    in ``releasekit.toml``::

        [workspace.monorepo.packages."my-js-lib"]
        versioning_scheme = "semver"
        dist_tag = "next"

        [workspace.monorepo.packages."my-py-lib"]
        versioning_scheme = "pep440"
        registry_url = "https://test.pypi.org"

    Attributes:
        versioning_scheme: ``"semver"``, ``"pep440"``, or ``"calver"``.
        calver_format: CalVer format string (e.g. ``"YYYY.MM.MICRO"``).
        prerelease_label: Default pre-release label for this package.
        changelog: Whether to generate CHANGELOG.md entries.
        changelog_template: Path to a Jinja2 template for changelog.
        smoke_test: Whether to run install smoke test after publish.
        major_on_zero: If ``True``, breaking changes on ``0.x`` produce
            MAJOR bumps.
        extra_files: Extra file paths with version strings to bump.
        dist_tag: npm dist-tag for this package.
        registry_url: Custom registry URL for publishing.
        provenance: Generate npm provenance attestation.
        skip_checks: List of check names to skip for this package.
            Merged with workspace-level ``skip_checks``. Use this to
            suppress checks for a specific package (e.g.
            ``['type_markers', 'naming_convention']``).
    """

    versioning_scheme: str = ''
    calver_format: str = ''
    prerelease_label: str = ''
    changelog: bool | None = None
    changelog_template: str = ''
    smoke_test: bool | None = None
    major_on_zero: bool | None = None
    extra_files: list[str] = field(default_factory=list)
    dist_tag: str = ''
    registry_url: str = ''
    provenance: bool | None = None
    skip_checks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkspaceConfig:
    """Per-workspace configuration for a single release unit.

    Each ``[workspace.<label>]`` section in ``releasekit.toml`` produces
    one instance. The ``label`` is a user-chosen name for the workspace
    (e.g. ``"py"``, ``"js"``, ``"dotprompt-rust"``).

    Attributes:
        label: User-chosen workspace name from the TOML section key.
        ecosystem: Ecosystem identifier (``"python"``, ``"js"``,
            ``"go"``, ``"rust"``, ``"java"``, ``"kotlin"``,
            ``"clojure"``, ``"dart"``).
        tool: Build/package-manager tool (``"uv"``, ``"pnpm"``,
            ``"cargo"``, ``"bazel"``, etc.). Defaults per ecosystem.
        root: Relative path from the monorepo root to the workspace
            root directory (e.g. ``"py"`` or ``"."`` for root-level).
        tag_format: Per-package git tag format string.
            Placeholders: ``{name}``, ``{version}``.
        umbrella_tag: Umbrella git tag format string.
            Placeholder: ``{version}``.
        groups: Named groups of package patterns for selective release.
        exclude: Glob patterns for packages to exclude from discovery.
        exclude_publish: Glob patterns (or ``group:<name>`` refs) for
            packages to skip during publish.
        exclude_bump: Glob patterns (or ``group:<name>`` refs) for
            packages to skip during version bumps.
        changelog: Whether to generate CHANGELOG.md entries.
        changelog_template: Path to a Jinja2 template for changelog
            rendering. If empty, uses the built-in default format.
        changeset_dir: Path to the ``.changeset/`` directory for
            hybrid changeset+conventional-commit mode. Empty disables.
        prerelease_label: Default pre-release label (``"alpha"``,
            ``"beta"``, ``"rc"``, ``"dev"``). Empty for stable.
        prerelease_mode: ``"rollup"`` or ``"separate"``.
        smoke_test: Whether to run install smoke test after publish.
        propagate_bumps: If ``True`` (default), bumping a library
            triggers transitive PATCH bumps in all its dependents.
            Set to ``False`` to release libraries independently
            without cascading bumps to consuming packages.
        synchronize: If ``True``, all packages share the same version.
        major_on_zero: If ``True``, breaking changes on ``0.x`` produce
            MAJOR bumps.
        core_package: Name of the core package for version checks.
        plugin_prefix: Expected prefix for plugin package names.
        namespace_dirs: Namespace directories requiring PEP 420 checks.
        library_dirs: Parent dirs whose children need ``py.typed``.
        plugin_dirs: Parent dirs whose children follow naming conventions.
        extra_files: Extra file paths with version strings to bump.
        dist_tag: npm dist-tag for ``pnpm publish --tag`` (e.g.
            ``"latest"``, ``"next"``). ``None`` means use the
            registry default (``latest``). Ignored for Python.
        publish_branch: Allow publishing from a non-default branch.
            Maps to ``pnpm publish --publish-branch``. ``None`` means
            use the default (``main``/``master``). Ignored for Python.
        registry_url: Custom registry URL for publishing and polling.
            Use this to point at a test/staging registry (e.g.
            ``https://test.pypi.org`` for Python, ``https://staging-crates.io``
            for Rust). When empty, the production registry is used.
        provenance: Generate npm provenance attestation via
            ``pnpm publish --provenance``. Ignored for Python.
        slsa_provenance: Generate SLSA Provenance v1 in-toto statement
            for all published artifacts. The provenance file is written
            alongside the release manifest and attached to the GitHub
            Release.
        sign_provenance: Sign the SLSA provenance file with Sigstore
            keyless signing. Requires ``slsa_provenance = true`` and
            an OIDC identity (CI environment or interactive OAuth2).
        oci_push_target: Explicit Bazel target label for OCI push
            (e.g. ``"//:push"``). Empty means derive from package.
        oci_repository: OCI registry repository (e.g.
            ``"gcr.io/my-project/my-image"``). Passed to
            ``oci_push --repository``.
        oci_remote_tags: Tags to apply after push-by-digest (e.g.
            ``["latest", "{version}"]``). Uses ``crane tag``.
        oci_cosign_sign: Sign container images with Sigstore cosign
            keyless signing after push. **On by default** for
            safe-by-default supply chain security.
        oci_sbom_attest: Attach SBOM attestation to container images
            via ``cosign attest --type spdx``. **On by default** for
            safe-by-default supply chain transparency.
        sbom: Generate Software Bill of Materials (SBOM) during publish.
            **On by default** for supply chain transparency.  SBOMs
            list every component (package) in a release with its version,
            license, supplier, and dependency relationships.
        sbom_formats: SBOM output formats to generate.  Allowed values:
            ``"cyclonedx"`` (CycloneDX 1.5 JSON) and ``"spdx"`` (SPDX
            2.3 JSON).  **Both formats by default.**
        pep740_attestations: Generate PEP 740 digital attestations for
            each Python distribution file using ``pypi-attestations``.
            Requires ambient OIDC credentials (Trusted Publisher).
            Only applies to Python ecosystem publishes. **On by default**.
        osv_severity_threshold: Minimum OSV severity level to report
            during preflight vulnerability scanning. One of ``CRITICAL``,
            ``HIGH``, ``MEDIUM``, ``LOW``. Default: ``HIGH``.
        skip_checks: List of check names to skip during preflight and
            workspace health checks. Use this to suppress checks that
            are not applicable to a workspace (e.g.
            ``['security_insights', 'compliance']``). Check names
            correspond to the identifiers used in
            :class:`~releasekit.preflight.PreflightResult`.
        ai: Per-workspace AI configuration override.  When set,
            fields are merged on top of the global ``[ai]`` config.
            Non-default fields in the workspace override win; unset
            fields inherit from the global config.  ``None`` means
            use the global config as-is.
        announcements: Announcement configuration for this workspace.
    """

    label: str = ''
    ecosystem: str = ''
    tool: str = ''
    root: str = '.'
    tag_format: str = '{name}-v{version}'
    secondary_tag_format: str = ''
    umbrella_tag: str = 'v{version}'
    groups: dict[str, list[str]] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    exclude_publish: list[str] = field(default_factory=list)
    exclude_bump: list[str] = field(default_factory=list)
    changelog: bool = True
    changelog_template: str = ''
    changeset_dir: str = ''
    prerelease_label: str = ''
    prerelease_mode: str = 'rollup'
    smoke_test: bool = True
    propagate_bumps: bool = True
    synchronize: bool = False
    major_on_zero: bool = False
    core_package: str = ''
    plugin_prefix: str = ''
    namespace_dirs: list[str] = field(default_factory=list)
    library_dirs: list[str] = field(default_factory=list)
    plugin_dirs: list[str] = field(default_factory=list)
    extra_files: list[str] = field(default_factory=list)
    max_commits: int = 0
    bootstrap_sha: str = ''
    auto_merge: bool = False
    dist_tag: str = ''
    publish_branch: str = ''
    registry_url: str = ''
    provenance: bool = True
    slsa_provenance: bool = True
    sign_provenance: bool = True
    oci_push_target: str = ''
    oci_repository: str = ''
    oci_remote_tags: list[str] = field(default_factory=list)
    oci_cosign_sign: bool = True
    oci_sbom_attest: bool = True
    sbom: bool = True
    sbom_formats: list[str] = field(default_factory=lambda: ['cyclonedx', 'spdx'])
    pep740_attestations: bool = True
    osv_severity_threshold: str = 'HIGH'
    skip_checks: list[str] = field(default_factory=list)
    release_mode: str = 'pr'
    versioning_scheme: str = 'semver'
    calver_format: str = 'YYYY.MM.MICRO'
    hooks: HooksConfig = field(default_factory=HooksConfig)
    hooks_replace: bool = False
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    branches: dict[str, str] = field(default_factory=dict)
    ai: AiConfig | None = None
    announcements: AnnouncementConfig = field(default_factory=AnnouncementConfig)
    packages: dict[str, PackageConfig] = field(default_factory=dict)


def resolve_package_config(
    ws: WorkspaceConfig,
    package_name: str,
) -> PackageConfig:
    """Resolve the effective per-package config for a package.

    Merges workspace-level defaults with any per-package overrides
    from ``ws.packages[package_name]``. Override fields that are
    set (non-empty / non-None) win; unset fields inherit from the
    workspace.

    Also checks group membership: if the package matches a group
    pattern and that group name has a packages entry, it is used
    as a fallback before workspace defaults.

    Args:
        ws: The workspace configuration.
        package_name: Exact package name.

    Returns:
        Resolved :class:`PackageConfig` for this package.
    """
    # Build the workspace-level baseline.
    baseline = PackageConfig(
        versioning_scheme=ws.versioning_scheme,
        calver_format=ws.calver_format,
        prerelease_label=ws.prerelease_label,
        changelog=ws.changelog,
        changelog_template=ws.changelog_template,
        smoke_test=ws.smoke_test,
        major_on_zero=ws.major_on_zero,
        extra_files=list(ws.extra_files),
        dist_tag=ws.dist_tag,
        registry_url=ws.registry_url,
        provenance=ws.provenance,
    )

    if not ws.packages:
        return baseline

    # 1. Exact package name match.
    override = ws.packages.get(package_name)

    # 2. Group membership match (first group wins).
    if override is None:
        for group_name, patterns in ws.groups.items():
            if group_name in ws.packages:
                for pattern in patterns:
                    if fnmatch.fnmatch(package_name, pattern):
                        override = ws.packages[group_name]
                        break
                if override is not None:
                    break

    if override is None:
        return baseline

    return _merge_package_configs(baseline, override)


def _merge_package_configs(
    base: PackageConfig,
    override: PackageConfig,
) -> PackageConfig:
    """Merge an override PackageConfig on top of a base.

    Non-empty/non-None override fields replace the base.
    """
    return PackageConfig(
        versioning_scheme=override.versioning_scheme or base.versioning_scheme,
        calver_format=override.calver_format or base.calver_format,
        prerelease_label=override.prerelease_label or base.prerelease_label,
        changelog=override.changelog if override.changelog is not None else base.changelog,
        changelog_template=override.changelog_template or base.changelog_template,
        smoke_test=override.smoke_test if override.smoke_test is not None else base.smoke_test,
        major_on_zero=override.major_on_zero if override.major_on_zero is not None else base.major_on_zero,
        extra_files=override.extra_files or base.extra_files,
        dist_tag=override.dist_tag or base.dist_tag,
        registry_url=override.registry_url or base.registry_url,
        provenance=override.provenance if override.provenance is not None else base.provenance,
        skip_checks=list({*base.skip_checks, *override.skip_checks}),
    )


def build_package_configs(
    ws: WorkspaceConfig,
    package_names: list[str],
) -> dict[str, PackageConfig]:
    """Build a per-package config dict for all packages in a workspace.

    Calls :func:`resolve_package_config` for each package name and
    returns a dict keyed by package name. This is the dict you pass
    to ``compute_bumps(package_configs=...)``.

    Args:
        ws: The workspace configuration.
        package_names: List of discovered package names.

    Returns:
        Dict mapping package name → resolved :class:`PackageConfig`.
    """
    return {name: resolve_package_config(ws, name) for name in package_names}


def build_skip_map(
    ws: WorkspaceConfig,
    package_names: list[str],
) -> dict[str, frozenset[str]]:
    """Build a per-package check skip map from workspace + package configs.

    For each package, the skip set is the union of:
    - ``ws.skip_checks`` (workspace-level skips apply to all packages)
    - ``PackageConfig.skip_checks`` for that package (per-package overrides)

    Args:
        ws: The workspace configuration.
        package_names: List of discovered package names.

    Returns:
        Dict mapping package name → frozenset of check names to skip.
        Only packages with at least one skip are included.
    """
    ws_skips = frozenset(ws.skip_checks)
    result: dict[str, frozenset[str]] = {}
    for name in package_names:
        pkg_cfg = resolve_package_config(ws, name)
        combined = ws_skips | frozenset(pkg_cfg.skip_checks)
        if combined:
            result[name] = combined
    return result


def resolve_workspace_ai_config(
    global_ai: AiConfig,
    ws: WorkspaceConfig,
) -> AiConfig:
    """Resolve the effective AI config for a workspace.

    Merges the workspace-level ``[workspace.<label>.ai]`` overrides
    on top of the global ``[ai]`` config.  Non-default workspace
    fields win; unset fields inherit from the global config.

    If the workspace has no ``ai`` override (``ws.ai is None``),
    the global config is returned as-is.

    Args:
        global_ai: The global ``[ai]`` config from :class:`ReleaseConfig`.
        ws: The workspace configuration.

    Returns:
        Merged :class:`AiConfig` for this workspace.
    """
    if ws.ai is None:
        return global_ai

    override = ws.ai
    default = AiConfig()

    ov, df, gl = override, default, global_ai

    return AiConfig(
        enabled=ov.enabled if ov.enabled != df.enabled else gl.enabled,
        models=ov.models if ov.models != df.models else gl.models,
        temperature=(ov.temperature if ov.temperature != df.temperature else gl.temperature),
        max_output_tokens=(
            ov.max_output_tokens if ov.max_output_tokens != df.max_output_tokens else gl.max_output_tokens
        ),
        codename_theme=(ov.codename_theme if ov.codename_theme != df.codename_theme else gl.codename_theme),
        blocklist_file=ov.blocklist_file or gl.blocklist_file,
        plugins=ov.plugins if ov.plugins else gl.plugins,
        features=_merge_ai_features(gl.features, ov.features),
    )


def _merge_ai_features(
    base: AiFeaturesConfig,
    override: AiFeaturesConfig,
) -> AiFeaturesConfig:
    """Merge workspace AI feature toggles on top of global ones.

    Non-default override values win; default values inherit from base.
    """
    default = AiFeaturesConfig()
    kwargs: dict[str, bool] = {}
    for f in (
        'summarize',
        'codename',
        'enhance',
        'detect_breaking',
        'classify',
        'scope',
        'migration_guide',
        'tailor_announce',
        'announce',
        'draft_advisory',
        'ai_hints',
    ):
        override_val = getattr(override, f)
        base_val = getattr(base, f)
        default_val = getattr(default, f)
        kwargs[f] = override_val if override_val != default_val else base_val
    return AiFeaturesConfig(**kwargs)


@dataclass(frozen=True)
class ReleaseConfig:
    """Validated configuration for a releasekit run.

    Global settings live at the top level. Per-workspace settings
    live under ``[workspace.<label>]`` sections and are stored in
    the :attr:`workspaces` dict keyed by user-chosen label.

    Attributes:
        forge: Code forge platform: ``"github"``, ``"gitlab"``,
            ``"bitbucket"``, or ``"none"``.
        repo_owner: Repository owner or organization.
        repo_name: Repository name.
        default_branch: Override the default branch name.
        publish_from: ``"local"`` or ``"ci"``.
        http_pool_size: Max connections for the httpx connection pool.
        pr_title_template: Template for the Release PR title.
        workspaces: Per-workspace configs keyed by label
            (e.g. ``{"py": WorkspaceConfig(...), "js": ...}``).
        config_path: Path to the releasekit.toml that was loaded.
    """

    forge: str = 'github'
    repo_owner: str = ''
    repo_name: str = ''
    default_branch: str = ''
    publish_from: str = 'local'
    http_pool_size: int = 10
    pr_title_template: str = 'chore(release): v{version}'
    release_mode: str = 'pr'
    versioning_scheme: str = 'semver'
    calver_format: str = 'YYYY.MM.MICRO'
    ai: AiConfig = field(default_factory=AiConfig)
    hooks: HooksConfig = field(default_factory=HooksConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    branches: dict[str, str] = field(default_factory=dict)
    announcements: AnnouncementConfig = field(default_factory=AnnouncementConfig)
    workspaces: dict[str, WorkspaceConfig] = field(default_factory=dict)
    config_path: Path | None = None


def _suggest_key(unknown: str) -> str | None:
    """Return the closest valid key for a typo, or None."""
    matches = difflib.get_close_matches(unknown, VALID_KEYS, n=1, cutoff=0.6)
    return matches[0] if matches else None


_GLOBAL_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    'ai': dict,
    'announcements': dict,
    'branches': dict,
    'calver_format': str,
    'default_branch': str,
    'forge': str,
    'hooks': dict,
    'http_pool_size': int,
    'pr_title_template': str,
    'publish_from': str,
    'release_mode': str,
    'repo_name': str,
    'repo_owner': str,
    'schedule': dict,
    'versioning_scheme': str,
}

_WORKSPACE_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    'ai': dict,
    'announcements': dict,
    'auto_merge': bool,
    'bootstrap_sha': str,
    'branches': dict,
    'calver_format': str,
    'changelog': bool,
    'changelog_template': str,
    'changeset_dir': str,
    'core_package': str,
    'dist_tag': str,
    'ecosystem': str,
    'exclude': list,
    'exclude_bump': list,
    'exclude_publish': list,
    'extra_files': list,
    'groups': dict,
    'hooks': dict,
    'hooks_replace': bool,
    'library_dirs': list,
    'major_on_zero': bool,
    'max_commits': int,
    'namespace_dirs': list,
    'oci_cosign_sign': bool,
    'oci_push_target': str,
    'oci_remote_tags': list,
    'oci_repository': str,
    'oci_sbom_attest': bool,
    'sbom': bool,
    'sbom_formats': list,
    'osv_severity_threshold': str,
    'pep740_attestations': bool,
    'skip_checks': list,
    'plugin_dirs': list,
    'plugin_prefix': str,
    'prerelease_label': str,
    'prerelease_mode': str,
    'propagate_bumps': bool,
    'provenance': bool,
    'publish_branch': str,
    'registry_url': str,
    'sign_provenance': bool,
    'slsa_provenance': bool,
    'release_mode': str,
    'root': str,
    'schedule': dict,
    'secondary_tag_format': str,
    'smoke_test': bool,
    'synchronize': bool,
    'tag_format': str,
    'tool': str,
    'umbrella_tag': str,
    'versioning_scheme': str,
}


def _validate_value_type(
    key: str,
    value: Any,  # noqa: ANN401 — dynamic config values
    type_map: dict[str, type | tuple[type, ...]],
    *,
    context: str = 'releasekit.toml',
) -> None:
    """Raise if a config value has the wrong type."""
    expected = type_map.get(key)
    if expected is None:
        return
    if not isinstance(value, expected):
        type_name = expected.__name__ if isinstance(expected, type) else str(expected)
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"'{key}' must be {type_name}, got {type(value).__name__}",
            hint=f'Check the value of {key} in {context}.',
        )


def _validate_forge(value: str) -> None:
    """Raise if forge is not a recognized value."""
    if value not in ALLOWED_FORGES:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"forge must be one of {sorted(ALLOWED_FORGES)}, got '{value}'",
            hint="Use 'github', 'gitlab', 'bitbucket', or 'none'.",
        )


def _validate_publish_from(value: str) -> None:
    """Raise if publish_from is not a recognized value."""
    if value not in ALLOWED_PUBLISH_FROM:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"publish_from must be one of {sorted(ALLOWED_PUBLISH_FROM)}, got '{value}'",
            hint="Use 'local' for publishing from your machine, 'ci' for CI pipelines.",
        )


def _validate_prerelease_mode(value: str) -> None:
    """Raise if prerelease_mode is not a recognized value."""
    if value not in ALLOWED_PRERELEASE_MODES:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"prerelease_mode must be one of {sorted(ALLOWED_PRERELEASE_MODES)}, got '{value}'",
            hint="Use 'rollup' to merge prerelease entries into the final release.",
        )


def _validate_groups(groups: dict[str, Any]) -> dict[str, list[str]]:  # noqa: ANN401 — dynamic config
    """Validate and normalize the groups mapping."""
    result: dict[str, list[str]] = {}
    for group_name, patterns in groups.items():
        if not isinstance(patterns, list):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f"Group '{group_name}' must be a list of glob patterns, got {type(patterns).__name__}",
                hint=f'Example: groups.{group_name} = ["genkit", "genkit-plugin-*"]',
            )
        for pattern in patterns:
            if not isinstance(pattern, str):
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=f"Group '{group_name}' patterns must be strings, got {type(pattern).__name__}",
                    hint=f'Each pattern in groups.{group_name} must be a quoted string.',
                )
        result[group_name] = list(patterns)
    return result


def _validate_string_list(key: str, items: list[object], context: str) -> None:
    """Raise if any item in a list is not a string."""
    for item in items:
        if not isinstance(item, str):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f"'{key}' items must be strings, got {type(item).__name__}: {item!r}",
                hint=f'Each {key} entry should be a glob pattern string in {context}.',
            )


def _validate_workspace_label(label: str) -> None:
    """Raise if a workspace label contains invalid characters."""
    if not _LABEL_RE.fullmatch(label):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_KEY,
            message=f"Workspace label '{label}' is invalid",
            hint='Labels must start with a lowercase letter and contain only lowercase letters, digits, and hyphens.',
        )


def _validate_release_mode(value: str, context: str = 'releasekit.toml') -> None:
    """Raise if release_mode is not a recognized value."""
    if value not in ALLOWED_RELEASE_MODES:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"release_mode must be one of {sorted(ALLOWED_RELEASE_MODES)}, got '{value}'",
            hint=f"Use 'pr' for PR-based releases or 'continuous' for direct tag+publish. Check {context}.",
        )


def _validate_versioning_scheme(value: str, context: str = 'releasekit.toml') -> None:
    """Raise if versioning_scheme is not a recognized value."""
    if value not in ALLOWED_VERSIONING_SCHEMES:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"versioning_scheme must be one of {sorted(ALLOWED_VERSIONING_SCHEMES)}, got '{value}'",
            hint=f"Use 'semver', 'pep440', or 'calver'. Check {context}.",
        )


def _parse_ai(
    raw: dict[str, Any],  # noqa: ANN401
    context: str = 'releasekit.toml',
) -> AiConfig:
    """Parse and validate an ``[ai]`` section."""
    for key in raw:
        if key not in VALID_AI_KEYS:
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown key '{key}' in {context} [ai]",
                hint=f'Valid ai keys: {sorted(VALID_AI_KEYS)}',
            )

    enabled = raw.get('enabled', True)
    if not isinstance(enabled, bool):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'ai.enabled must be a boolean, got {type(enabled).__name__}',
            hint=f'Use enabled = true or enabled = false in {context} [ai].',
        )

    models = raw.get('models', list(_DEFAULT_AI_MODELS))
    if not isinstance(models, list):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'ai.models must be a list of strings, got {type(models).__name__}',
            hint=f'Use models = ["ollama/gemma3:4b", ...] in {context} [ai].',
        )
    for i, m in enumerate(models):
        if not isinstance(m, str):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f'ai.models[{i}] must be a string, got {type(m).__name__}: {m!r}',
                hint='Each model must be a "provider/model" string (e.g. "ollama/gemma3:4b").',
            )
        if '/' not in m:
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f"ai.models[{i}] must use 'provider/model' format, got '{m}'",
                hint='Use "ollama/gemma3:4b" or "google-genai/gemini-3.0-flash-preview".',
            )

    temperature = raw.get('temperature', 0.2)
    if not isinstance(temperature, int | float):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'ai.temperature must be a number, got {type(temperature).__name__}',
            hint=f'Use a value between 0.0 and 1.0 in {context} [ai].',
        )
    if not 0.0 <= float(temperature) <= 1.0:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'ai.temperature must be between 0.0 and 1.0, got {temperature}',
            hint='Lower values (e.g. 0.2) produce more factual output.',
        )

    max_output_tokens = raw.get('max_output_tokens', 4096)
    if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'ai.max_output_tokens must be a positive integer, got {max_output_tokens!r}',
            hint=f'Use a value like 4096 in {context} [ai].',
        )

    codename_theme = raw.get('codename_theme', 'mountains')
    if not isinstance(codename_theme, str):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'ai.codename_theme must be a string, got {type(codename_theme).__name__}',
            hint=f'Use a theme like "mountains", "animals", "space", or any custom string in {context} [ai].',
        )

    blocklist_file = raw.get('blocklist_file', '')
    if not isinstance(blocklist_file, str):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'ai.blocklist_file must be a string, got {type(blocklist_file).__name__}',
            hint=f'Use a relative path like "custom_blocklist.txt" in {context} [ai].',
        )

    plugins = raw.get('plugins', [])
    if not isinstance(plugins, list):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'ai.plugins must be a list of strings, got {type(plugins).__name__}',
            hint=f'Use plugins = ["ollama", "google-genai"] in {context} [ai].',
        )
    for i, p in enumerate(plugins):
        if not isinstance(p, str):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f'ai.plugins[{i}] must be a string, got {type(p).__name__}: {p!r}',
                hint='Each plugin must be a provider name string (e.g. "ollama", "google-genai").',
            )

    # Parse [ai.features] sub-section.
    features = AiFeaturesConfig()
    raw_features = raw.get('features')
    if raw_features is not None:
        if not isinstance(raw_features, dict):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f'ai.features must be a table, got {type(raw_features).__name__}',
                hint=f'Use [ai.features] with boolean keys in {context}.',
            )
        for key in raw_features:
            if key not in VALID_AI_FEATURES_KEYS:
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_KEY,
                    message=f"Unknown key '{key}' in {context} [ai.features]",
                    hint=f'Valid ai.features keys: {sorted(VALID_AI_FEATURES_KEYS)}',
                )
        for key, value in raw_features.items():
            if not isinstance(value, bool):
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=f'ai.features.{key} must be a boolean, got {type(value).__name__}',
                    hint=f'Use {key} = true or {key} = false in {context} [ai.features].',
                )
        features = AiFeaturesConfig(**raw_features)

    return AiConfig(
        enabled=enabled,
        models=list(models),
        temperature=float(temperature),
        max_output_tokens=max_output_tokens,
        codename_theme=codename_theme,
        blocklist_file=blocklist_file,
        plugins=list(plugins),
        features=features,
    )


def _parse_schedule(
    raw: dict[str, Any],  # noqa: ANN401
    context: str = 'releasekit.toml',
) -> ScheduleConfig:
    """Parse and validate a ``[schedule]`` section."""
    for key in raw:
        if key not in VALID_SCHEDULE_KEYS:
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown key '{key}' in {context} [schedule]",
                hint=f'Valid schedule keys: {sorted(VALID_SCHEDULE_KEYS)}',
            )

    cadence = raw.get('cadence', 'on-push')
    if cadence not in ALLOWED_CADENCES:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"cadence must be one of {sorted(ALLOWED_CADENCES)}, got '{cadence}'",
            hint=f'Check the cadence value in {context} [schedule].',
        )

    min_bump = raw.get('min_bump', '')
    if min_bump and min_bump not in ALLOWED_MIN_BUMPS:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"min_bump must be one of {sorted(ALLOWED_MIN_BUMPS)}, got '{min_bump}'",
            hint=f'Check the min_bump value in {context} [schedule].',
        )

    cooldown = raw.get('cooldown_minutes', 0)
    if not isinstance(cooldown, int) or cooldown < 0:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'cooldown_minutes must be a non-negative integer, got {cooldown!r}',
            hint=f'Check cooldown_minutes in {context} [schedule].',
        )

    release_window = raw.get('release_window', '')
    if release_window and not re.match(r'^\d{2}:\d{2}-\d{2}:\d{2}$', release_window):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"release_window must be 'HH:MM-HH:MM' format, got '{release_window}'",
            hint=f'Use UTC time range like "14:00-16:00". Check {context} [schedule].',
        )

    return ScheduleConfig(
        cadence=cadence,
        release_window=release_window,
        cooldown_minutes=cooldown,
        min_bump=min_bump,
    )


def _parse_hooks(
    raw: dict[str, Any],  # noqa: ANN401
    context: str = 'releasekit.toml',
) -> HooksConfig:
    """Parse and validate a ``[hooks]`` section."""
    for key in raw:
        if key not in ALLOWED_HOOK_EVENTS:
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown hook event '{key}' in {context} [hooks]",
                hint=f'Valid hook events: {sorted(ALLOWED_HOOK_EVENTS)}',
            )

    kwargs: dict[str, list[str]] = {}
    for event in ALLOWED_HOOK_EVENTS:
        if event in raw:
            cmds = raw[event]
            if not isinstance(cmds, list):
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=f'hooks.{event} must be a list of strings, got {type(cmds).__name__}',
                    hint=f'Each hook event should be a list of shell commands in {context}.',
                )
            for cmd in cmds:
                if not isinstance(cmd, str):
                    raise ReleaseKitError(
                        code=E.CONFIG_INVALID_VALUE,
                        message=f'hooks.{event} items must be strings, got {type(cmd).__name__}',
                        hint=f'Each command in hooks.{event} must be a quoted string in {context}.',
                    )
            kwargs[event] = list(cmds)

    return HooksConfig(**kwargs)


def _parse_announcements(
    raw: dict[str, Any],  # noqa: ANN401
    context: str = 'releasekit.toml',
) -> AnnouncementConfig:
    """Parse and validate an ``[announcements]`` section."""
    for key in raw:
        if key not in VALID_ANNOUNCEMENT_KEYS:
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown key '{key}' in {context} [announcements]",
                hint=f'Valid announcement keys: {sorted(VALID_ANNOUNCEMENT_KEYS)}',
            )

    custom_webhooks = raw.get('custom_webhooks', [])
    if custom_webhooks and not isinstance(custom_webhooks, list):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'custom_webhooks must be a list of strings, got {type(custom_webhooks).__name__}',
            hint=f'Each webhook should be a URL string in {context} [announcements].',
        )

    # Parse per-group / per-package overrides.
    overrides: dict[str, AnnouncementConfig] = {}
    raw_overrides = raw.get('overrides', {})
    if raw_overrides:
        if not isinstance(raw_overrides, dict):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f'overrides must be a table of tables, got {type(raw_overrides).__name__}',
                hint=f'Each override key should be a group or package name in {context} [announcements.overrides].',
            )
        for override_key, override_raw in raw_overrides.items():
            if not isinstance(override_raw, dict):
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=f"Override '{override_key}' must be a table, got {type(override_raw).__name__}",
                    hint=f'Use [announcements.overrides.{override_key}] with webhook/template keys.',
                )
            # Validate keys inside the override (same keys minus 'overrides' to prevent nesting).
            for k in override_raw:
                if k not in VALID_ANNOUNCEMENT_KEYS or k == 'overrides':
                    raise ReleaseKitError(
                        code=E.CONFIG_INVALID_KEY,
                        message=f"Unknown key '{k}' in {context} [announcements.overrides.{override_key}]",
                        hint=f'Valid keys: {sorted(VALID_ANNOUNCEMENT_KEYS - {"overrides"})}',
                    )
            override_custom = override_raw.get('custom_webhooks', [])
            overrides[override_key] = AnnouncementConfig(
                slack_webhook=override_raw.get('slack_webhook', ''),
                discord_webhook=override_raw.get('discord_webhook', ''),
                teams_webhook=override_raw.get('teams_webhook', ''),
                irc_webhook=override_raw.get('irc_webhook', ''),
                twitter_bearer_token=override_raw.get('twitter_bearer_token', ''),
                linkedin_access_token=override_raw.get('linkedin_access_token', ''),
                linkedin_org_id=override_raw.get('linkedin_org_id', ''),
                custom_webhooks=list(override_custom) if override_custom else [],
                template=override_raw.get('template', ''),
                rollback_template=override_raw.get('rollback_template', ''),
                enabled=override_raw.get('enabled', True),
            )

    return AnnouncementConfig(
        slack_webhook=raw.get('slack_webhook', ''),
        discord_webhook=raw.get('discord_webhook', ''),
        teams_webhook=raw.get('teams_webhook', ''),
        irc_webhook=raw.get('irc_webhook', ''),
        twitter_bearer_token=raw.get('twitter_bearer_token', ''),
        linkedin_access_token=raw.get('linkedin_access_token', ''),
        linkedin_org_id=raw.get('linkedin_org_id', ''),
        custom_webhooks=list(custom_webhooks) if custom_webhooks else [],
        template=raw.get('template', '\U0001f680 Released ${version}: ${packages}'),
        rollback_template=raw.get('rollback_template', '\u26a0\ufe0f Rolled back ${version}: ${packages}'),
        enabled=raw.get('enabled', True),
        overrides=overrides,
    )


def _validate_prerelease_label(value: str, context: str = 'releasekit.toml') -> None:
    """Raise if prerelease_label is not a recognized value."""
    if value and value not in ALLOWED_PRERELEASE_LABELS:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"prerelease_label must be one of {sorted(ALLOWED_PRERELEASE_LABELS)}, got '{value}'",
            hint=f"Use 'alpha', 'beta', 'rc', or 'dev'. Check {context}.",
        )


def _parse_packages(
    raw: dict[str, Any],  # noqa: ANN401
    context: str = 'releasekit.toml',
) -> dict[str, PackageConfig]:
    """Parse and validate a ``[workspace.<label>.packages]`` section.

    Each key is a package name (or group name) mapping to a table of
    per-package overrides.
    """
    if not isinstance(raw, dict):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'packages must be a table of tables, got {type(raw).__name__}',
            hint=f'Use [workspace.<label>.packages."pkg-name"] in {context}.',
        )

    result: dict[str, PackageConfig] = {}
    for pkg_name, pkg_raw in raw.items():
        pkg_context = f'{context} [packages.{pkg_name}]'
        if not isinstance(pkg_raw, dict):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f"Package '{pkg_name}' must be a table, got {type(pkg_raw).__name__}",
                hint=f'Use [{pkg_context}] with per-package override keys.',
            )
        for k in pkg_raw:
            if k not in VALID_PACKAGE_KEYS:
                suggestion = difflib.get_close_matches(k, VALID_PACKAGE_KEYS, n=1, cutoff=0.6)
                hint = f"Did you mean '{suggestion[0]}'?" if suggestion else f'Valid keys: {sorted(VALID_PACKAGE_KEYS)}'
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_KEY,
                    message=f"Unknown key '{k}' in {pkg_context}",
                    hint=hint,
                )
        if 'versioning_scheme' in pkg_raw:
            _validate_versioning_scheme(pkg_raw['versioning_scheme'], pkg_context)
        if 'prerelease_label' in pkg_raw:
            _validate_prerelease_label(pkg_raw['prerelease_label'], pkg_context)

        extra_files = pkg_raw.get('extra_files', [])
        if extra_files and not isinstance(extra_files, list):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f'extra_files must be a list of strings in {pkg_context}',
                hint='Use extra_files = ["path/to/file"].',
            )

        result[pkg_name] = PackageConfig(
            versioning_scheme=pkg_raw.get('versioning_scheme', ''),
            calver_format=pkg_raw.get('calver_format', ''),
            prerelease_label=pkg_raw.get('prerelease_label', ''),
            changelog=pkg_raw.get('changelog'),
            changelog_template=pkg_raw.get('changelog_template', ''),
            smoke_test=pkg_raw.get('smoke_test'),
            major_on_zero=pkg_raw.get('major_on_zero'),
            extra_files=list(extra_files) if extra_files else [],
            dist_tag=pkg_raw.get('dist_tag', ''),
            registry_url=pkg_raw.get('registry_url', ''),
            provenance=pkg_raw.get('provenance'),
        )

    return result


def _parse_workspace_section(
    label: str,
    raw: dict[str, Any],  # noqa: ANN401
) -> WorkspaceConfig:
    """Parse and validate a single ``[workspace.<label>]`` section."""
    context = f'[workspace.{label}]'

    _validate_workspace_label(label)

    for key in raw:
        if key not in VALID_WORKSPACE_KEYS:
            suggestion = difflib.get_close_matches(key, VALID_WORKSPACE_KEYS, n=1, cutoff=0.6)
            hint = f"Did you mean '{suggestion[0]}'?" if suggestion else f'Check valid keys for {context}.'
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown key '{key}' in {context}",
                hint=hint,
            )

    for key, value in raw.items():
        _validate_value_type(key, value, _WORKSPACE_TYPE_MAP, context=context)

    # Validate ecosystem.
    ecosystem = raw.get('ecosystem', '')
    if ecosystem and ecosystem not in ALLOWED_ECOSYSTEMS:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"ecosystem must be one of {sorted(ALLOWED_ECOSYSTEMS)}, got '{ecosystem}'",
            hint=f'Check the ecosystem value in {context}.',
        )

    if 'prerelease_mode' in raw:
        _validate_prerelease_mode(raw['prerelease_mode'])
    if 'prerelease_label' in raw:
        _validate_prerelease_label(raw['prerelease_label'], context)
    for list_key in ('exclude', 'exclude_publish', 'exclude_bump'):
        if list_key in raw:
            _validate_string_list(list_key, raw[list_key], context)

    if 'release_mode' in raw:
        _validate_release_mode(raw['release_mode'], context)
    if 'versioning_scheme' in raw:
        _validate_versioning_scheme(raw['versioning_scheme'], context)

    kwargs: dict[str, Any] = dict(raw)  # noqa: ANN401
    if 'groups' in kwargs:
        kwargs['groups'] = _validate_groups(kwargs['groups'])

    # Parse nested sections into dataclass instances.
    if 'schedule' in kwargs:
        kwargs['schedule'] = _parse_schedule(dict(kwargs['schedule']), context)
    if 'hooks' in kwargs:
        kwargs['hooks'] = _parse_hooks(dict(kwargs['hooks']), context)
    if 'branches' in kwargs:
        kwargs['branches'] = dict(kwargs['branches'])
    if 'ai' in kwargs:
        kwargs['ai'] = _parse_ai(dict(kwargs['ai']), context)
    if 'announcements' in kwargs:
        kwargs['announcements'] = _parse_announcements(dict(kwargs['announcements']), context)
    if 'packages' in kwargs:
        kwargs['packages'] = _parse_packages(dict(kwargs['packages']), context)

    # Default tool from ecosystem if not explicitly set.
    if not kwargs.get('tool') and ecosystem:
        kwargs['tool'] = DEFAULT_TOOLS.get(ecosystem, '')

    # Default versioning scheme from ecosystem if not explicitly set.
    if not kwargs.get('versioning_scheme') and ecosystem:
        default_scheme = DEFAULT_VERSIONING_SCHEMES.get(ecosystem, '')
        if default_scheme:
            kwargs['versioning_scheme'] = default_scheme

    return WorkspaceConfig(label=label, **kwargs)


def load_config(workspace_root: Path) -> ReleaseConfig:
    """Load and validate configuration from ``releasekit.toml``.

    Global settings are top-level keys. Per-workspace settings live
    under ``[workspace.<label>]`` sections where ``<label>`` is a
    user-chosen name (e.g. ``[workspace.py]``, ``[workspace.js]``).

    Args:
        workspace_root: Directory containing ``releasekit.toml``.

    Returns:
        A validated :class:`ReleaseConfig`.

    Raises:
        ReleaseKitError: If the file contains invalid config.
    """
    config_path = workspace_root / CONFIG_FILENAME

    if not config_path.is_file():
        logger.debug('no_releasekit_config', path=str(config_path))
        return ReleaseConfig(config_path=None)

    try:
        text = config_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message=f'Failed to read {config_path}: {exc}',
            hint=f'Check that {config_path} exists and is readable.',
        ) from exc

    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message=f'Failed to parse {config_path}: {exc}',
            hint=f'Check that {config_path} contains valid TOML.',
        ) from exc

    raw: dict[str, Any] = dict(doc)  # noqa: ANN401

    if not raw:
        logger.debug('empty_releasekit_config', path=str(config_path))
        return ReleaseConfig(config_path=config_path)

    # Separate workspace sections from global keys.
    workspace_raw: dict[str, Any] = {}  # noqa: ANN401
    if 'workspace' in raw:
        workspace_raw = dict(raw.pop('workspace'))

    # Validate global keys.
    for key in raw:
        if key not in VALID_KEYS:
            all_keys = VALID_KEYS | VALID_WORKSPACE_KEYS
            suggestion = difflib.get_close_matches(key, all_keys, n=1, cutoff=0.6)
            if suggestion and suggestion[0] in VALID_WORKSPACE_KEYS:
                hint = f"'{suggestion[0]}' is a workspace key. Move it under [workspace.<label>]."
            elif suggestion:
                hint = f"Did you mean '{suggestion[0]}'?"
            else:
                hint = 'Check the releasekit docs for valid keys.'
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown key '{key}' in releasekit.toml",
                hint=hint,
            )

    for key, value in raw.items():
        _validate_value_type(key, value, _GLOBAL_TYPE_MAP)

    if 'forge' in raw:
        _validate_forge(raw['forge'])
    if 'publish_from' in raw:
        _validate_publish_from(raw['publish_from'])
    if 'release_mode' in raw:
        _validate_release_mode(raw['release_mode'])
    if 'versioning_scheme' in raw:
        _validate_versioning_scheme(raw['versioning_scheme'])

    # Parse [workspace.*] sections.
    workspaces: dict[str, WorkspaceConfig] = {}
    for ws_label, section in workspace_raw.items():
        if not isinstance(section, dict):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f'[workspace.{ws_label}] must be a table, got {type(section).__name__}',
                hint=f'Define [workspace.{ws_label}] as a TOML table with key-value pairs.',
            )
        workspaces[ws_label] = _parse_workspace_section(ws_label, dict(section))

    # Cross-workspace validation.
    _validate_workspace_overlap(workspaces)

    global_kwargs: dict[str, Any] = dict(raw)  # noqa: ANN401

    # Parse global nested sections into dataclass instances.
    if 'schedule' in global_kwargs:
        global_kwargs['schedule'] = _parse_schedule(dict(global_kwargs['schedule']))
    if 'hooks' in global_kwargs:
        global_kwargs['hooks'] = _parse_hooks(dict(global_kwargs['hooks']))
    if 'branches' in global_kwargs:
        global_kwargs['branches'] = dict(global_kwargs['branches'])
    if 'ai' in global_kwargs:
        global_kwargs['ai'] = _parse_ai(dict(global_kwargs['ai']))
    if 'announcements' in global_kwargs:
        global_kwargs['announcements'] = _parse_announcements(dict(global_kwargs['announcements']))

    return ReleaseConfig(**global_kwargs, workspaces=workspaces, config_path=config_path)


def _validate_workspace_overlap(workspaces: dict[str, WorkspaceConfig]) -> None:
    """Validate that workspace configurations do not conflict.

    Checks performed:

    1. **Overlapping roots** — Two workspaces whose ``root`` directories
       overlap (one is a prefix of the other) would discover the same
       packages, leading to duplicate version bumps, conflicting tags,
       and double publishes.

    2. **Conflicting tag formats** — Two workspaces with the same
       ``tag_format`` could produce colliding git tags for packages
       that happen to share a name across workspaces.

    Args:
        workspaces: Parsed workspace configs keyed by label.

    Raises:
        ReleaseKitError: If any overlap or conflict is detected.
    """
    if len(workspaces) < 2:
        return

    ws_list = list(workspaces.values())

    # Check 1: Overlapping roots.
    for i, ws_a in enumerate(ws_list):
        for ws_b in ws_list[i + 1 :]:
            root_a = Path(ws_a.root).resolve()
            root_b = Path(ws_b.root).resolve()
            if root_a == root_b:
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=(
                        f"Workspaces '{ws_a.label}' and '{ws_b.label}' "
                        f"share the same root '{ws_a.root}'. "
                        f'Each workspace must have a distinct root directory.'
                    ),
                    hint='Use different root directories so each package is discovered by exactly one workspace.',
                )
            # Check if one root is a parent of the other.
            try:
                root_b.relative_to(root_a)
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=(
                        f"Workspace '{ws_b.label}' root '{ws_b.root}' "
                        f"is inside workspace '{ws_a.label}' root '{ws_a.root}'. "
                        f'Overlapping roots cause packages to be discovered by both workspaces.'
                    ),
                    hint='Ensure workspace roots do not overlap. Use exclude patterns if needed.',
                )
            except ValueError:
                pass
            try:
                root_a.relative_to(root_b)
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=(
                        f"Workspace '{ws_a.label}' root '{ws_a.root}' "
                        f"is inside workspace '{ws_b.label}' root '{ws_b.root}'. "
                        f'Overlapping roots cause packages to be discovered by both workspaces.'
                    ),
                    hint='Ensure workspace roots do not overlap. Use exclude patterns if needed.',
                )
            except ValueError:
                pass

    # Check 2: Conflicting tag formats.
    tag_formats: dict[str, str] = {}  # tag_format → first label
    for ws in ws_list:
        if ws.tag_format in tag_formats:
            other = tag_formats[ws.tag_format]
            logger.warning(
                'conflicting_tag_formats',
                workspace_a=other,
                workspace_b=ws.label,
                tag_format=ws.tag_format,
                hint=(
                    'Two workspaces with the same tag_format may produce '
                    'colliding tags if packages share names across workspaces.'
                ),
            )
        else:
            tag_formats[ws.tag_format] = ws.label


# Prefix for group references in exclude lists.
_GROUP_PREFIX = 'group:'


def resolve_group_refs(
    patterns: list[str],
    groups: dict[str, list[str]],
) -> list[str]:
    """Expand ``group:<name>`` references into flat package-name patterns.

    Entries without the ``group:`` prefix are passed through unchanged.
    Group references are replaced with the package patterns from the
    named group. Groups can reference other groups recursively using
    the same ``group:<name>`` syntax — cycles are detected and raise
    an error.

    Args:
        patterns: List of glob patterns or ``group:<name>`` references.
        groups: The ``[groups]`` mapping from :class:`ReleaseConfig`.

    Returns:
        A flat list of glob patterns with all group refs expanded.

    Raises:
        ReleaseKitError: If a ``group:<name>`` reference points to an
            unknown group, or if a cycle is detected.

    Example::

        resolve_group_refs(
            ['group:all_plugins'],
            {
                'google': ['genkit-plugin-firebase'],
                'community': ['genkit-plugin-ollama'],
                'all_plugins': ['group:google', 'group:community'],
            },
        )
        # => ["genkit-plugin-firebase", "genkit-plugin-ollama"]
    """
    result: list[str] = []
    for pat in patterns:
        if pat.startswith(_GROUP_PREFIX):
            group_name = pat[len(_GROUP_PREFIX) :]
            result.extend(_resolve_group(group_name, groups, visiting=set()))
        else:
            result.append(pat)
    return result


def _resolve_group(
    name: str,
    groups: dict[str, list[str]],
    visiting: set[str],
) -> list[str]:
    """Recursively expand a single group, detecting cycles.

    Args:
        name: Group name to resolve.
        groups: All group definitions.
        visiting: Set of group names currently being resolved (for
            cycle detection).

    Returns:
        Flat list of package-name patterns.
    """
    if name not in groups:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"Unknown group '{name}' referenced as 'group:{name}'",
            hint=f'Available groups: {sorted(groups)}',
        )
    if name in visiting:
        cycle = ' → '.join([*visiting, name])
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'Cycle detected in group references: {cycle}',
            hint='Remove the circular group reference.',
        )

    visiting = visiting | {name}
    result: list[str] = []
    for pat in groups[name]:
        if pat.startswith(_GROUP_PREFIX):
            nested_name = pat[len(_GROUP_PREFIX) :]
            result.extend(_resolve_group(nested_name, groups, visiting))
        else:
            result.append(pat)
    return result


__all__ = [
    'ALLOWED_CADENCES',
    'ALLOWED_ECOSYSTEMS',
    'ALLOWED_FORGES',
    'ALLOWED_HOOK_EVENTS',
    'ALLOWED_MIN_BUMPS',
    'ALLOWED_PRERELEASE_LABELS',
    'ALLOWED_PRERELEASE_MODES',
    'ALLOWED_PUBLISH_FROM',
    'ALLOWED_RELEASE_MODES',
    'ALLOWED_VERSIONING_SCHEMES',
    'CONFIG_FILENAME',
    'DEFAULT_VERSIONING_SCHEMES',
    'DEFAULT_TOOLS',
    'VALID_ANNOUNCEMENT_KEYS',
    'VALID_KEYS',
    'VALID_PACKAGE_KEYS',
    'VALID_SCHEDULE_KEYS',
    'VALID_WORKSPACE_KEYS',
    'AnnouncementConfig',
    'HooksConfig',
    'PackageConfig',
    'ReleaseConfig',
    'ScheduleConfig',
    'WorkspaceConfig',
    'build_package_configs',
    'build_skip_map',
    'load_config',
    'resolve_group_refs',
    'resolve_package_config',
    'resolve_workspace_ai_config',
]
