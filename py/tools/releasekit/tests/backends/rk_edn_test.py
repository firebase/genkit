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

r"""Comprehensive tests for the EDN / Clojure reader.

Covers the full EDN specification and Clojure reader extensions:

EDN built-in elements:
- nil, true, false
- strings (with all escape sequences including \\uNNNN)
- characters (\\c, \\newline, \\return, \\space, \\tab, \\uNNNN)
- symbols, keywords
- integers, bigints (N suffix), floats, bigdecimals (M suffix), ratios
- lists, vectors, maps, sets
- #inst, #uuid tagged literals
- generic tagged literals
- comments, discard (#_)

Clojure reader extensions:
- regex #"..."
- metadata ^
- quote '
- deref @
- syntax-quote `
- unquote ~, unquote-splicing ~@
- var quote #'
- anonymous functions #(...)
- reader conditionals #?(...), #?@(...)
- namespaced maps #:ns{...}, #::ns{...}
- span tracking for string rewrites
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from uuid import UUID

import pytest
from releasekit.backends.workspace._edn import EdnReader, Tagged, parse_edn

# EDN built-in elements


# nil, booleans


class TestNilAndBooleans:
    """Tests for nil, true, false."""

    def test_nil(self) -> None:
        """Nil."""
        assert parse_edn('nil') is None

    def test_true(self) -> None:
        """True."""
        assert parse_edn('true') is True

    def test_false(self) -> None:
        """False."""
        assert parse_edn('false') is False

    def test_nil_with_whitespace(self) -> None:
        """Nil with whitespace."""
        assert parse_edn('  nil  ') is None

    def test_true_with_comment(self) -> None:
        """True with comment."""
        assert parse_edn('; comment\ntrue') is True


# Strings


class TestStrings:
    """Tests for EDN string parsing with all escape sequences."""

    def test_empty_string(self) -> None:
        """Empty string."""
        assert parse_edn('""') == ''

    def test_simple_string(self) -> None:
        """Simple string."""
        assert parse_edn('"hello"') == 'hello'

    def test_string_with_spaces(self) -> None:
        """String with spaces."""
        assert parse_edn('"hello world"') == 'hello world'

    def test_multiline_string(self) -> None:
        """Multiline string."""
        assert parse_edn('"line1\nline2"') == 'line1\nline2'

    def test_escape_tab(self) -> None:
        """Escape tab."""
        assert parse_edn(r'"a\tb"') == 'a\tb'

    def test_escape_return(self) -> None:
        """Escape return."""
        assert parse_edn(r'"a\rb"') == 'a\rb'

    def test_escape_newline(self) -> None:
        """Escape newline."""
        assert parse_edn(r'"a\nb"') == 'a\nb'

    def test_escape_backslash(self) -> None:
        """Escape backslash."""
        assert parse_edn(r'"a\\b"') == 'a\\b'

    def test_escape_double_quote(self) -> None:
        """Escape double quote."""
        assert parse_edn(r'"a\"b"') == 'a"b'

    def test_escape_backspace(self) -> None:
        """Escape backspace."""
        assert parse_edn(r'"a\bb"') == 'a\bb'

    def test_escape_formfeed(self) -> None:
        """Escape formfeed."""
        assert parse_edn(r'"a\fb"') == 'a\fb'

    def test_unicode_escape(self) -> None:
        """Unicode escape."""
        assert parse_edn(r'"caf\u00e9"') == 'caf\u00e9'

    def test_unicode_escape_cjk(self) -> None:
        """Unicode escape cjk."""
        assert parse_edn(r'"\u4e16\u754c"') == '\u4e16\u754c'

    def test_unterminated_string_raises(self) -> None:
        """Unterminated string raises."""
        with pytest.raises(ValueError, match='Unterminated string'):
            parse_edn('"hello')

    def test_unterminated_unicode_escape_raises(self) -> None:
        """Unterminated unicode escape raises."""
        with pytest.raises(ValueError, match='Unterminated'):
            parse_edn(r'"hello\u00"')

    def test_invalid_unicode_escape_raises(self) -> None:
        """Invalid unicode escape raises."""
        with pytest.raises(ValueError, match='Invalid unicode'):
            parse_edn(r'"hello\uzzzz"')


# Characters


class TestCharacters:
    """Tests for EDN character literals."""

    def test_single_char(self) -> None:
        """Single char."""
        assert parse_edn('\\a') == 'a'

    def test_char_z(self) -> None:
        """Char z."""
        assert parse_edn('\\z') == 'z'

    def test_char_digit(self) -> None:
        """Char digit."""
        assert parse_edn('\\5') == '5'

    def test_named_newline(self) -> None:
        """Named newline."""
        assert parse_edn('\\newline') == '\n'

    def test_named_return(self) -> None:
        """Named return."""
        assert parse_edn('\\return') == '\r'

    def test_named_space(self) -> None:
        """Named space."""
        assert parse_edn('\\space') == ' '

    def test_named_tab(self) -> None:
        """Named tab."""
        assert parse_edn('\\tab') == '\t'

    def test_named_backspace(self) -> None:
        """Named backspace."""
        assert parse_edn('\\backspace') == '\b'

    def test_named_formfeed(self) -> None:
        """Named formfeed."""
        assert parse_edn('\\formfeed') == '\f'

    def test_unicode_char(self) -> None:
        """Unicode char."""
        assert parse_edn('\\u0041') == 'A'

    def test_unicode_char_euro(self) -> None:
        """Unicode char euro."""
        assert parse_edn('\\u20AC') == '\u20ac'

    def test_char_in_vector(self) -> None:
        """Char in vector."""
        result = parse_edn('[\\a \\b \\c]')
        assert result == ['a', 'b', 'c']

    def test_unknown_named_char_raises(self) -> None:
        """Unknown named char raises."""
        with pytest.raises(ValueError, match='Unknown character'):
            parse_edn('\\foobar')

    def test_eof_after_backslash_raises(self) -> None:
        """Eof after backslash raises."""
        with pytest.raises(ValueError, match='Unexpected end'):
            parse_edn('\\')


# Symbols


class TestSymbols:
    """Tests for EDN symbols."""

    def test_simple_symbol(self) -> None:
        """Simple symbol."""
        assert parse_edn('foo') == 'foo'

    def test_namespaced_symbol(self) -> None:
        """Namespaced symbol."""
        assert parse_edn('my.ns/bar') == 'my.ns/bar'

    def test_symbol_with_special_chars(self) -> None:
        """Symbol with special chars."""
        assert parse_edn('my-fn!') == 'my-fn!'

    def test_symbol_with_question_mark(self) -> None:
        """Symbol with question mark."""
        assert parse_edn('empty?') == 'empty?'

    def test_symbol_plus(self) -> None:
        """Symbol plus."""
        assert parse_edn('+') == '+'

    def test_symbol_minus(self) -> None:
        # '-' alone is a symbol, not a number.
        """Symbol minus."""
        assert parse_edn('-') == '-'

    def test_slash_symbol(self) -> None:
        """Slash symbol."""
        assert parse_edn('/') == '/'

    def test_symbol_with_dots(self) -> None:
        """Symbol with dots."""
        assert parse_edn('com.example.core') == 'com.example.core'


# Keywords


class TestKeywords:
    """Tests for EDN keywords."""

    def test_simple_keyword(self) -> None:
        """Simple keyword."""
        assert parse_edn(':foo') == ':foo'

    def test_namespaced_keyword(self) -> None:
        """Namespaced keyword."""
        assert parse_edn(':my.ns/bar') == ':my.ns/bar'

    def test_keyword_in_map(self) -> None:
        """Keyword in map."""
        result = parse_edn('{:a 1 :b 2}')
        assert result == {':a': 1, ':b': 2}


# Integers


class TestIntegers:
    """Tests for EDN integer parsing."""

    def test_zero(self) -> None:
        """Zero."""
        assert parse_edn('0') == 0

    def test_positive(self) -> None:
        """Positive."""
        assert parse_edn('42') == 42

    def test_negative(self) -> None:
        """Negative."""
        assert parse_edn('-7') == -7

    def test_positive_with_plus(self) -> None:
        """Positive with plus."""
        assert parse_edn('+42') == 42

    def test_large_integer(self) -> None:
        """Large integer."""
        assert parse_edn('9999999999') == 9999999999

    def test_negative_zero(self) -> None:
        """Negative zero."""
        assert parse_edn('-0') == 0

    def test_bigint_suffix(self) -> None:
        """Bigint suffix."""
        result = parse_edn('42N')
        assert result == 42
        assert isinstance(result, int)

    def test_bigint_large(self) -> None:
        """Bigint large."""
        result = parse_edn('999999999999999999999999999999N')
        assert result == 999999999999999999999999999999
        assert isinstance(result, int)

    def test_bigint_negative(self) -> None:
        """Bigint negative."""
        result = parse_edn('-100N')
        assert result == -100


# Floating-point numbers


class TestFloats:
    """Tests for EDN floating-point parsing."""

    def test_simple_float(self) -> None:
        """Simple float."""
        assert parse_edn('3.14') == pytest.approx(3.14)

    def test_negative_float(self) -> None:
        """Negative float."""
        assert parse_edn('-2.5') == pytest.approx(-2.5)

    def test_float_with_exponent(self) -> None:
        """Float with exponent."""
        assert parse_edn('1.5e10') == pytest.approx(1.5e10)

    def test_float_with_negative_exponent(self) -> None:
        """Float with negative exponent."""
        assert parse_edn('1.5e-3') == pytest.approx(1.5e-3)

    def test_float_with_capital_e(self) -> None:
        """Float with capital e."""
        assert parse_edn('1.5E10') == pytest.approx(1.5e10)

    def test_bigdecimal_suffix(self) -> None:
        """Bigdecimal suffix."""
        result = parse_edn('3.14M')
        assert result == Decimal('3.14')
        assert isinstance(result, Decimal)

    def test_bigdecimal_integer_form(self) -> None:
        """Bigdecimal integer form."""
        result = parse_edn('42M')
        assert result == Decimal('42')
        assert isinstance(result, Decimal)

    def test_bigdecimal_negative(self) -> None:
        """Bigdecimal negative."""
        result = parse_edn('-1.5M')
        assert result == Decimal('-1.5')


# Ratios


class TestRatios:
    """Tests for EDN ratio parsing."""

    def test_simple_ratio(self) -> None:
        """Simple ratio."""
        result = parse_edn('22/7')
        assert result == Fraction(22, 7)
        assert isinstance(result, Fraction)

    def test_ratio_reduces(self) -> None:
        """Ratio reduces."""
        result = parse_edn('4/2')
        assert result == Fraction(2, 1)

    def test_negative_ratio(self) -> None:
        """Negative ratio."""
        result = parse_edn('-1/3')
        assert result == Fraction(-1, 3)

    def test_namespaced_symbol_not_ratio(self) -> None:
        # my.ns/foo should be a symbol, not a ratio.
        """Namespaced symbol not ratio."""
        result = parse_edn('my.ns/foo')
        assert result == 'my.ns/foo'
        assert isinstance(result, str)


# Lists


class TestLists:
    """Tests for EDN list parsing."""

    def test_empty_list(self) -> None:
        """Empty list."""
        assert parse_edn('()') == []

    def test_list_of_ints(self) -> None:
        """List of ints."""
        assert parse_edn('(1 2 3)') == [1, 2, 3]

    def test_nested_list(self) -> None:
        """Nested list."""
        assert parse_edn('(1 (2 3) 4)') == [1, [2, 3], 4]

    def test_heterogeneous_list(self) -> None:
        """Heterogeneous list."""
        result = parse_edn('(1 "two" :three)')
        assert result == [1, 'two', ':three']

    def test_unterminated_list_raises(self) -> None:
        """Unterminated list raises."""
        with pytest.raises(ValueError, match='Unterminated list'):
            parse_edn('(1 2 3')


# Vectors


class TestVectors:
    """Tests for EDN vector parsing."""

    def test_empty_vector(self) -> None:
        """Empty vector."""
        assert parse_edn('[]') == []

    def test_vector_of_strings(self) -> None:
        """Vector of strings."""
        assert parse_edn('["src" "resources"]') == ['src', 'resources']

    def test_nested_vector(self) -> None:
        """Nested vector."""
        assert parse_edn('[[1 2] [3 4]]') == [[1, 2], [3, 4]]

    def test_unterminated_vector_raises(self) -> None:
        """Unterminated vector raises."""
        with pytest.raises(ValueError, match='Unterminated vector'):
            parse_edn('[1 2 3')


# Maps


class TestMaps:
    """Tests for EDN map parsing."""

    def test_empty_map(self) -> None:
        """Empty map."""
        assert parse_edn('{}') == {}

    def test_keyword_keys(self) -> None:
        """Keyword keys."""
        result = parse_edn('{:name "hello" :version "1.0"}')
        assert result == {':name': 'hello', ':version': '1.0'}

    def test_nested_map(self) -> None:
        """Nested map."""
        result = parse_edn('{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}')
        assert isinstance(result, dict)
        deps = result[':deps']  # type: ignore[index]
        assert isinstance(deps, dict)
        assert 'org.clojure/clojure' in deps

    def test_commas_as_whitespace(self) -> None:
        """Commas as whitespace."""
        result = parse_edn('{:a 1, :b 2}')
        assert result == {':a': 1, ':b': 2}

    def test_heterogeneous_keys(self) -> None:
        """Heterogeneous keys."""
        result = parse_edn('{:a 1, "foo" :bar}')
        assert result[':a'] == 1  # type: ignore[index]
        assert result['foo'] == ':bar'  # type: ignore[index]

    def test_unterminated_map_raises(self) -> None:
        """Unterminated map raises."""
        with pytest.raises(ValueError, match='Unterminated map'):
            parse_edn('{:a 1')


# Sets


class TestSets:
    """Tests for EDN set parsing."""

    def test_empty_set(self) -> None:
        """Empty set."""
        assert parse_edn('#{}') == set()

    def test_set_of_ints(self) -> None:
        """Set of ints."""
        result = parse_edn('#{1 2 3}')
        assert isinstance(result, set)
        assert result == {1, 2, 3}

    def test_set_of_strings(self) -> None:
        """Set of strings."""
        result = parse_edn('#{"a" "b" "c"}')
        assert result == {'a', 'b', 'c'}

    def test_unterminated_set_raises(self) -> None:
        """Unterminated set raises."""
        with pytest.raises(ValueError, match='Unterminated set'):
            parse_edn('#{1 2 3')


# Comments and whitespace


class TestCommentsAndWhitespace:
    """Tests for comment and whitespace handling."""

    def test_line_comment(self) -> None:
        """Line comment."""
        result = parse_edn('{;; this is a comment\n:name "hello" ; inline\n}')
        assert result == {':name': 'hello'}

    def test_multiple_comments(self) -> None:
        """Multiple comments."""
        result = parse_edn('; first\n; second\n42')
        assert result == 42

    def test_commas_are_whitespace(self) -> None:
        """Commas are whitespace."""
        result = parse_edn('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_mixed_whitespace(self) -> None:
        """Mixed whitespace."""
        result = parse_edn('  \t\n\r  42  ')
        assert result == 42


# Discard


class TestDiscard:
    """Tests for #_ discard form."""

    def test_discard_simple(self) -> None:
        """Discard simple."""
        result = parse_edn('#_ {:ignored true} {:kept true}')
        assert result == {':kept': True}

    def test_discard_in_vector(self) -> None:
        """Discard in vector."""
        result = parse_edn('[1 #_ 2 3]')
        assert result == [1, 3]

    def test_discard_nested(self) -> None:
        """Discard nested."""
        result = parse_edn('#_ [1 2 3] "hello"')
        assert result == 'hello'

    def test_discard_multiple(self) -> None:
        """Discard multiple."""
        result = parse_edn('[1 #_ 2 #_ 3 4]')
        assert result == [1, 4]


