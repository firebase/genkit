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
extensible -- swap in a mock backend for tests, or a different VCS
backend for a non-git workflow.

Protocols:

- :class:`PackageManager` -- build, publish, lock (default: :class:`UvBackend`)
- :class:`VCS` -- commit, tag, push, log (default: :class:`GitBackend`)
- :class:`Forge` -- GitHub releases, PRs (default: :class:`GitHubBackend`)
- :class:`Registry` -- PyPI queries (default: :class:`PyPIBackend`)
"""

from releasekit.backends._run import CommandResult, run_command
from releasekit.backends.forge import Forge, GitHubBackend
from releasekit.backends.pm import PackageManager, UvBackend
from releasekit.backends.registry import PyPIBackend, Registry
from releasekit.backends.vcs import VCS, GitBackend

__all__ = [
    'CommandResult',
    'Forge',
    'GitBackend',
    'GitHubBackend',
    'PackageManager',
    'PyPIBackend',
    'Registry',
    'UvBackend',
    'VCS',
    'run_command',
]
