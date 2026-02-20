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

"""Tests for the commit_parsing subpackage.

Covers the Conventional Commits v1.0.0 spec, the Angular commit
convention, multi-line message parsing, footer extraction, and
the CommitParser protocol.

All tests are pure — no I/O, no mocks, no async.
"""

from __future__ import annotations

import pytest
from releasekit.commit_parsing import (
    ANGULAR_TYPES,
    BUMP_PRECEDENCE,
    AngularCommitParser,
    BumpType,
    CommitParser,
    ConventionalCommit,
    ConventionalCommitParser,
    ParsedCommit,
    max_bump,
    parse_conventional_commit,
)


class TestBumpType:
    """Tests for BumpType enum."""

    def test_values(self) -> None:
        """Test values."""
        assert BumpType.MAJOR.value == 'major'
        assert BumpType.MINOR.value == 'minor'
        assert BumpType.PATCH.value == 'patch'
        assert BumpType.PRERELEASE.value == 'prerelease'
        assert BumpType.NONE.value == 'none'

    def test_precedence_order(self) -> None:
        """Test precedence order."""
        assert BUMP_PRECEDENCE == [
            BumpType.MAJOR,
            BumpType.MINOR,
            BumpType.PATCH,
            BumpType.PRERELEASE,
            BumpType.NONE,
        ]


class TestMaxBump:
    """Tests for the max_bump pure function."""

    def test_same_type(self) -> None:
        """Test same type."""
        for bt in BumpType:
            assert max_bump(bt, bt) == bt

    def test_major_wins_over_all(self) -> None:
        """Test major wins over all."""
        for bt in BumpType:
            assert max_bump(BumpType.MAJOR, bt) == BumpType.MAJOR
            assert max_bump(bt, BumpType.MAJOR) == BumpType.MAJOR

    def test_minor_over_patch(self) -> None:
        """Test minor over patch."""
        assert max_bump(BumpType.MINOR, BumpType.PATCH) == BumpType.MINOR
        assert max_bump(BumpType.PATCH, BumpType.MINOR) == BumpType.MINOR

    def test_patch_over_none(self) -> None:
        """Test patch over none."""
        assert max_bump(BumpType.PATCH, BumpType.NONE) == BumpType.PATCH
        assert max_bump(BumpType.NONE, BumpType.PATCH) == BumpType.PATCH

    def test_prerelease_over_none(self) -> None:
        """Test prerelease over none."""
        assert max_bump(BumpType.PRERELEASE, BumpType.NONE) == BumpType.PRERELEASE

    def test_patch_over_prerelease(self) -> None:
        """Test patch over prerelease."""
        assert max_bump(BumpType.PATCH, BumpType.PRERELEASE) == BumpType.PATCH

    def test_none_none(self) -> None:
        """Test none none."""
        assert max_bump(BumpType.NONE, BumpType.NONE) == BumpType.NONE

    def test_commutative(self) -> None:
        """max_bump(a, b) == max_bump(b, a) for all pairs."""
        for a in BumpType:
            for b in BumpType:
                assert max_bump(a, b) == max_bump(b, a)


class TestParsedCommit:
    """Tests for the ParsedCommit dataclass."""

    def test_frozen(self) -> None:
        """Test frozen."""
        cc = ParsedCommit(sha='abc', type='feat', description='x')
        with pytest.raises(AttributeError):
            cc.sha = 'def'  # type: ignore[misc]

    def test_defaults(self) -> None:
        """Test defaults."""
        cc = ParsedCommit(sha='', type='feat', description='x')
        assert cc.scope == ''
        assert cc.body == ''
        assert cc.footers == ()
        assert cc.breaking is False
        assert cc.breaking_description == ''
        assert cc.bump == BumpType.NONE
        assert cc.raw == ''
        assert cc.is_revert is False
        assert cc.reverted_bump == BumpType.NONE

    def test_alias(self) -> None:
        """ConventionalCommit is an alias for ParsedCommit."""
        assert ConventionalCommit is ParsedCommit

    def test_equality(self) -> None:
        """Test equality."""
        a = ParsedCommit(sha='a', type='feat', description='x', bump=BumpType.MINOR)
        b = ParsedCommit(sha='a', type='feat', description='x', bump=BumpType.MINOR)
        assert a == b

    def test_inequality(self) -> None:
        """Test inequality."""
        a = ParsedCommit(sha='a', type='feat', description='x')
        b = ParsedCommit(sha='b', type='feat', description='x')
        assert a != b