# #inst tagged literal


class TestInst:
    """Tests for #inst tagged literal."""

    def test_inst_utc_z(self) -> None:
        """Inst utc z."""
        result = parse_edn('#inst "1985-04-12T23:20:50.52Z"')
        assert isinstance(result, datetime)
        assert result.year == 1985
        assert result.month == 4
        assert result.day == 12

    def test_inst_with_offset(self) -> None:
        """Inst with offset."""
        result = parse_edn('#inst "2023-01-15T10:30:00+05:30"')
        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_inst_date_only(self) -> None:
        """Inst date only."""
        result = parse_edn('#inst "2023-06-15"')
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 6
        assert result.day == 15

    def test_inst_invalid_raises(self) -> None:
        """Inst invalid raises."""
        with pytest.raises(ValueError, match='Invalid #inst'):
            parse_edn('#inst "not-a-date"')

    def test_inst_non_string_raises(self) -> None:
        """Inst non string raises."""
        with pytest.raises(ValueError, match='#inst requires a string'):
            parse_edn('#inst 42')


# #uuid tagged literal


class TestUuid:
    """Tests for #uuid tagged literal."""

    def test_uuid_parses(self) -> None:
        """Uuid parses."""
        result = parse_edn('#uuid "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"')
        assert isinstance(result, UUID)
        assert str(result) == 'f81d4fae-7dec-11d0-a765-00a0c91e6bf6'

    def test_uuid_v4(self) -> None:
        """Uuid v4."""
        result = parse_edn('#uuid "550e8400-e29b-41d4-a716-446655440000"')
        assert isinstance(result, UUID)

    def test_uuid_invalid_raises(self) -> None:
        """Uuid invalid raises."""
        with pytest.raises(ValueError, match='Invalid #uuid'):
            parse_edn('#uuid "not-a-uuid"')

    def test_uuid_non_string_raises(self) -> None:
        """Uuid non string raises."""
        with pytest.raises(ValueError, match='#uuid requires a string'):
            parse_edn('#uuid 42')


