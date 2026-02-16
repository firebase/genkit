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

r"""Commit message parsing framework.

This subpackage provides a protocol-based commit parsing system.
The :class:`CommitParser` protocol allows teams to plug in their own
commit message format while keeping the same version-bump and
changelog machinery.

Built-in parsers:

- :class:`ConventionalCommitParser` — ``type(scope)!: description``
  (accepts any type)
- :class:`AngularCommitParser` — same syntax but restricted to Angular's
  type allowlist (``build``, ``ci``, ``docs``, ``feat``, ``fix``,
  ``perf``, ``refactor``, ``style``, ``test``)

Usage::

    from releasekit.commit_parsing import (
        ConventionalCommitParser,
        AngularCommitParser,
        ParsedCommit,
        parse_conventional_commit,
    )

    # Using the convenience function (default parser):
    cc = parse_conventional_commit('feat(auth): add OAuth2')
    assert cc.type == 'feat'
    assert cc.bump == BumpType.MINOR

    # Using the Angular parser:
    parser = AngularCommitParser()
    cc = parser.parse('refactor(core): simplify logic')
    assert cc.type == 'refactor'
    assert cc.bump == BumpType.NONE

    # Angular rejects unknown types:
    assert parser.parse('chore: update deps') is None

    # Full multi-line message with footer:
    msg = 'feat: new API\\n\\nBREAKING CHANGE: removed v1 endpoints'
    cc = parse_conventional_commit(msg)
    assert cc.breaking is True
    assert cc.breaking_description == 'removed v1 endpoints'
"""

from releasekit.commit_parsing._angular import (
    ANGULAR_MINOR_TYPES,
    ANGULAR_PATCH_TYPES,
    ANGULAR_TYPES,
    AngularCommitParser,
)
from releasekit.commit_parsing._conventional import ConventionalCommitParser
from releasekit.commit_parsing._types import (
    BUMP_PRECEDENCE,
    BumpType,
    CommitParser,
    ConventionalCommit,
    ParsedCommit,
    max_bump,
)

# Module-level singleton for convenience.
_DEFAULT_PARSER = ConventionalCommitParser()


def parse_conventional_commit(message: str, sha: str = '') -> ParsedCommit | None:
    """Parse a single commit message as a Conventional Commit.

    Convenience wrapper around :meth:`ConventionalCommitParser.parse`.

    Args:
        message: The commit message (subject line, or full multi-line
            message with body and footers).
        sha: The commit SHA (for reference).

    Returns:
        A :class:`ParsedCommit` if the message follows the
        convention, otherwise ``None``.
    """
    return _DEFAULT_PARSER.parse(message, sha=sha)


__all__ = [
    'ANGULAR_MINOR_TYPES',
    'ANGULAR_PATCH_TYPES',
    'ANGULAR_TYPES',
    'AngularCommitParser',
    'BUMP_PRECEDENCE',
    'BumpType',
    'CommitParser',
    'ConventionalCommit',
    'ConventionalCommitParser',
    'ParsedCommit',
    'max_bump',
    'parse_conventional_commit',
]
