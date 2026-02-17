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

"""Tests for the SPDX license expression parser."""

from __future__ import annotations

import pytest
from releasekit.spdx_expr import (
    And,
    LicenseId,
    LicenseRef,
    Or,
    ParseError,
    With,
    license_ids,
    parse,
)

# ── Simple license identifiers ──────────────────────────────────────────


class TestSimpleLicenseId:
    """Tests for simple License Id."""

    def test_single_id(self) -> None:
        """Test single id."""
        result = parse('MIT')
        assert result == LicenseId(id='MIT', or_later=False)

    def test_hyphenated_id(self) -> None:
        """Test hyphenated id."""
        result = parse('Apache-2.0')
        assert result == LicenseId(id='Apache-2.0', or_later=False)

    def test_dotted_id(self) -> None:
        """Test dotted id."""
        result = parse('GPL-3.0-only')
        assert result == LicenseId(id='GPL-3.0-only', or_later=False)

    def test_or_later_suffix(self) -> None:
        """Test or later suffix."""
        result = parse('GPL-2.0+')
        assert result == LicenseId(id='GPL-2.0', or_later=True)

    def test_or_later_with_full_id(self) -> None:
        """Test or later with full id."""
        result = parse('LGPL-2.1-only+')
        assert result == LicenseId(id='LGPL-2.1-only', or_later=True)

    def test_whitespace_stripped(self) -> None:
        """Test whitespace stripped."""
        result = parse('  MIT  ')
        assert result == LicenseId(id='MIT', or_later=False)


# ── LicenseRef ───────────────────────────────────────────────────────────


class TestLicenseRef:
    """Tests for license Ref."""

    def test_simple_license_ref(self) -> None:
        """Test simple license ref."""
        result = parse('LicenseRef-Custom')
        assert result == LicenseRef(ref='LicenseRef-Custom', document_ref='')

    def test_license_ref_with_document_ref(self) -> None:
        """Test license ref with document ref."""
        result = parse('DocumentRef-spdx-tool-1.2:LicenseRef-MIT-Style-2')
        assert result == LicenseRef(
            ref='LicenseRef-MIT-Style-2',
            document_ref='DocumentRef-spdx-tool-1.2',
        )

    def test_addition_ref(self) -> None:
        """Test addition ref."""
        result = parse('AdditionRef-Custom-Exception')
        assert result == LicenseRef(ref='AdditionRef-Custom-Exception', document_ref='')


# ── WITH operator ────────────────────────────────────────────────────────


class TestWithOperator:
    """Tests for with Operator."""

    def test_with_exception(self) -> None:
        """Test with exception."""
        result = parse('GPL-2.0-or-later WITH Classpath-exception-2.0')
        assert result == With(
            license=LicenseId(id='GPL-2.0-or-later', or_later=False),
            exception='Classpath-exception-2.0',
        )

    def test_with_bison_exception(self) -> None:
        """Test with bison exception."""
        result = parse('GPL-2.0-or-later WITH Bison-exception-2.2')
        assert result == With(
            license=LicenseId(id='GPL-2.0-or-later', or_later=False),
            exception='Bison-exception-2.2',
        )

    def test_with_lowercase(self) -> None:
        """Test with lowercase."""
        result = parse('Apache-2.0 with LLVM-exception')
        assert result == With(
            license=LicenseId(id='Apache-2.0', or_later=False),
            exception='LLVM-exception',
        )

    def test_with_or_later_and_exception(self) -> None:
        """Test with or later and exception."""
        result = parse('GPL-2.0+ WITH Classpath-exception-2.0')
        assert result == With(
            license=LicenseId(id='GPL-2.0', or_later=True),
            exception='Classpath-exception-2.0',
        )

    def test_with_license_ref(self) -> None:
        """Test with license ref."""
        result = parse('LicenseRef-Custom WITH AdditionRef-Custom-Exception')
        assert result == With(
            license=LicenseRef(ref='LicenseRef-Custom', document_ref=''),
            exception='AdditionRef-Custom-Exception',
        )


# ── AND operator ─────────────────────────────────────────────────────────