# Generic tagged literals


class TestTaggedLiterals:
    """Tests for generic tagged literals."""

    def test_unknown_tag_returns_tagged(self) -> None:
        """Unknown tag returns tagged."""
        result = parse_edn('#myapp/Person {:first "Fred" :last "Mertz"}')
        assert isinstance(result, Tagged)
        assert result.tag == 'myapp/Person'
        assert result.value == {':first': 'Fred', ':last': 'Mertz'}

    def test_tagged_equality(self) -> None:
        """Tagged equality."""
        a = Tagged('foo', 42)
        b = Tagged('foo', 42)
        assert a == b

    def test_tagged_inequality(self) -> None:
        """Tagged inequality."""
        a = Tagged('foo', 42)
        b = Tagged('bar', 42)
        assert a != b

    def test_tagged_repr(self) -> None:
        """Tagged repr."""
        t = Tagged('foo', 42)
        assert repr(t) == "Tagged('foo', 42)"

    def test_tagged_hash(self) -> None:
        """Tagged hash."""
        a = Tagged('foo', 42)
        b = Tagged('foo', 42)
        assert hash(a) == hash(b)

    def test_tagged_not_equal_to_non_tagged(self) -> None:
        """Tagged not equal to non tagged."""
        t = Tagged('foo', 42)
        assert t != 42


