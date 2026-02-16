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

"""Protocol-based backend shim layer for releasekit.

All external tool calls (uv, git, gh, PyPI API) go through injectable
Protocol interfaces defined here. This makes the tool testable and
extensible — swap in a mock backend for tests, or a different VCS
backend for a non-git workflow.

Protocols (defined in subpackage ``__init__.py`` files):

- :class:`PackageManager` — build, publish, lock (default: :class:`UvBackend`)
- :class:`VCS` — commit, tag, push, log (default: :class:`GitCLIBackend`)
- :class:`Forge` — GitHub releases, PRs (default: :class:`GitHubCLIBackend`)
- :class:`Registry` — PyPI queries (default: :class:`PyPIBackend`)
- :class:`Workspace` — discover, classify deps, rewrite versions (default: :class:`UvWorkspace`)
- :class:`Validator` — extensible validation (OIDC, schema, provenance digest)
"""

from releasekit.backends._run import CommandResult, run_command
from releasekit.backends.forge import Forge, GitHubAPIBackend, GitHubCLIBackend
from releasekit.backends.pm import PackageManager, UvBackend
from releasekit.backends.registry import ChecksumResult, PyPIBackend, Registry
from releasekit.backends.validation import ValidationResult, Validator
from releasekit.backends.vcs import VCS, GitCLIBackend
from releasekit.backends.workspace import Package, UvWorkspace, Workspace

__all__ = [
    'ChecksumResult',
    'CommandResult',
    'Forge',
    'GitCLIBackend',
    'GitHubAPIBackend',
    'GitHubCLIBackend',
    'Package',
    'PackageManager',
    'PyPIBackend',
    'Registry',
    'UvBackend',
    'UvWorkspace',
    'VCS',
    'ValidationResult',
    'Validator',
    'Workspace',
    'run_command',
]
