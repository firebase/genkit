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

"""Commit message parsing framework.

This subpackage provides a protocol-based commit parsing system.
The :class:`CommitParser` protocol allows teams to plug in their own
commit message format while keeping the same version-bump and
changelog machinery.

Built-in parsers:

- :class:`ConventionalCommitParser` — ``type(scope)!: description``

Usage::

    from releasekit.commit_parsing import (
        ConventionalCommitParser,
        ParsedCommit,
        parse_conventional_commit,
    )

    # Using the convenience function (default parser):
    cc = parse_conventional_commit('feat(auth): add OAuth2')
    assert cc.type == 'feat'
    assert cc.bump == BumpType.MINOR

    # Using a parser instance (for DI):
    parser = ConventionalCommitParser()
    cc = parser.parse('fix: null pointer')
"""

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
        message: The commit subject line.
        sha: The commit SHA (for reference).

    Returns:
        A :class:`ParsedCommit` if the message follows the
        convention, otherwise ``None``.
    """
    return _DEFAULT_PARSER.parse(message, sha=sha)


__all__ = [
    'BUMP_PRECEDENCE',
    'BumpType',
    'CommitParser',
    'ConventionalCommit',
    'ConventionalCommitParser',
    'ParsedCommit',
    'max_bump',
    'parse_conventional_commit',
]