# Clojure reader extensions


# Regex #"..."


class TestRegex:
    """Tests for Clojure regex literals."""

    def test_simple_regex(self) -> None:
        """Simple regex."""
        result = parse_edn(r'#"\d+"')
        assert isinstance(result, re.Pattern)
        assert result.pattern == r'\d+'

    def test_regex_with_escapes(self) -> None:
        """Regex with escapes."""
        result = parse_edn(r'#"\w+\s+"')
        assert isinstance(result, re.Pattern)
        assert result.pattern == r'\w+\s+'

    def test_regex_matches(self) -> None:
        """Regex matches."""
        result = parse_edn(r'#"hello"')
        assert result.match('hello') is not None  # type: ignore[union-attr]

    def test_regex_with_groups(self) -> None:
        """Regex with groups."""
        result = parse_edn(r'#"(\d+)-(\d+)"')
        m = result.match('123-456')  # type: ignore[union-attr]
        assert m is not None
        assert m.group(1) == '123'
        assert m.group(2) == '456'

    def test_unterminated_regex_raises(self) -> None:
        """Unterminated regex raises."""
        with pytest.raises(ValueError, match='Unterminated regex'):
            parse_edn('#"hello')

    def test_regex_in_vector(self) -> None:
        """Regex in vector."""
        result = parse_edn(r'[#"\d+" #"\w+"]')
        assert len(result) == 2  # type: ignore[arg-type]
        assert all(isinstance(r, re.Pattern) for r in result)  # type: ignore[arg-type]


