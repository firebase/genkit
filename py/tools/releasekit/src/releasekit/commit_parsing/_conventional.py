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

r"""Conventional Commits v1.0.0 parser.

Implements the full `Conventional Commits v1.0.0
<https://www.conventionalcommits.org/en/v1.0.0/>`_ specification:

**Subject line** (required)::

    type(scope)!: description

**Body** (optional): free-form text separated from the subject by one
blank line.

**Footers** (optional): git trailers separated from the body by one
blank line.  Each footer is ``token: value`` or ``token #value``.
The token ``BREAKING CHANGE`` (with space) is a special case permitted
by the spec.

Spec compliance notes:

- **Rule 1**: Type is a noun (``feat``, ``fix``, etc.) followed by
  optional scope, optional ``!``, and required ``: ``.
- **Rule 4**: Scope is a noun in parentheses.
- **Rule 8**: Footers follow the git trailer convention
  (``token: value`` or ``token #value``).
- **Rule 9**: Footer tokens use ``-`` in place of whitespace, except
  ``BREAKING CHANGE`` which may use a space.
- **Rule 11–13**: Breaking changes via ``!`` or ``BREAKING CHANGE:``
  footer.
- **Rule 15**: Types are case-insensitive; ``BREAKING CHANGE`` must be
  uppercase.
- **Rule 16**: ``BREAKING-CHANGE`` is synonymous with
  ``BREAKING CHANGE`` as a footer token.

Pure implementation — depends only on ``re`` and :mod:`._types`.
No I/O, no logging, no side effects.
"""

from __future__ import annotations

import re

from releasekit.commit_parsing._types import BumpType, ParsedCommit

# Major is only via "!" or "BREAKING CHANGE" footer.
MAJOR_TYPES: frozenset[str] = frozenset()
MINOR_TYPES: frozenset[str] = frozenset({'feat'})
PATCH_TYPES: frozenset[str] = frozenset({'fix', 'perf'})

# Subject line: type(scope)!: description
# Per spec rule 15, types are case-insensitive — we match lowercase and
# normalise later.
CC_PATTERN: re.Pattern[str] = re.compile(
    r'^(?P<type>[a-zA-Z]+)'  # type (e.g. feat, fix, chore)
    r'(?:\((?P<scope>[^)]*)\))?'  # optional scope in parens
    r'(?P<breaking>!)?'  # optional breaking change indicator
    r':\s*'  # colon + space
    r'(?P<description>.+)$',  # description
)

# Git trailer: "token: value" or "token #value"
# Per spec rule 9, tokens use "-" instead of spaces, except
# "BREAKING CHANGE" which is special-cased.
_FOOTER_PATTERN: re.Pattern[str] = re.compile(
    r'^(?P<token>[A-Za-z][\w -]*[\w]|BREAKING[- ]CHANGE)'  # token
    r'(?:'
    r':\s*'  # ": " separator
    r'|'
    r'\s+#'  # " #" separator
    r')'
    r'(?P<value>.*)$',  # value
)

# GitHub's default revert format: Revert "feat: add X"
REVERT_PATTERN: re.Pattern[str] = re.compile(
    r'^[Rr]evert\s+"(?P<inner>.+)"',
)


def _parse_body_and_footers(
    lines: list[str],
) -> tuple[str, tuple[tuple[str, str], ...]]:
    """Split the post-subject portion into body and footers.

    Per the spec, footers are the trailing block of lines that each
    start with a valid git trailer token.  The body is everything
    between the subject and the footer block.

    Args:
        lines: Lines after the first blank line following the subject.

    Returns:
        ``(body, footers)`` where ``footers`` is a tuple of
        ``(token, value)`` pairs.
    """
    if not lines:
        return '', ()

    # Find where the footer block starts by scanning backwards.
    # Footers are a contiguous block of trailer lines at the end,
    # possibly with continuation lines (value spans multiple lines
    # until the next token is found).
    footer_start = len(lines)
    footers: list[tuple[str, str]] = []

    # Parse from the end: find the last contiguous block of footer lines.
    i = len(lines) - 1
    while i >= 0:
        line = lines[i]
        m = _FOOTER_PATTERN.match(line)
        if m:
            footer_start = i
            i -= 1
        elif footer_start < len(lines) and line.strip() == '':
            # Blank line before footer block — stop.
            break
        else:
            # Not a footer line and we haven't started the footer block yet.
            break

    # If we found footers, re-parse them forward to handle multi-line values.
    if footer_start < len(lines):
        current_token = ''
        current_value_lines: list[str] = []

        for line in lines[footer_start:]:
            m = _FOOTER_PATTERN.match(line)
            if m:
                # Save previous footer if any.
                if current_token:
                    footers.append((current_token, '\n'.join(current_value_lines).strip()))
                current_token = m.group('token')
                current_value_lines = [m.group('value')]
            else:
                # Continuation line for the current footer value.
                current_value_lines.append(line)

        # Save last footer.
        if current_token:
            footers.append((current_token, '\n'.join(current_value_lines).strip()))

    # Body is everything before the footer block (stripping blank
    # separator lines).
    body_lines = lines[:footer_start]
    body = '\n'.join(body_lines).strip()

    return body, tuple(footers)