class TestCommitParserProtocol:
    """Tests for the CommitParser protocol."""

    def test_conventional_parser_satisfies_protocol(self) -> None:
        """Test conventional parser satisfies protocol."""
        parser = ConventionalCommitParser()
        assert isinstance(parser, CommitParser)

    def test_angular_parser_satisfies_protocol(self) -> None:
        """Test angular parser satisfies protocol."""
        parser = AngularCommitParser()
        assert isinstance(parser, CommitParser)

    def test_custom_parser_satisfies_protocol(self) -> None:
        """Test custom parser satisfies protocol."""

        class MyParser:
            """MyParser."""

            def parse(self, message: str, sha: str = '') -> ParsedCommit | None:
                """Parse."""
                if message.startswith('['):
                    return ParsedCommit(sha=sha, type='fix', description=message)
                return None

        parser = MyParser()
        assert isinstance(parser, CommitParser)

    def test_non_parser_fails_protocol(self) -> None:
        """Test non parser fails protocol."""

        class NotAParser:
            """NotAParser."""

            def analyze(self, msg: str) -> str:
                """Analyze."""
                return msg

        assert not isinstance(NotAParser(), CommitParser)


class TestConventionalCommitParser:
    """Comprehensive tests for ConventionalCommitParser.parse()."""

    @pytest.fixture()
    def parser(self) -> ConventionalCommitParser:
        """Parser."""
        return ConventionalCommitParser()

    # --- Basic types ---

    def test_feat(self, parser: ConventionalCommitParser) -> None:
        """Test feat."""
        cc = parser.parse('feat: add streaming support')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.description == 'add streaming support'
        assert cc.bump == BumpType.MINOR
        assert cc.breaking is False

    def test_fix(self, parser: ConventionalCommitParser) -> None:
        """Test fix."""
        cc = parser.parse('fix: resolve null pointer')
        assert cc is not None
        assert cc.type == 'fix'
        assert cc.bump == BumpType.PATCH

    def test_perf(self, parser: ConventionalCommitParser) -> None:
        """Test perf."""
        cc = parser.parse('perf: optimize hot loop')
        assert cc is not None
        assert cc.type == 'perf'
        assert cc.bump == BumpType.PATCH

    def test_chore(self, parser: ConventionalCommitParser) -> None:
        """Test chore."""
        cc = parser.parse('chore: update deps')
        assert cc is not None
        assert cc.type == 'chore'
        assert cc.bump == BumpType.NONE

    def test_docs(self, parser: ConventionalCommitParser) -> None:
        """Test docs."""
        cc = parser.parse('docs: update README')
        assert cc is not None
        assert cc.type == 'docs'
        assert cc.bump == BumpType.NONE

    def test_ci(self, parser: ConventionalCommitParser) -> None:
        """Test ci."""
        cc = parser.parse('ci: add coverage')
        assert cc is not None
        assert cc.type == 'ci'
        assert cc.bump == BumpType.NONE

    def test_build(self, parser: ConventionalCommitParser) -> None:
        """Test build."""
        cc = parser.parse('build: update Makefile')
        assert cc is not None
        assert cc.type == 'build'
        assert cc.bump == BumpType.NONE

    def test_style(self, parser: ConventionalCommitParser) -> None:
        """Test style."""
        cc = parser.parse('style: fix formatting')
        assert cc is not None
        assert cc.type == 'style'
        assert cc.bump == BumpType.NONE

    def test_refactor(self, parser: ConventionalCommitParser) -> None:
        """Test refactor."""
        cc = parser.parse('refactor: extract helper')
        assert cc is not None
        assert cc.type == 'refactor'
        assert cc.bump == BumpType.NONE

    def test_test(self, parser: ConventionalCommitParser) -> None:
        """Test test."""
        cc = parser.parse('test: add unit tests')
        assert cc is not None
        assert cc.type == 'test'
        assert cc.bump == BumpType.NONE

    # --- Scope ---

    def test_scope(self, parser: ConventionalCommitParser) -> None:
        """Test scope."""
        cc = parser.parse('feat(auth): add OAuth2')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.scope == 'auth'
        assert cc.description == 'add OAuth2'

    def test_empty_scope(self, parser: ConventionalCommitParser) -> None:
        """Test empty scope."""
        cc = parser.parse('feat(): add thing')
        assert cc is not None
        assert cc.scope == ''

    def test_scope_with_dashes(self, parser: ConventionalCommitParser) -> None:
        """Test scope with dashes."""
        cc = parser.parse('fix(my-scope): thing')
        assert cc is not None
        assert cc.scope == 'my-scope'

    # --- Breaking changes (subject line) ---

    def test_breaking_bang(self, parser: ConventionalCommitParser) -> None:
        """Test breaking bang."""
        cc = parser.parse('fix!: remove deprecated API')
        assert cc is not None
        assert cc.breaking is True
        assert cc.bump == BumpType.MAJOR

    def test_breaking_scope_bang(self, parser: ConventionalCommitParser) -> None:
        """Test breaking scope bang."""
        cc = parser.parse('feat(api)!: redesign endpoints')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.scope == 'api'
        assert cc.breaking is True
        assert cc.bump == BumpType.MAJOR

    def test_chore_breaking(self, parser: ConventionalCommitParser) -> None:
        """Even chore with ! is MAJOR."""
        cc = parser.parse('chore!: drop Python 3.9 support')
        assert cc is not None
        assert cc.breaking is True
        assert cc.bump == BumpType.MAJOR

    def test_breaking_bang_description_is_breaking_description(self, parser: ConventionalCommitParser) -> None:
        """When ! is used without a BREAKING CHANGE footer, description serves as breaking_description."""
        cc = parser.parse('feat!: remove v1 endpoints')
        assert cc is not None
        assert cc.breaking is True
        assert cc.breaking_description == 'remove v1 endpoints'

    # --- Case insensitivity (spec rule 15) ---

    def test_uppercase_type_normalised(self, parser: ConventionalCommitParser) -> None:
        """Spec rule 15: types are case-insensitive, normalised to lowercase."""
        cc = parser.parse('FEAT: add thing')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.bump == BumpType.MINOR

    def test_mixed_case_type_normalised(self, parser: ConventionalCommitParser) -> None:
        """Mixed case types are normalised to lowercase."""
        cc = parser.parse('Fix: bug')
        assert cc is not None
        assert cc.type == 'fix'
        assert cc.bump == BumpType.PATCH

    # --- Revert commits ---

    def test_revert_github_format(self, parser: ConventionalCommitParser) -> None:
        """Test revert github format."""
        cc = parser.parse('Revert "feat: add streaming"')
        assert cc is not None
        assert cc.type == 'revert'
        assert cc.is_revert is True
        assert cc.reverted_bump == BumpType.MINOR
        assert cc.bump == BumpType.NONE
        assert cc.description == 'feat: add streaming'

    def test_revert_github_lowercase(self, parser: ConventionalCommitParser) -> None:
        """Test revert github lowercase."""
        cc = parser.parse('revert "fix: null pointer"')
        assert cc is not None
        assert cc.is_revert is True
        assert cc.reverted_bump == BumpType.PATCH

    def test_revert_conventional_format(self, parser: ConventionalCommitParser) -> None:
        """Test revert conventional format."""
        cc = parser.parse('revert: feat: add streaming')
        assert cc is not None
        assert cc.type == 'revert'
        assert cc.is_revert is True
        assert cc.reverted_bump == BumpType.MINOR

    def test_revert_conventional_with_scope(self, parser: ConventionalCommitParser) -> None:
        """Test revert conventional with scope."""
        cc = parser.parse('revert: feat(auth): add OAuth2')
        assert cc is not None
        assert cc.is_revert is True
        assert cc.scope == 'auth'
        assert cc.reverted_bump == BumpType.MINOR

    def test_revert_non_conventional_inner(self, parser: ConventionalCommitParser) -> None:
        """Revert of a non-conventional message still parses as revert."""
        cc = parser.parse('Revert "Update README.md"')
        assert cc is not None
        assert cc.is_revert is True
        assert cc.reverted_bump == BumpType.NONE

    def test_revert_breaking_inner(self, parser: ConventionalCommitParser) -> None:
        """Test revert breaking inner."""
        cc = parser.parse('Revert "feat!: breaking change"')
        assert cc is not None
        assert cc.is_revert is True
        assert cc.reverted_bump == BumpType.MAJOR

    # --- Non-conventional messages ---

    def test_non_conventional_plain(self, parser: ConventionalCommitParser) -> None:
        """Test non conventional plain."""
        assert parser.parse('Update README.md') is None

    def test_non_conventional_merge(self, parser: ConventionalCommitParser) -> None:
        """Test non conventional merge."""
        assert parser.parse('Merge pull request #42') is None

    def test_non_conventional_wip(self, parser: ConventionalCommitParser) -> None:
        """Test non conventional wip."""
        assert parser.parse('WIP') is None

    def test_non_conventional_empty(self, parser: ConventionalCommitParser) -> None:
        """Test non conventional empty."""
        assert parser.parse('') is None

    def test_non_conventional_whitespace(self, parser: ConventionalCommitParser) -> None:
        """Test non conventional whitespace."""
        assert parser.parse('   ') is None

    # --- Edge cases ---

    def test_empty_description(self, parser: ConventionalCommitParser) -> None:
        """Test empty description."""
        assert parser.parse('feat:') is None
        assert parser.parse('feat: ') is None

    def test_sha_preserved(self, parser: ConventionalCommitParser) -> None:
        """Test sha preserved."""
        cc = parser.parse('fix: bug', sha='abc123')
        assert cc is not None
        assert cc.sha == 'abc123'

    def test_raw_preserved(self, parser: ConventionalCommitParser) -> None:
        """Test raw preserved."""
        msg = 'feat(auth): add OAuth2'
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.raw == msg

    def test_leading_trailing_whitespace(self, parser: ConventionalCommitParser) -> None:
        """Test leading trailing whitespace."""
        cc = parser.parse('  feat: add thing  ')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.description == 'add thing'

    def test_colon_in_description(self, parser: ConventionalCommitParser) -> None:
        """Test colon in description."""
        cc = parser.parse('fix: handle edge case: null input')
        assert cc is not None
        assert cc.description == 'handle edge case: null input'