# Metadata ^


class TestMetadata:
    """Tests for Clojure metadata reader macro."""

    def test_metadata_map_discarded(self) -> None:
        """Metadata map discarded."""
        result = parse_edn('^{:private true} foo')
        assert result == 'foo'

    def test_metadata_keyword_discarded(self) -> None:
        """Metadata keyword discarded."""
        result = parse_edn('^:dynamic *var*')
        assert result == '*var*'

    def test_metadata_type_hint_discarded(self) -> None:
        """Metadata type hint discarded."""
        result = parse_edn('^String name')
        assert result == 'name'

    def test_metadata_on_vector(self) -> None:
        """Metadata on vector."""
        result = parse_edn('^:const [1 2 3]')
        assert result == [1, 2, 3]

    def test_nested_metadata(self) -> None:
        """Nested metadata."""
        result = parse_edn('^:a ^:b foo')
        assert result == 'foo'


# Quote '


class TestQuote:
    """Tests for Clojure quote reader macro."""

    def test_quote_symbol(self) -> None:
        """Quote symbol."""
        result = parse_edn("'foo")
        assert result == ['quote', 'foo']

    def test_quote_list(self) -> None:
        """Quote list."""
        result = parse_edn("'(1 2 3)")
        assert result == ['quote', [1, 2, 3]]

    def test_quote_in_vector(self) -> None:
        """Quote in vector."""
        result = parse_edn("['a 'b]")
        assert result == [['quote', 'a'], ['quote', 'b']]