def _has_breaking_footer(
    footers: tuple[tuple[str, str], ...],
) -> tuple[bool, str]:
    """Check if any footer indicates a breaking change.

    Returns:
        ``(is_breaking, description)`` tuple.
    """
    for token, value in footers:
        # Spec rules 12, 16: "BREAKING CHANGE" or "BREAKING-CHANGE"
        # must be uppercase.
        if token in ('BREAKING CHANGE', 'BREAKING-CHANGE'):
            return True, value
    return False, ''


class ConventionalCommitParser:
    r"""Parser for `Conventional Commits v1.0.0 <https://www.conventionalcommits.org/en/v1.0.0/>`_.

    Parses the full commit message including subject, body, and footers.
    The ``message`` argument to :meth:`parse` can be either:

    - A single subject line: ``"feat(auth): add OAuth2"``
    - A full multi-line commit message with body and footers

    Spec compliance:

    - Types are case-insensitive (normalised to lowercase).
    - ``BREAKING CHANGE`` and ``BREAKING-CHANGE`` footers are both
      recognised (must be uppercase per spec rule 15).
    - ``!`` after type/scope indicates a breaking change.
    - Footers are parsed per the git trailer convention.
    - Revert commits are handled in two formats:

      - GitHub default: ``Revert "feat: add X"``
      - Conventional: ``revert: feat: add X``

    Example::

        parser = ConventionalCommitParser()

        # Single-line (subject only):
        cc = parser.parse('feat(auth): add OAuth2')
        assert cc.type == 'feat'
        assert cc.scope == 'auth'
        assert cc.bump == BumpType.MINOR

        # Multi-line with footer:
        msg = 'feat: new API\n\nRe-designed the public API.\n\nBREAKING CHANGE: removed v1 endpoints'
        cc = parser.parse(msg)
        assert cc.breaking is True
        assert cc.breaking_description == 'removed v1 endpoints'
        assert cc.bump == BumpType.MAJOR
    """

    def parse(self, message: str, sha: str = '') -> ParsedCommit | None:
        """Parse a commit message as a Conventional Commit.

        Args:
            message: The commit message (subject line, or full message
                with body and footers separated by blank lines).
            sha: The commit SHA (for reference).

        Returns:
            A :class:`ParsedCommit` if the message follows the
            convention, otherwise ``None``.
        """
        # Split into lines; first line is the subject.
        all_lines = message.split('\n')
        subject = all_lines[0].strip()

        # Check for revert: parse the inner message to determine what's reverted.
        revert_match = REVERT_PATTERN.match(subject)
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

        match = CC_PATTERN.match(subject)
        if not match:
            return None

        # Spec rule 15: types are case-insensitive — normalise to lowercase.
        cc_type = match.group('type').lower()
        scope = match.group('scope') or ''
        breaking = bool(match.group('breaking'))
        description = match.group('description')

        # Parse body and footers from remaining lines.
        # Find the first blank line after the subject to start body parsing.
        remaining_lines: list[str] = []
        if len(all_lines) > 1:
            # Skip the blank separator line(s) between subject and body.
            body_start = 1
            while body_start < len(all_lines) and all_lines[body_start].strip() == '':
                body_start += 1
            remaining_lines = all_lines[body_start:]

        body, footers = _parse_body_and_footers(remaining_lines)

        # Check for BREAKING CHANGE in footers (spec rules 11, 12, 16).
        footer_breaking, breaking_desc = _has_breaking_footer(footers)
        if footer_breaking:
            breaking = True

        # If "!" was used but no BREAKING CHANGE footer, the description
        # serves as the breaking change description (spec rule 13).
        breaking_description = breaking_desc
        if breaking and not breaking_description:
            breaking_description = description

        # Handle "revert: feat: add X" conventional format.
        if cc_type == 'revert':
            inner_cc = self.parse(description, sha=sha)
            reverted_bump = inner_cc.bump if inner_cc else BumpType.NONE
            return ParsedCommit(
                sha=sha,
                type='revert',
                scope=inner_cc.scope if inner_cc else scope,
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
            body=body,
            footers=footers,
            breaking=breaking,
            breaking_description=breaking_description,
            bump=bump,
            raw=message,
        )