class TestConventionalCommitMultiLine:
    """Tests for full multi-line Conventional Commit messages."""

    @pytest.fixture()
    def parser(self) -> ConventionalCommitParser:
        """Parser."""
        return ConventionalCommitParser()

    def test_body_extracted(self, parser: ConventionalCommitParser) -> None:
        """Spec rule 6: body begins one blank line after description."""
        msg = 'feat: add streaming\n\nThis adds real-time streaming support.'
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.description == 'add streaming'
        assert cc.body == 'This adds real-time streaming support.'

    def test_multi_paragraph_body(self, parser: ConventionalCommitParser) -> None:
        """Spec rule 7: body may consist of multiple paragraphs."""
        msg = 'fix: prevent racing\n\nIntroduce a request id.\n\nRemove old timeouts.'
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.body == 'Introduce a request id.\n\nRemove old timeouts.'

    def test_breaking_change_footer(self, parser: ConventionalCommitParser) -> None:
        """Spec rule 12: BREAKING CHANGE footer triggers MAJOR."""
        msg = 'feat: new API\n\nBREAKING CHANGE: removed v1 endpoints'
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.breaking is True
        assert cc.breaking_description == 'removed v1 endpoints'
        assert cc.bump == BumpType.MAJOR

    def test_breaking_change_hyphen_footer(self, parser: ConventionalCommitParser) -> None:
        """Spec rule 16: BREAKING-CHANGE is synonymous with BREAKING CHANGE."""
        msg = 'feat: new API\n\nBREAKING-CHANGE: removed v1 endpoints'
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.breaking is True
        assert cc.breaking_description == 'removed v1 endpoints'
        assert cc.bump == BumpType.MAJOR

    def test_bang_plus_breaking_footer(self, parser: ConventionalCommitParser) -> None:
        """Spec example: both ! and BREAKING CHANGE footer."""
        msg = 'chore!: drop Node 6\n\nBREAKING CHANGE: use JS features not in Node 6.'
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.breaking is True
        assert cc.breaking_description == 'use JS features not in Node 6.'
        assert cc.bump == BumpType.MAJOR

    def test_footer_colon_separator(self, parser: ConventionalCommitParser) -> None:
        """Spec rule 8: footers use 'token: value' format."""
        msg = 'fix: bug\n\nReviewed-by: Jane\nRefs: #123'
        cc = parser.parse(msg)
        assert cc is not None
        assert ('Reviewed-by', 'Jane') in cc.footers
        assert ('Refs', '#123') in cc.footers

    def test_footer_hash_separator(self, parser: ConventionalCommitParser) -> None:
        """Spec rule 8: footers can use 'token #value' format."""
        msg = 'fix: bug\n\nFixes #42'
        cc = parser.parse(msg)
        assert cc is not None
        assert ('Fixes', '42') in cc.footers

    def test_body_with_footers(self, parser: ConventionalCommitParser) -> None:
        """Body and footers are separated correctly."""
        msg = (
            'fix: prevent racing\n'
            '\n'
            'Introduce a request id and a reference to latest request.\n'
            'Remove timeouts.\n'
            '\n'
            'Reviewed-by: Z\n'
            'Refs: #123'
        )
        cc = parser.parse(msg)
        assert cc is not None
        assert 'Introduce a request id' in cc.body
        assert 'Remove timeouts' in cc.body
        assert ('Reviewed-by', 'Z') in cc.footers
        assert ('Refs', '#123') in cc.footers

    def test_no_body_with_footer(self, parser: ConventionalCommitParser) -> None:
        """Footer directly after subject (no body)."""
        msg = 'feat: add thing\n\nBREAKING CHANGE: old API removed'
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.breaking is True
        assert cc.breaking_description == 'old API removed'
        # When BREAKING CHANGE is the only content, it's a footer, not body.

    def test_subject_only_no_body_no_footers(self, parser: ConventionalCommitParser) -> None:
        """Single-line message has empty body and footers."""
        cc = parser.parse('docs: correct spelling')
        assert cc is not None
        assert cc.body == ''
        assert cc.footers == ()

    def test_spec_example_with_description_and_breaking_footer(self, parser: ConventionalCommitParser) -> None:
        """Spec example: feat with breaking change footer."""
        msg = (
            'feat: allow provided config object to extend other configs\n'
            '\n'
            'BREAKING CHANGE: `extends` key in config file is now used for '
            'extending other config files'
        )
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.breaking is True
        assert '`extends` key' in cc.breaking_description

    def test_spec_example_multi_paragraph_body_and_multiple_footers(self, parser: ConventionalCommitParser) -> None:
        """Spec example: multi-paragraph body with multiple footers."""
        msg = (
            'fix: prevent racing of requests\n'
            '\n'
            'Introduce a request id and a reference to latest request. Dismiss\n'
            'incoming responses other than from latest request.\n'
            '\n'
            'Remove timeouts which were used to mitigate the racing issue but are\n'
            'obsolete now.\n'
            '\n'
            'Reviewed-by: Z\n'
            'Refs: #123'
        )
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.type == 'fix'
        assert cc.bump == BumpType.PATCH
        assert 'Introduce a request id' in cc.body
        assert 'obsolete now.' in cc.body
        assert ('Reviewed-by', 'Z') in cc.footers
        assert ('Refs', '#123') in cc.footers