# Deref @


class TestDeref:
    """Tests for Clojure deref reader macro."""

    def test_deref_symbol(self) -> None:
        """Deref symbol."""
        result = parse_edn('@my-atom')
        assert result == ['deref', 'my-atom']

    def test_deref_in_list(self) -> None:
        """Deref in list."""
        result = parse_edn('(@state)')
        assert result == [['deref', 'state']]


# Syntax-quote, unquote, unquote-splicing


class TestSyntaxQuote:
    """Tests for Clojure syntax-quote, unquote, unquote-splicing."""

    def test_syntax_quote(self) -> None:
        """Syntax quote."""
        result = parse_edn('`foo')
        assert result == ['syntax-quote', 'foo']

    def test_unquote(self) -> None:
        """Unquote."""
        result = parse_edn('~foo')
        assert result == ['unquote', 'foo']

    def test_unquote_splicing(self) -> None:
        """Unquote splicing."""
        result = parse_edn('~@foo')
        assert result == ['unquote-splicing', 'foo']

    def test_syntax_quote_with_unquote(self) -> None:
        """Syntax quote with unquote."""
        result = parse_edn('`(foo ~bar)')
        assert result == ['syntax-quote', ['foo', ['unquote', 'bar']]]

    def test_syntax_quote_with_splicing(self) -> None:
        """Syntax quote with splicing."""
        result = parse_edn('`(foo ~@items)')
        assert result == ['syntax-quote', ['foo', ['unquote-splicing', 'items']]]


# Var quote #'


class TestVarQuote:
    """Tests for Clojure var quote reader macro."""

    def test_var_quote(self) -> None:
        """Var quote."""
        result = parse_edn("#'my-fn")
        assert result == ['var', 'my-fn']

    def test_var_quote_namespaced(self) -> None:
        """Var quote namespaced."""
        result = parse_edn("#'clojure.core/map")
        assert result == ['var', 'clojure.core/map']


# Anonymous functions #(...)


class TestAnonFn:
    """Tests for Clojure anonymous function reader macro."""

    def test_anon_fn_single_arg(self) -> None:
        """Anon fn single arg."""
        result = parse_edn('#(inc %)')
        assert isinstance(result, list)
        assert result[0] == 'fn*'
        # Should have ['%1'] as params.
        assert '%1' in result[1]  # type: ignore[operator]
        # Body should contain 'inc' and '%'.
        assert 'inc' in result
        assert '%' in result

    def test_anon_fn_multiple_args(self) -> None:
        """Anon fn multiple args."""
        result = parse_edn('#(+ %1 %2)')
        assert result[0] == 'fn*'  # type: ignore[index]
        params = result[1]  # type: ignore[index]
        assert '%1' in params
        assert '%2' in params

    def test_anon_fn_rest_args(self) -> None:
        """Anon fn rest args."""
        result = parse_edn('#(apply str %&)')
        assert result[0] == 'fn*'  # type: ignore[index]
        params = result[1]  # type: ignore[index]
        assert '&' in params
        assert '%&' in params

    def test_anon_fn_no_args(self) -> None:
        """Anon fn no args."""
        result = parse_edn('#(println "hello")')
        assert result[0] == 'fn*'  # type: ignore[index]
        assert result[1] == []  # type: ignore[index]  # no % params found


