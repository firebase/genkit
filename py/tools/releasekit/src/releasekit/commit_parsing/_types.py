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

"""Pure types for commit message parsing.

This module has **zero** runtime dependencies beyond the standard library.
Everything here is a frozen dataclass, enum, or protocol — no I/O, no
logging, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class BumpType(Enum):
    """Semver bump types, ordered by precedence (highest first).

    The "strongest" bump wins when multiple commits affect the same
    package. For example, if a package has both a ``feat:`` and a
    ``fix:`` commit, the bump is ``MINOR`` (not ``PATCH``).
    """

    MAJOR = 'major'
    MINOR = 'minor'
    PATCH = 'patch'
    PRERELEASE = 'prerelease'
    NONE = 'none'


# Bump precedence: lower index = higher precedence.
BUMP_PRECEDENCE: list[BumpType] = [
    BumpType.MAJOR,
    BumpType.MINOR,
    BumpType.PATCH,
    BumpType.PRERELEASE,
    BumpType.NONE,
]


def max_bump(a: BumpType, b: BumpType) -> BumpType:
    """Return the higher-precedence bump type.

    >>> max_bump(BumpType.MINOR, BumpType.PATCH)
    <BumpType.MINOR: 'minor'>
    >>> max_bump(BumpType.NONE, BumpType.MAJOR)
    <BumpType.MAJOR: 'major'>
    """
    a_idx = BUMP_PRECEDENCE.index(a)
    b_idx = BUMP_PRECEDENCE.index(b)
    return BUMP_PRECEDENCE[min(a_idx, b_idx)]


@dataclass(frozen=True)
class ParsedCommit:
    """A parsed commit message (format-agnostic).

    This dataclass is the output of any :class:`CommitParser`
    implementation.  It captures everything releasekit needs
    for version bumps and changelog generation, regardless of
    the commit message convention used by the team.

    Attributes:
        sha: The full commit SHA.
        type: The commit type (e.g. ``"feat"``, ``"fix"``).
        scope: The optional scope (e.g. ``"auth"``).
        description: The commit description.
        breaking: Whether this is a breaking change.
        bump: The computed bump type for this commit.
        raw: The original unparsed commit message.
        is_revert: Whether this commit reverts another commit.
        reverted_bump: The bump type of the reverted commit (for cancellation).
    """

    sha: str
    type: str
    description: str
    scope: str = ''
    breaking: bool = False
    bump: BumpType = BumpType.NONE
    raw: str = ''
    is_revert: bool = False
    reverted_bump: BumpType = BumpType.NONE


# Backward-compatible alias.
ConventionalCommit = ParsedCommit


@runtime_checkable
class CommitParser(Protocol):
    """Protocol for commit message parsers.

    Implement this protocol to support commit message formats other
    than `Conventional Commits <https://www.conventionalcommits.org/>`_.

    A parser receives a raw commit subject line and returns a
    :class:`ParsedCommit` if the message matches the expected format,
    or ``None`` if it should be skipped.

    Built-in implementations:

    - :class:`~releasekit.commit_parsing.ConventionalCommitParser`

    Example custom parser::

        class JiraCommitParser:
            def parse(self, message: str, sha: str = '') -> ParsedCommit | None:
                # Parse "[PROJ-123] fix: description" format
                ...
    """

    def parse(self, message: str, sha: str = '') -> ParsedCommit | None:
        """Parse a commit message.

        Args:
            message: The commit subject line.
            sha: The commit SHA (for reference).

        Returns:
            A :class:`ParsedCommit` if the message matches, else ``None``.
        """
        ...