class TestAngularCommitParser:
    """Comprehensive tests for AngularCommitParser."""

    @pytest.fixture()
    def parser(self) -> AngularCommitParser:
        """Parser."""
        return AngularCommitParser()

    # --- Allowed types ---

    @pytest.mark.parametrize(
        'commit_type',
        sorted(ANGULAR_TYPES),
    )
    def test_all_angular_types_accepted(self, parser: AngularCommitParser, commit_type: str) -> None:
        """Every Angular type is accepted."""
        cc = parser.parse(f'{commit_type}: do something')
        assert cc is not None
        assert cc.type == commit_type

    def test_feat_minor(self, parser: AngularCommitParser) -> None:
        """Feat maps to MINOR."""
        cc = parser.parse('feat: add streaming')
        assert cc is not None
        assert cc.bump == BumpType.MINOR

    def test_fix_patch(self, parser: AngularCommitParser) -> None:
        """Fix maps to PATCH."""
        cc = parser.parse('fix: null pointer')
        assert cc is not None
        assert cc.bump == BumpType.PATCH

    def test_perf_patch(self, parser: AngularCommitParser) -> None:
        """Perf maps to PATCH."""
        cc = parser.parse('perf: optimize loop')
        assert cc is not None
        assert cc.bump == BumpType.PATCH

    @pytest.mark.parametrize(
        'commit_type',
        ['build', 'ci', 'docs', 'refactor', 'style', 'test'],
    )
    def test_non_release_types_none(self, parser: AngularCommitParser, commit_type: str) -> None:
        """Non-release types map to NONE."""
        cc = parser.parse(f'{commit_type}: do something')
        assert cc is not None
        assert cc.bump == BumpType.NONE

    # --- Rejected types ---

    def test_chore_rejected(self, parser: AngularCommitParser) -> None:
        """Chore is not in Angular's type list."""
        assert parser.parse('chore: update deps') is None

    def test_release_rejected(self, parser: AngularCommitParser) -> None:
        """Release is not in Angular's type list."""
        assert parser.parse('release: v1.0.0') is None

    def test_wip_rejected(self, parser: AngularCommitParser) -> None:
        """Wip is not in Angular's type list."""
        assert parser.parse('wip: work in progress') is None

    # --- Custom allowlist ---

    def test_custom_types(self) -> None:
        """Custom types extend the allowlist."""
        parser = AngularCommitParser(
            allowed_types=frozenset({*ANGULAR_TYPES, 'chore'}),
        )
        cc = parser.parse('chore: update deps')
        assert cc is not None
        assert cc.type == 'chore'

    # --- Scope ---

    def test_scope(self, parser: AngularCommitParser) -> None:
        """Test scope extraction."""
        cc = parser.parse('feat(auth): add OAuth2')
        assert cc is not None
        assert cc.scope == 'auth'

    # --- Breaking changes ---

    def test_breaking_bang(self, parser: AngularCommitParser) -> None:
        """! triggers MAJOR."""
        cc = parser.parse('fix!: remove deprecated API')
        assert cc is not None
        assert cc.breaking is True
        assert cc.bump == BumpType.MAJOR

    def test_breaking_footer(self, parser: AngularCommitParser) -> None:
        """BREAKING CHANGE footer triggers MAJOR."""
        msg = 'feat: new config\n\nBREAKING CHANGE: old config format removed'
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.breaking is True
        assert cc.breaking_description == 'old config format removed'

    # --- Case insensitivity ---

    def test_uppercase_type_normalised(self, parser: AngularCommitParser) -> None:
        """Types are case-insensitive, normalised to lowercase."""
        cc = parser.parse('FEAT: add thing')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.bump == BumpType.MINOR

    # --- Reverts ---

    def test_revert_github_format(self, parser: AngularCommitParser) -> None:
        """GitHub revert format works."""
        cc = parser.parse('Revert "feat: add streaming"')
        assert cc is not None
        assert cc.is_revert is True
        assert cc.reverted_bump == BumpType.MINOR

    def test_revert_non_angular_inner(self, parser: AngularCommitParser) -> None:
        """Revert of a non-Angular message (e.g. chore) has NONE reverted_bump."""
        cc = parser.parse('Revert "chore: update deps"')
        assert cc is not None
        assert cc.is_revert is True
        assert cc.reverted_bump == BumpType.NONE

    # --- Multi-line ---

    def test_body_and_footers(self, parser: AngularCommitParser) -> None:
        """Full message with body and footers."""
        msg = (
            'fix(core): prevent null pointer\n'
            '\n'
            'Added null check before dereferencing.\n'
            '\n'
            'Reviewed-by: Alice\n'
            'Refs: #456'
        )
        cc = parser.parse(msg)
        assert cc is not None
        assert cc.type == 'fix'
        assert cc.scope == 'core'
        assert 'null check' in cc.body
        assert ('Reviewed-by', 'Alice') in cc.footers

    # --- Non-conventional messages ---

    def test_non_conventional(self, parser: AngularCommitParser) -> None:
        """Non-conventional messages return None."""
        assert parser.parse('Update README.md') is None
        assert parser.parse('') is None
        assert parser.parse('   ') is None