# Reader conditionals #?(...), #?@(...)


class TestReaderConditionals:
    """Tests for Clojure reader conditionals."""

    def test_reader_conditional(self) -> None:
        """Reader conditional."""
        result = parse_edn('#?(:clj Double/NaN :cljs js/NaN)')
        assert isinstance(result, Tagged)
        assert result.tag == '?'
        assert isinstance(result.value, list)

    def test_reader_conditional_splicing(self) -> None:
        """Reader conditional splicing."""
        result = parse_edn('#?@(:clj [1 2] :cljs [3 4])')
        assert isinstance(result, Tagged)
        assert result.tag == '?@'
        assert isinstance(result.value, list)


# Namespaced maps #:ns{...}, #::ns{...}


class TestNamespacedMaps:
    """Tests for Clojure namespaced map reader macro."""

    def test_namespaced_map(self) -> None:
        """Namespaced map."""
        result = parse_edn('#:person{:name "Fred" :age 42}')
        assert result == {':person/name': 'Fred', ':person/age': 42}

    def test_namespaced_map_preserves_qualified(self) -> None:
        """Namespaced map preserves qualified."""
        result = parse_edn('#:person{:name "Fred" :other/age 42}')
        assert ':person/name' in result  # type: ignore[operator]
        assert ':other/age' in result  # type: ignore[operator]

    def test_auto_resolve_namespaced_map(self) -> None:
        """Auto resolve namespaced map."""
        result = parse_edn('#::person{:name "Fred"}')
        assert result == {':person/name': 'Fred'}

    def test_auto_resolve_no_ns(self) -> None:
        # #::{} with no namespace — keys stay as-is.
        """Auto resolve no ns."""
        result = parse_edn('#::{:name "Fred"}')
        assert result == {':name': 'Fred'}


# Span tracking


class TestSpanTracking:
    """Tests for EdnReader.read_string_with_span()."""

    def test_span_simple(self) -> None:
        """Span simple."""
        reader = EdnReader('"hello"')
        value, start, end = reader.read_string_with_span()
        assert value == 'hello'
        assert start == 0
        assert end == 7

    def test_span_with_offset(self) -> None:
        """Span with offset."""
        text = '  "world"  '
        reader = EdnReader(text)
        reader._skip_whitespace_and_comments()
        value, start, end = reader.read_string_with_span()
        assert value == 'world'
        assert start == 2
        assert end == 9
        assert text[start:end] == '"world"'

    def test_span_with_escapes(self) -> None:
        """Span with escapes."""
        text = r'"he\"llo"'
        reader = EdnReader(text)
        value, start, end = reader.read_string_with_span()
        assert value == 'he"llo'
        assert text[start:end] == r'"he\"llo"'

    def test_span_for_rewrite(self) -> None:
        """Span for rewrite."""
        text = '(defproject foo "1.0.0" :description "A lib")'
        reader = EdnReader(text)
        reader._advance()  # consume '('
        reader._skip_whitespace_and_comments()
        reader.read()  # 'defproject'
        reader._skip_whitespace_and_comments()
        reader.read()  # 'foo'
        reader._skip_whitespace_and_comments()
        old_ver, start, end = reader.read_string_with_span()
        assert old_ver == '1.0.0'
        new_text = text[:start] + '"2.0.0"' + text[end:]
        assert '2.0.0' in new_text
        assert '1.0.0' not in new_text


# Error handling


