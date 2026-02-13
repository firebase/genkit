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

"""Conventional Commits parser.

Pure implementation — depends only on ``re`` and :mod:`._types`.
No I/O, no logging, no side effects.
"""

from __future__ import annotations

import re

from releasekit.commit_parsing._types import BumpType, ParsedCommit

# Conventional Commit types that trigger each bump level.
MAJOR_TYPES: frozenset[str] = frozenset()  # Major is only via "!" or "BREAKING CHANGE"
MINOR_TYPES: frozenset[str] = frozenset({'feat'})
PATCH_TYPES: frozenset[str] = frozenset({'fix', 'perf'})

# Regex for Conventional Commits: type(scope)!: description
CC_PATTERN: re.Pattern[str] = re.compile(
    r'^(?P<type>[a-z]+)'  # type (e.g. feat, fix, chore)
    r'(?:\((?P<scope>[^)]*)\))?'  # optional scope in parens
    r'(?P<breaking>!)?'  # optional breaking change indicator
    r':\s*'  # colon + space
    r'(?P<description>.+)$',  # description
)

# GitHub's default revert format: Revert "feat: add X"
REVERT_PATTERN: re.Pattern[str] = re.compile(
    r'^[Rr]evert\s+"(?P<inner>.+)"',
)


class ConventionalCommitParser:
    """Parser for `Conventional Commits <https://www.conventionalcommits.org/>`_.

    Parses messages in the format ``type(scope)!: description``.
    Handles revert commits in two formats:

    - GitHub default: ``Revert "feat: add X"``
    - Conventional: ``revert: feat: add X``
    """

    def parse(self, message: str, sha: str = '') -> ParsedCommit | None:
        """Parse a commit message as a Conventional Commit.

        Args:
            message: The commit subject line.
            sha: The commit SHA (for reference).

        Returns:
            A :class:`ParsedCommit` if the message follows the
            convention, otherwise ``None``.
        """
        stripped = message.strip()

        # Check for revert: parse the inner message to determine what's reverted.
        revert_match = REVERT_PATTERN.match(stripped)
        if revert_match:
            inner = revert_match.group('inner')
            inner_cc = self.parse(inner, sha=sha)
            reverted_bump = inner_cc.bump if inner_cc else BumpType.NONE
            return ParsedCommit(
                sha=sha,
                type='revert',
                scope=inner_cc.scope if inner_cc else '',
                description=inner,
                breaking=False,
                bump=BumpType.NONE,
                raw=message,
                is_revert=True,
                reverted_bump=reverted_bump,
            )

        match = CC_PATTERN.match(stripped)
        if not match:
            return None

        cc_type = match.group('type')
        scope = match.group('scope') or ''
        breaking = bool(match.group('breaking'))
        description = match.group('description')

        # Check for "BREAKING CHANGE:" in the body (simplified: check subject).
        if 'BREAKING CHANGE' in message or 'BREAKING-CHANGE' in message:
            breaking = True

        # Handle "revert: feat: add X" conventional format.
        if cc_type == 'revert':
            inner_cc = self.parse(description, sha=sha)
            reverted_bump = inner_cc.bump if inner_cc else BumpType.NONE
            return ParsedCommit(
                sha=sha,
                type='revert',
                scope=inner_cc.scope if inner_cc else scope,
                description=description,
                breaking=False,
                bump=BumpType.NONE,
                raw=message,
                is_revert=True,
                reverted_bump=reverted_bump,
            )

        # Determine bump type.
        if breaking:
            bump = BumpType.MAJOR
        elif cc_type in MINOR_TYPES:
            bump = BumpType.MINOR
        elif cc_type in PATCH_TYPES:
            bump = BumpType.PATCH
        else:
            bump = BumpType.NONE

        return ParsedCommit(
            sha=sha,
            type=cc_type,
            scope=scope,
            description=description,
            breaking=breaking,
            bump=bump,
            raw=message,
        )