class TestAndOperator:
    """Tests for and Operator."""

    def test_two_licenses(self) -> None:
        """Test two licenses."""
        result = parse('MIT AND BSD-3-Clause')
        assert result == And(
            left=LicenseId(id='MIT'),
            right=LicenseId(id='BSD-3-Clause'),
        )

    def test_three_licenses_left_associative(self) -> None:
        """Test three licenses left associative."""
        result = parse('MIT AND BSD-3-Clause AND Apache-2.0')
        assert result == And(
            left=And(
                left=LicenseId(id='MIT'),
                right=LicenseId(id='BSD-3-Clause'),
            ),
            right=LicenseId(id='Apache-2.0'),
        )

    def test_lowercase_and(self) -> None:
        """Test lowercase and."""
        result = parse('MIT and BSD-3-Clause')
        assert result == And(
            left=LicenseId(id='MIT'),
            right=LicenseId(id='BSD-3-Clause'),
        )


# ── OR operator ──────────────────────────────────────────────────────────


class TestOrOperator:
    """Tests for or Operator."""

    def test_two_licenses(self) -> None:
        """Test two licenses."""
        result = parse('MIT OR Apache-2.0')
        assert result == Or(
            left=LicenseId(id='MIT'),
            right=LicenseId(id='Apache-2.0'),
        )

    def test_three_licenses_left_associative(self) -> None:
        """Test three licenses left associative."""
        result = parse('MIT OR Apache-2.0 OR GPL-3.0-only')
        assert result == Or(
            left=Or(
                left=LicenseId(id='MIT'),
                right=LicenseId(id='Apache-2.0'),
            ),
            right=LicenseId(id='GPL-3.0-only'),
        )

    def test_lowercase_or(self) -> None:
        """Test lowercase or."""
        result = parse('MIT or Apache-2.0')
        assert result == Or(
            left=LicenseId(id='MIT'),
            right=LicenseId(id='Apache-2.0'),
        )


# ── Operator precedence ─────────────────────────────────────────────────


class TestPrecedence:
    """Tests for precedence."""

    def test_and_binds_tighter_than_or(self) -> None:
        # "LGPL-2.1-only OR BSD-3-Clause AND MIT"
        # should parse as: LGPL-2.1-only OR (BSD-3-Clause AND MIT)
        """Test and binds tighter than or."""
        result = parse('LGPL-2.1-only OR BSD-3-Clause AND MIT')
        assert result == Or(
            left=LicenseId(id='LGPL-2.1-only'),
            right=And(
                left=LicenseId(id='BSD-3-Clause'),
                right=LicenseId(id='MIT'),
            ),
        )

    def test_with_binds_tighter_than_and(self) -> None:
        # "GPL-2.0+ WITH Bison-exception-2.2 AND MIT"
        # should parse as: (GPL-2.0+ WITH Bison-exception-2.2) AND MIT
        """Test with binds tighter than and."""
        result = parse('GPL-2.0+ WITH Bison-exception-2.2 AND MIT')
        assert result == And(
            left=With(
                license=LicenseId(id='GPL-2.0', or_later=True),
                exception='Bison-exception-2.2',
            ),
            right=LicenseId(id='MIT'),
        )

    def test_with_binds_tighter_than_or(self) -> None:
        # "MIT OR GPL-2.0+ WITH Bison-exception-2.2"
        # should parse as: MIT OR (GPL-2.0+ WITH Bison-exception-2.2)
        """Test with binds tighter than or."""
        result = parse('MIT OR GPL-2.0+ WITH Bison-exception-2.2')
        assert result == Or(
            left=LicenseId(id='MIT'),
            right=With(
                license=LicenseId(id='GPL-2.0', or_later=True),
                exception='Bison-exception-2.2',
            ),
        )


# ── Parentheses ──────────────────────────────────────────────────────────