class TestErrors:
    """Tests for error handling."""

    def test_empty_input_raises(self) -> None:
        """Empty input raises."""
        with pytest.raises(ValueError, match='Unexpected end'):
            parse_edn('')

    def test_whitespace_only_raises(self) -> None:
        """Whitespace only raises."""
        with pytest.raises(ValueError, match='Unexpected end'):
            parse_edn('   ')

    def test_unexpected_close_brace(self) -> None:
        """Unexpected close brace."""
        with pytest.raises(ValueError, match='Unexpected closing'):
            parse_edn('}')

    def test_unexpected_close_bracket(self) -> None:
        """Unexpected close bracket."""
        with pytest.raises(ValueError, match='Unexpected closing'):
            parse_edn(']')

    def test_unexpected_close_paren(self) -> None:
        """Unexpected close paren."""
        with pytest.raises(ValueError, match='Unexpected closing'):
            parse_edn(')')

    def test_hash_at_eof(self) -> None:
        """Hash at eof."""
        with pytest.raises(ValueError, match='Unexpected end'):
            parse_edn('#')


# EdnReader multi-value streaming


class TestStreaming:
    """Tests for reading multiple values from a single reader."""

    def test_read_multiple_values(self) -> None:
        """Read multiple values."""
        reader = EdnReader(':a 1 :b 2')
        assert reader.read() == ':a'
        assert reader.read() == 1
        assert reader.read() == ':b'
        assert reader.read() == 2

    def test_read_past_end_raises(self) -> None:
        """Read past end raises."""
        reader = EdnReader('42')
        reader.read()
        with pytest.raises(ValueError, match='Unexpected end'):
            reader.read()

    def test_pos_advances(self) -> None:
        """Pos advances."""
        reader = EdnReader('42 "hello"')
        assert reader.pos == 0
        reader.read()
        assert reader.pos > 0
        old_pos = reader.pos
        reader.read()
        assert reader.pos > old_pos


# Realistic Clojure files


class TestRealisticFiles:
    """Tests parsing realistic deps.edn and project.clj content."""

    def test_deps_edn(self) -> None:
        """Deps edn."""
        edn = """\
{:deps {org.clojure/clojure {:mvn/version "1.11.1"}
        org.clojure/tools.reader {:mvn/version "1.3.7"}
        my.lib/core {:local/root "../core"}}
 :paths ["src" "resources"]
 :aliases {:dev {:extra-deps {nrepl/nrepl {:mvn/version "1.0.0"}}}}}
"""
        result = parse_edn(edn)
        assert isinstance(result, dict)
        assert ':deps' in result
        assert ':paths' in result
        assert ':aliases' in result
        deps = result[':deps']  # type: ignore[index]
        assert len(deps) == 3  # type: ignore[arg-type]
        assert deps['org.clojure/clojure'] == {':mvn/version': '1.11.1'}  # type: ignore[index]

    def test_project_clj(self) -> None:
        """Project clj."""
        clj = """\
(defproject com.example/my-lib "1.0.0"
  :description "A library"
  :url "https://example.com"
  :license {:name "Apache-2.0"}
  :dependencies [[org.clojure/clojure "1.11.1"]
                 [ring/ring-core "1.10.0"]]
  :profiles {:dev {:dependencies [[midje "1.10.9"]]}})
"""
        result = parse_edn(clj)
        assert isinstance(result, list)
        assert result[0] == 'defproject'
        assert result[1] == 'com.example/my-lib'
        assert result[2] == '1.0.0'

    def test_deps_edn_with_comments(self) -> None:
        """Deps edn with comments."""
        edn = """\
{;; Main dependencies
 :deps {org.clojure/clojure {:mvn/version "1.11.1"}}
 ;; Source paths
 :paths ["src"]}
"""
        result = parse_edn(edn)
        assert ':deps' in result  # type: ignore[operator]
        assert ':paths' in result  # type: ignore[operator]

    def test_project_clj_with_metadata(self) -> None:
        """Project clj with metadata."""
        clj = '(defproject foo "1.0" :dependencies [^:replace [org.clojure/clojure "1.11.1"]])'
        result = parse_edn(clj)
        assert isinstance(result, list)
        assert result[0] == 'defproject'
        # The ^:replace metadata is discarded, leaving the vector.
        deps_kw_idx = result.index(':dependencies')  # type: ignore[arg-type]
        deps = result[deps_kw_idx + 1]
        assert isinstance(deps, list)
