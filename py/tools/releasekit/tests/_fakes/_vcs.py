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

"""Fake VCS backend for tests.

Provides a configurable :class:`FakeVCS` that satisfies the full
:class:`~releasekit.backends.vcs.VCS` protocol with sensible no-op
defaults.  Constructor keyword arguments let callers inject the specific
state each test needs without subclassing.

For tests that need to *record* calls (e.g. which tags were created),
subclass and override only the methods you care about.
"""

from __future__ import annotations

from releasekit.backends._run import CommandResult

OK = CommandResult(command=[], return_code=0, stdout='', stderr='')
"""A successful no-op ``CommandResult`` for use as a default return value."""


class FakeVCS:
    """Configurable VCS test double that satisfies the full VCS protocol.

    Every method has a sensible no-op default.  Constructor keyword arguments
    let callers inject the specific state each test needs without subclassing.
    """

    def __init__(
        self,
        *,
        sha: str = 'abc123',
        clean: bool = True,
        shallow: bool = False,
        default_branch: str = 'main',
        current_branch: str = 'main',
        log_lines: list[str] | None = None,
        log_by_path: dict[str, list[str]] | None = None,
        diff_files: list[str] | None = None,
        tags: set[str] | None = None,
        tag_list: list[str] | None = None,
        tag_shas: dict[str, str] | None = None,
    ) -> None:
        """Initialize with configurable state.

        Args:
            sha: Value returned by ``current_sha()``.
            clean: Value returned by ``is_clean()``.
            shallow: Value returned by ``is_shallow()``.
            default_branch: Value returned by ``default_branch()``.
            current_branch: Value returned by ``current_branch()``.
            log_lines: Lines returned by ``log()`` (flat, no path scoping).
            log_by_path: Path-scoped log lines for ``log(paths=...)``.
                When ``paths`` is provided to ``log()``, lines are looked
                up per-path from this dict.  Falls back to ``log_lines``.
            diff_files: Files returned by ``diff_files()``.
            tags: Set of existing tag names (used by ``tag_exists``,
                ``list_tags``).  Mutable — ``tag()`` and ``delete_tag()``
                update it.
            tag_list: Ordered list of tags for ``list_tags()`` (takes
                precedence over ``tags`` when provided).
            tag_shas: Mapping of tag name → commit SHA for
                ``tag_commit_sha()``.
        """
        self._sha = sha
        self._clean = clean
        self._shallow = shallow
        self._default_branch = default_branch
        self._current_branch = current_branch
        self._log_lines = log_lines or []
        self._log_by_path = log_by_path or {}
        self._diff_files = diff_files or []
        self._tags: set[str] = tags if tags is not None else set()
        self._tag_list = tag_list
        self._tag_shas = tag_shas or {}

    # -- Query methods -------------------------------------------------------

    async def is_clean(self, *, dry_run: bool = False) -> bool:
        """Return configured clean state."""
        return self._clean

    async def is_shallow(self) -> bool:
        """Return configured shallow state."""
        return self._shallow

    async def default_branch(self) -> str:
        """Return configured default branch."""
        return self._default_branch

    async def current_branch(self) -> str:
        """Return configured current branch."""
        return self._current_branch

    async def current_sha(self) -> str:
        """Return configured SHA."""
        return self._sha

    async def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
        first_parent: bool = False,
        no_merges: bool = False,
        max_commits: int = 0,
    ) -> list[str]:
        """Return canned log lines, optionally scoped by path."""
        if paths and self._log_by_path:
            result: list[str] = []
            for p in paths:
                result.extend(self._log_by_path.get(p, []))
            return result
        return list(self._log_lines)

    async def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return configured diff files."""
        return list(self._diff_files)

    async def tag_exists(self, tag_name: str) -> bool:
        """Return True if tag is in the configured tag set."""
        return tag_name in self._tags

    async def list_tags(self, *, pattern: str = '') -> list[str]:
        """Return tags as a sorted list."""
        if self._tag_list is not None:
            return list(self._tag_list)
        return sorted(self._tags)

    async def tag_commit_sha(self, tag_name: str) -> str:
        """Return configured SHA for a tag, or empty string."""
        return self._tag_shas.get(tag_name, '')

    # -- Mutating methods (no-op by default) ---------------------------------

    async def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op commit."""
        return OK

    async def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op tag — adds to the internal tag set."""
        if not dry_run:
            self._tags.add(tag_name)
        return OK

    async def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op delete_tag — removes from the internal tag set."""
        self._tags.discard(tag_name)
        return OK

    async def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        set_upstream: bool = True,
        force: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op push."""
        return OK

    async def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op checkout_branch."""
        return OK

    async def tags_on_branch(self, branch: str) -> list[str]:
        """Return tags as a sorted list (ignores branch)."""
        if self._tag_list is not None:
            return list(self._tag_list)
        return sorted(self._tags)

    async def commit_exists(self, sha: str) -> bool:
        """Return True if sha matches the configured SHA."""
        return sha == self._sha

    async def cherry_pick(
        self,
        sha: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """No-op cherry_pick."""
        return OK

    async def cherry_pick_abort(self) -> CommandResult:
        """No-op cherry_pick_abort."""
        return OK

    async def tag_date(self, tag_name: str) -> str:
        """Return empty string (no date info in fake)."""
        return ''