class TestParentheses:
    """Tests for parentheses."""

    def test_override_precedence(self) -> None:
        # "MIT AND (LGPL-2.1-or-later OR BSD-3-Clause)"
        """Test override precedence."""
        result = parse('MIT AND (LGPL-2.1-or-later OR BSD-3-Clause)')
        assert result == And(
            left=LicenseId(id='MIT'),
            right=Or(
                left=LicenseId(id='LGPL-2.1-or-later'),
                right=LicenseId(id='BSD-3-Clause'),
            ),
        )

    def test_nested_parentheses(self) -> None:
        """Test nested parentheses."""
        result = parse('(MIT OR (Apache-2.0 AND BSD-3-Clause))')
        assert result == Or(
            left=LicenseId(id='MIT'),
            right=And(
                left=LicenseId(id='Apache-2.0'),
                right=LicenseId(id='BSD-3-Clause'),
            ),
        )

    def test_redundant_parentheses(self) -> None:
        """Test redundant parentheses."""
        result = parse('((MIT))')
        assert result == LicenseId(id='MIT')

    def test_complex_nested(self) -> None:
        """Test complex nested."""
        expr = '(MIT OR Apache-2.0) AND (GPL-3.0-only OR BSD-2-Clause)'
        result = parse(expr)
        assert result == And(
            left=Or(
                left=LicenseId(id='MIT'),
                right=LicenseId(id='Apache-2.0'),
            ),
            right=Or(
                left=LicenseId(id='GPL-3.0-only'),
                right=LicenseId(id='BSD-2-Clause'),
            ),
        )


# ── Real-world expressions ───────────────────────────────────────────────


class TestRealWorldExpressions:
    """Tests for real World Expressions."""

    def test_rust_dual_license(self) -> None:
        # Common in Rust crates.
        """Test rust dual license."""
        result = parse('MIT OR Apache-2.0')
        assert isinstance(result, Or)
        assert license_ids(result) == {'MIT', 'Apache-2.0'}

    def test_perl_license(self) -> None:
        """Test perl license."""
        result = parse('Artistic-2.0 OR GPL-1.0-or-later')
        assert isinstance(result, Or)

    def test_linux_kernel(self) -> None:
        """Test linux kernel."""
        result = parse('GPL-2.0-only')
        assert result == LicenseId(id='GPL-2.0-only')

    def test_gcc_runtime_exception(self) -> None:
        """Test gcc runtime exception."""
        result = parse('GPL-3.0-or-later WITH GCC-exception-3.1')
        assert isinstance(result, With)
        assert result.exception == 'GCC-exception-3.1'

    def test_complex_multi_license(self) -> None:
        """Test complex multi license."""
        expr = 'LGPL-2.1-only OR BSD-3-Clause AND MIT'
        result = parse(expr)
        # AND binds tighter: LGPL-2.1-only OR (BSD-3-Clause AND MIT)
        assert isinstance(result, Or)
        assert isinstance(result.right, And)

    def test_openssl(self) -> None:
        """Test openssl."""
        result = parse('OpenSSL OR Apache-2.0')
        assert license_ids(result) == {'OpenSSL', 'Apache-2.0'}

    def test_qt_license(self) -> None:
        """Test qt license."""
        result = parse('LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only')
        assert license_ids(result) == {
            'LGPL-3.0-only',
            'GPL-2.0-only',
            'GPL-3.0-only',
        }


# ── license_ids() ────────────────────────────────────────────────────────


class TestLicenseIds:
    """Tests for license Ids."""

    def test_single(self) -> None:
        """Test single."""
        assert license_ids(parse('MIT')) == {'MIT'}

    def test_or(self) -> None:
        """Test or."""
        assert license_ids(parse('MIT OR Apache-2.0')) == {'MIT', 'Apache-2.0'}

    def test_and(self) -> None:
        """Test and."""
        assert license_ids(parse('MIT AND BSD-3-Clause')) == {'MIT', 'BSD-3-Clause'}

    def test_with(self) -> None:
        # WITH exception — only the base license ID is collected.
        """Test with."""
        assert license_ids(parse('GPL-2.0+ WITH Bison-exception-2.2')) == {'GPL-2.0'}

    def test_complex(self) -> None:
        """Test complex."""
        expr = '(MIT OR Apache-2.0) AND (GPL-3.0-only OR BSD-2-Clause)'
        assert license_ids(parse(expr)) == {
            'MIT',
            'Apache-2.0',
            'GPL-3.0-only',
            'BSD-2-Clause',
        }

    def test_license_ref(self) -> None:
        """Test license ref."""
        assert license_ids(parse('LicenseRef-Custom')) == {'LicenseRef-Custom'}

    def test_license_ref_with_document_ref(self) -> None:
        """Test license ref with document ref."""
        result = license_ids(parse('DocumentRef-foo:LicenseRef-Bar'))
        assert result == {'DocumentRef-foo:LicenseRef-Bar'}

    def test_or_later_id_without_plus(self) -> None:
        # The ID string is collected without the + suffix.
        """Test or later id without plus."""
        assert license_ids(parse('GPL-2.0+')) == {'GPL-2.0'}


