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

"""Angular commit convention parser.

Implements the `Angular commit message format
<https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit>`_.

Angular uses the same ``type(scope): description`` syntax as
Conventional Commits but restricts ``type`` to a fixed allowlist:

.. list-table::
   :header-rows: 1

   * - Type
     - Purpose
     - Bump
   * - ``feat``
     - New feature
     - MINOR
   * - ``fix``
     - Bug fix
     - PATCH
   * - ``perf``
     - Performance improvement
     - PATCH
   * - ``build``
     - Build system / dependencies
     - NONE
   * - ``ci``
     - CI configuration
     - NONE
   * - ``docs``
     - Documentation only
     - NONE
   * - ``refactor``
     - Code refactoring (no feature/fix)
     - NONE
   * - ``style``
     - Formatting, whitespace
     - NONE
   * - ``test``
     - Adding/fixing tests
     - NONE

Breaking changes are indicated by ``!`` after the type/scope or by a
``BREAKING CHANGE:`` / ``BREAKING-CHANGE:`` footer — identical to
Conventional Commits.

Commits whose type is not in the allowlist are rejected (return ``None``).

Supports full multi-line messages with body and footer parsing,
reusing the footer infrastructure from :mod:`._conventional`.

Pure implementation — depends only on ``re`` and sibling modules.
No I/O, no logging, no side effects.
"""

from __future__ import annotations

import re

from releasekit.commit_parsing._conventional import (
    REVERT_PATTERN,
    _has_breaking_footer,
    _parse_body_and_footers,
)
from releasekit.commit_parsing._types import BumpType, ParsedCommit

# Angular's fixed set of allowed commit types.
# https://github.com/angular/angular/blob/main/CONTRIBUTING.md#type
ANGULAR_TYPES: frozenset[str] = frozenset({
    'build',
    'ci',
    'docs',
    'feat',
    'fix',
    'perf',
    'refactor',
    'style',
    'test',
})

# Bump mappings (same as Conventional Commits).
ANGULAR_MINOR_TYPES: frozenset[str] = frozenset({'feat'})
ANGULAR_PATCH_TYPES: frozenset[str] = frozenset({'fix', 'perf'})

# Subject line regex — identical to CC but we validate allowed types after.
_ANGULAR_PATTERN: re.Pattern[str] = re.compile(
    r'^(?P<type>[a-zA-Z]+)'  # type (case-insensitive, normalised later)
    r'(?:\((?P<scope>[^)]*)\))?'  # optional scope in parens
    r'(?P<breaking>!)?'  # optional breaking change indicator
    r':\s*'  # colon + space
    r'(?P<description>.+)$',  # description
)


class AngularCommitParser:
    """Parser for `Angular commit conventions <https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit>`_.

    Parses messages in the format ``type(scope): description`` where
    ``type`` must be one of the Angular-defined types.

    Unlike :class:`ConventionalCommitParser`, this parser **rejects**
    commits with unrecognized types (e.g. ``chore``, ``release``).
    If you want to accept any type, use :class:`ConventionalCommitParser`
    instead.

    Supports full multi-line messages with body and footer parsing.

    Handles revert commits in two formats:

    - GitHub default: ``Revert "feat: add X"``
    - Angular/CC: ``revert: feat: add X``

    Example::

        parser = AngularCommitParser()
        cc = parser.parse('feat(auth): add OAuth2 support')
        assert cc.type == 'feat'
        assert cc.scope == 'auth'
        assert cc.bump == BumpType.MINOR

        # Unknown types are rejected:
        assert parser.parse('chore: update deps') is None

        # Custom type allowlist:
        parser = AngularCommitParser(
            allowed_types=frozenset({*ANGULAR_TYPES, 'chore'}),
        )
        cc = parser.parse('chore: update deps')
        assert cc is not None
    """

    def __init__(
        self,
        *,
        allowed_types: frozenset[str] | None = None,
    ) -> None:
        """Initialize the parser.

        Args:
            allowed_types: Override the default Angular type allowlist.
                Useful for teams that want Angular conventions but with
                additional custom types (e.g. ``frozenset({*ANGULAR_TYPES, 'chore'})``).
        """
        self._allowed_types = allowed_types or ANGULAR_TYPES

    def parse(self, message: str, sha: str = '') -> ParsedCommit | None:
        """Parse a commit message using Angular conventions.

        Args:
            message: The commit message (subject line, or full message
                with body and footers separated by blank lines).
            sha: The commit SHA (for reference).

        Returns:
            A :class:`ParsedCommit` if the message follows Angular
            conventions and uses an allowed type, otherwise ``None``.
        """
        all_lines = message.split('\n')
        subject = all_lines[0].strip()

        # Check for revert: parse the inner message to determine what's reverted.
        revert_match = REVERT_PATTERN.match(subject)
        if revert_match:
            inner = revert_match.group('inner')
            inner_parsed = self.parse(inner, sha=sha)
            reverted_bump = inner_parsed.bump if inner_parsed else BumpType.NONE
            return ParsedCommit(
                sha=sha,
                type='revert',
                scope=inner_parsed.scope if inner_parsed else '',
                description=inner,
                breaking=False,
                bump=BumpType.NONE,
                raw=message,
                is_revert=True,
                reverted_bump=reverted_bump,
            )

        match = _ANGULAR_PATTERN.match(subject)
        if not match:
            return None

        # Normalise type to lowercase.
        commit_type = match.group('type').lower()

        # Angular is strict: reject unrecognized types.
        if commit_type not in self._allowed_types:
            return None

        scope = match.group('scope') or ''
        breaking = bool(match.group('breaking'))
        description = match.group('description')

        # Parse body and footers from remaining lines.
        remaining_lines: list[str] = []
        if len(all_lines) > 1:
            body_start = 1
            while body_start < len(all_lines) and all_lines[body_start].strip() == '':
                body_start += 1
            remaining_lines = all_lines[body_start:]

        body, footers = _parse_body_and_footers(remaining_lines)

        # Check for BREAKING CHANGE in footers.
        footer_breaking, breaking_desc = _has_breaking_footer(footers)
        if footer_breaking:
            breaking = True

        breaking_description = breaking_desc
        if breaking and not breaking_description:
            breaking_description = description

        # Handle "revert: feat: add X" format.
        if commit_type == 'revert':
            inner_parsed = self.parse(description, sha=sha)
            reverted_bump = inner_parsed.bump if inner_parsed else BumpType.NONE
            return ParsedCommit(
                sha=sha,
                type='revert',
                scope=inner_parsed.scope if inner_parsed else scope,
                description=description,
                body=body,
                footers=footers,
                breaking=False,
                bump=BumpType.NONE,
                raw=message,
                is_revert=True,
                reverted_bump=reverted_bump,
            )

        # Determine bump type.
        if breaking:
            bump = BumpType.MAJOR
        elif commit_type in ANGULAR_MINOR_TYPES:
            bump = BumpType.MINOR
        elif commit_type in ANGULAR_PATCH_TYPES:
            bump = BumpType.PATCH
        else:
            bump = BumpType.NONE

        return ParsedCommit(
            sha=sha,
            type=commit_type,
            scope=scope,
            description=description,
            body=body,
            footers=footers,
            breaking=breaking,
            breaking_description=breaking_description,
            bump=bump,
            raw=message,
        )