class TestParseConventionalCommitFunction:
    """Tests for the module-level convenience function."""

    def test_delegates_to_parser(self) -> None:
        """Test delegates to parser."""
        cc = parse_conventional_commit('feat: add thing')
        assert cc is not None
        assert cc.type == 'feat'
        assert cc.bump == BumpType.MINOR

    def test_returns_none_for_non_conventional(self) -> None:
        """Test returns none for non conventional."""
        assert parse_conventional_commit('Update README') is None

    def test_sha_forwarded(self) -> None:
        """Test sha forwarded."""
        cc = parse_conventional_commit('fix: bug', sha='deadbeef')
        assert cc is not None
        assert cc.sha == 'deadbeef'

    def test_multi_line_with_footer(self) -> None:
        """Multi-line messages work through the convenience function."""
        msg = 'feat: new API\n\nBREAKING CHANGE: v1 removed'
        cc = parse_conventional_commit(msg)
        assert cc is not None
        assert cc.breaking is True


class TestCustomParser:
    """Test that a custom parser can be used as a drop-in replacement."""

    def test_custom_parser_produces_parsed_commit(self) -> None:
        """Test custom parser produces parsed commit."""

        class PrefixParser:
            """Parses '[TYPE] description' format."""

            def parse(self, message: str, sha: str = '') -> ParsedCommit | None:
                """Parse."""
                if not message.startswith('['):
                    return None
                end = message.index(']')
                commit_type = message[1:end].lower()
                description = message[end + 1 :].strip()
                bump = BumpType.MINOR if commit_type == 'feature' else BumpType.PATCH
                return ParsedCommit(
                    sha=sha,
                    type=commit_type,
                    description=description,
                    bump=bump,
                    raw=message,
                )

        parser = PrefixParser()
        assert isinstance(parser, CommitParser)

        cc = parser.parse('[FEATURE] add streaming', sha='abc')
        assert cc is not None
        assert cc.type == 'feature'
        assert cc.bump == BumpType.MINOR
        assert cc.description == 'add streaming'

        cc2 = parser.parse('[BUGFIX] null pointer', sha='def')
        assert cc2 is not None
        assert cc2.type == 'bugfix'
        assert cc2.bump == BumpType.PATCH

        assert parser.parse('not a bracket message') is None