# ── __str__ round-trip ───────────────────────────────────────────────────


class TestStrRoundTrip:
    """Tests for str Round Trip."""

    def test_simple_id(self) -> None:
        """Test simple id."""
        assert str(parse('MIT')) == 'MIT'

    def test_or_later(self) -> None:
        """Test or later."""
        assert str(parse('GPL-2.0+')) == 'GPL-2.0+'

    def test_with(self) -> None:
        """Test with."""
        assert str(parse('GPL-2.0+ WITH Bison-exception-2.2')) == 'GPL-2.0+ WITH Bison-exception-2.2'

    def test_and(self) -> None:
        """Test and."""
        assert str(parse('MIT AND BSD-3-Clause')) == 'MIT AND BSD-3-Clause'

    def test_or(self) -> None:
        """Test or."""
        assert str(parse('MIT OR Apache-2.0')) == 'MIT OR Apache-2.0'

    def test_and_with_or_child_gets_parens(self) -> None:
        # AND's __str__ should parenthesize OR children.
        """Test and with or child gets parens."""
        node = And(
            left=Or(left=LicenseId('MIT'), right=LicenseId('ISC')),
            right=LicenseId('BSD-3-Clause'),
        )
        assert str(node) == '(MIT OR ISC) AND BSD-3-Clause'

    def test_license_ref(self) -> None:
        """Test license ref."""
        assert str(parse('LicenseRef-Custom')) == 'LicenseRef-Custom'

    def test_license_ref_with_doc(self) -> None:
        """Test license ref with doc."""
        assert str(parse('DocumentRef-foo:LicenseRef-Bar')) == 'DocumentRef-foo:LicenseRef-Bar'


# ── Error handling ───────────────────────────────────────────────────────


class TestParseErrors:
    """Tests for parse Errors."""

    def test_empty_string(self) -> None:
        """Test empty string."""
        with pytest.raises(ParseError, match='empty expression'):
            parse('')

    def test_whitespace_only(self) -> None:
        """Test whitespace only."""
        with pytest.raises(ParseError, match='empty expression'):
            parse('   ')

    def test_unexpected_rparen(self) -> None:
        """Test unexpected rparen."""
        with pytest.raises(ParseError):
            parse(')')

    def test_unmatched_lparen(self) -> None:
        """Test unmatched lparen."""
        with pytest.raises(ParseError):
            parse('(MIT')

    def test_trailing_operator(self) -> None:
        """Test trailing operator."""
        with pytest.raises(ParseError):
            parse('MIT AND')

    def test_leading_operator(self) -> None:
        """Test leading operator."""
        with pytest.raises(ParseError):
            parse('AND MIT')

    def test_double_operator(self) -> None:
        """Test double operator."""
        with pytest.raises(ParseError):
            parse('MIT AND AND BSD-3-Clause')

    def test_unexpected_character(self) -> None:
        """Test unexpected character."""
        with pytest.raises(ParseError, match='unexpected character'):
            parse('MIT @ BSD')

    def test_trailing_tokens(self) -> None:
        """Test trailing tokens."""
        with pytest.raises(ParseError, match='unexpected token'):
            parse('MIT BSD')

    def test_error_has_position(self) -> None:
        """Test error has position."""
        with pytest.raises(ParseError) as exc_info:
            parse('MIT AND')
        assert exc_info.value.position > 0
        assert exc_info.value.expression == 'MIT AND'

    def test_error_has_caret(self) -> None:
        """Test error has caret."""
        with pytest.raises(ParseError) as exc_info:
            parse('MIT @')
        assert '^' in str(exc_info.value)


# ── SPDX v3.0.1 spec edge cases ─────────────────────────────────────────


class TestSpdxV301SpecEdgeCases:
    """Edge cases derived from SPDX Specification v3.0.1 Annex B."""

    # -- Case sensitivity: operators must be all-upper or all-lower --

    def test_mixed_case_and_rejected(self) -> None:
        """'And' is neither 'AND' nor 'and' — must be treated as an ID."""
        with pytest.raises(ParseError):
            parse('MIT And BSD-3-Clause')

    def test_mixed_case_or_rejected(self) -> None:
        """Test mixed case or rejected."""
        with pytest.raises(ParseError):
            parse('MIT Or BSD-3-Clause')

    def test_mixed_case_with_rejected(self) -> None:
        """Test mixed case with rejected."""
        with pytest.raises(ParseError):
            parse('Apache-2.0 With LLVM-exception')

    # -- No whitespace between license-id and + --

    def test_space_before_plus_rejected(self) -> None:
        """'GPL-2.0 +' has whitespace before + — invalid per spec."""
        with pytest.raises(ParseError):
            parse('GPL-2.0 +')

    # -- AdditionRef with DocumentRef prefix in WITH --

    def test_addition_ref_with_document_ref_in_with(self) -> None:
        """Test addition ref with document ref in with."""
        result = parse('MIT WITH DocumentRef-foo:AdditionRef-bar')
        assert isinstance(result, With)
        assert result.exception == 'DocumentRef-foo:AdditionRef-bar'

    # -- LicenseRef examples from the spec --

    def test_license_ref_numeric(self) -> None:
        """LicenseRef-23 from the spec examples."""
        result = parse('LicenseRef-23')
        assert isinstance(result, LicenseRef)
        assert result.ref == 'LicenseRef-23'

    def test_license_ref_mit_style(self) -> None:
        """Test license ref mit style."""
        result = parse('LicenseRef-MIT-Style-1')
        assert isinstance(result, LicenseRef)

    def test_document_ref_license_ref_from_spec(self) -> None:
        """DocumentRef-spdx-tool-1.2:LicenseRef-MIT-Style-2 from spec."""
        result = parse('DocumentRef-spdx-tool-1.2:LicenseRef-MIT-Style-2')
        assert isinstance(result, LicenseRef)
        assert result.document_ref == 'DocumentRef-spdx-tool-1.2'
        assert result.ref == 'LicenseRef-MIT-Style-2'

    # -- CDDL-1.0+ from spec example --

    def test_cddl_or_later(self) -> None:
        """Test cddl or later."""
        result = parse('CDDL-1.0+')
        assert result == LicenseId(id='CDDL-1.0', or_later=True)

    # -- Lowercase operators with correct precedence --

    def test_lowercase_or_and_precedence(self) -> None:
        """'MIT or Apache-2.0 and BSD-3-Clause' — and binds tighter."""
        result = parse('MIT or Apache-2.0 and BSD-3-Clause')
        assert result == Or(
            left=LicenseId(id='MIT'),
            right=And(
                left=LicenseId(id='Apache-2.0'),
                right=LicenseId(id='BSD-3-Clause'),
            ),
        )

    # -- Spec example: precedence --

    def test_spec_precedence_example(self) -> None:
        """From spec: 'LGPL-2.1-only OR BSD-3-Clause AND MIT'."""
        result = parse('LGPL-2.1-only OR BSD-3-Clause AND MIT')
        assert result == Or(
            left=LicenseId(id='LGPL-2.1-only'),
            right=And(
                left=LicenseId(id='BSD-3-Clause'),
                right=LicenseId(id='MIT'),
            ),
        )

    def test_spec_parens_override_example(self) -> None:
        """From spec: 'MIT AND (LGPL-2.1-or-later OR BSD-3-Clause)'."""
        result = parse('MIT AND (LGPL-2.1-or-later OR BSD-3-Clause)')
        assert result == And(
            left=LicenseId(id='MIT'),
            right=Or(
                left=LicenseId(id='LGPL-2.1-or-later'),
                right=LicenseId(id='BSD-3-Clause'),
            ),
        )

    # -- WITH with or-later (from spec: GPL-2.0-or-later WITH Bison-exception-2.2) --

    def test_spec_with_example(self) -> None:
        """Test spec with example."""
        result = parse('GPL-2.0-or-later WITH Bison-exception-2.2')
        assert result == With(
            license=LicenseId(id='GPL-2.0-or-later', or_later=False),
            exception='Bison-exception-2.2',
        )

    # -- Three-way OR from spec --

    def test_three_way_or(self) -> None:
        """Test three way or."""
        result = parse('LGPL-2.1-only OR MIT OR BSD-3-Clause')
        ids = license_ids(result)
        assert ids == {'LGPL-2.1-only', 'MIT', 'BSD-3-Clause'}
