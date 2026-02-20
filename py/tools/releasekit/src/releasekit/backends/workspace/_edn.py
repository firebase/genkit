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

r"""Complete EDN / Clojure reader.

`EDN <https://github.com/edn-format/edn>`_ (Extensible Data Notation)
is the data-literal subset of Clojure.  This module provides a
zero-dependency, pure-Python streaming parser that covers the **full
EDN specification** plus common **Clojure reader extensions**.

EDN built-in elements
~~~~~~~~~~~~~~~~~~~~~

- ``nil``, ``true``, ``false``
- strings ``"..."`` with ``\\t \\r \\n \\\\ \\" \\uNNNN`` escapes
- characters ``\\c``, ``\\newline``, ``\\return``, ``\\space``,
  ``\\tab``, ``\\uNNNN``
- symbols ``foo``, ``my.ns/bar``
- keywords ``:name``, ``:ns/name``
- integers (64-bit), arbitrary-precision ``42N``
- floating-point (64-bit), exact-precision ``3.14M``
- ratios ``22/7``
- lists ``()``, vectors ``[]``, maps ``{}``, sets ``#{}``
- ``#inst "..."`` → :class:`datetime.datetime`
- ``#uuid "..."`` → :class:`uuid.UUID`
- tagged literals ``#tag value`` (generic fallback)
- comments ``;``
- discard ``#_``

Clojure reader extensions
~~~~~~~~~~~~~~~~~~~~~~~~~

- regex ``#"pattern"`` → :class:`re.Pattern`
- metadata ``^{...} form``, ``^:kw form``, ``^Type form``
- quote ``'form`` → ``(quote form)``
- deref ``@form`` → ``(deref form)``
- syntax-quote (backtick) ``form`` → ``(syntax-quote form)``
- unquote ``~form`` → ``(unquote form)``
- unquote-splicing ``~@form`` → ``(unquote-splicing form)``
- var quote ``#'sym`` → ``(var sym)``
- anonymous functions ``#(... % %1 %2 %&)``
  → ``(fn* [...] ...)``
- reader conditionals ``#?(...)``, ``#?@(...)``
  → platform-filtered or raw list
- namespaced maps ``#:ns{...}``, ``#::ns{...}``

Span tracking
~~~~~~~~~~~~~

:meth:`EdnReader.read_string_with_span` returns the byte offsets of a
parsed string literal so callers can perform targeted text splices
without regex.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from typing import cast
from uuid import UUID

__all__ = [
    'EdnReader',
    'Tagged',
    'parse_edn',
]


class Tagged:
    """A tagged literal ``#tag value`` with no registered handler.

    Attributes:
        tag: The tag symbol (e.g. ``"myapp/Person"``).
        value: The parsed value following the tag.
    """

    __slots__ = ('tag', 'value')

    def __init__(self, tag: str, value: object) -> None:
        self.tag = tag
        self.value = value

    def __repr__(self) -> str:
        return f'Tagged({self.tag!r}, {self.value!r})'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tagged):
            return self.tag == other.tag and self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.tag, repr(self.value)))


_NAMED_CHARS: dict[str, str] = {
    'newline': '\n',
    'return': '\r',
    'space': ' ',
    'tab': '\t',
    'backspace': '\b',
    'formfeed': '\f',
}

# Characters that terminate an atom/symbol/keyword token.
_DELIMITERS = frozenset(' \t\n\r,{}[]()";')


def parse_edn(text: str) -> object:
    r"""Parse an EDN string into Python objects.

    Mapping:
        - EDN map ``{}``       → Python ``dict``
        - EDN vector ``[]``    → Python ``list``
        - EDN list ``()``      → Python ``list``
        - EDN set ``#{}``      → Python ``set``
        - EDN string ``"..."`` → Python ``str``
        - EDN character ``\\c``→ Python ``str`` (single char)
        - EDN keyword ``:k``   → Python ``str`` (prefixed with ``:``)
        - EDN symbol ``foo``   → Python ``str``
        - EDN integer          → Python ``int``
        - EDN bigint ``42N``   → Python ``int``
        - EDN float            → Python ``float``
        - EDN bigdecimal ``M`` → :class:`~decimal.Decimal`
        - EDN ratio ``22/7``   → :class:`~fractions.Fraction`
        - EDN nil              → Python ``None``
        - EDN true/false       → Python ``True``/``False``
        - ``#inst "..."``      → :class:`~datetime.datetime`
        - ``#uuid "..."``      → :class:`~uuid.UUID`
        - ``#"regex"``         → :class:`re.Pattern`
        - other tagged         → :class:`Tagged`

    Args:
        text: EDN source text.

    Returns:
        The parsed Python object.

    Raises:
        ValueError: If the EDN is malformed.
    """
    reader = EdnReader(text)
    return reader.read()


class EdnReader:
    """Complete streaming EDN / Clojure reader.

    Instantiate with the full source text, then call :meth:`read`
    repeatedly to consume values.  The reader maintains a cursor
    position accessible via :attr:`pos`.
    """

    def __init__(self, text: str) -> None:
        """Initialize with EDN source text."""
        self._text = text
        self._pos = 0

    def _peek(self) -> str:
        """Peek at the current character without advancing."""
        if self._pos >= len(self._text):
            return ''
        return self._text[self._pos]

    def _peek2(self) -> str:
        """Peek at the character after the current one."""
        idx = self._pos + 1
        if idx >= len(self._text):
            return ''
        return self._text[idx]

    def _advance(self) -> str:
        """Advance and return the current character."""
        ch = self._text[self._pos]
        self._pos += 1
        return ch

    def _skip_whitespace_and_comments(self) -> None:
        """Skip whitespace, commas (EDN treats commas as whitespace), and ; comments."""
        while self._pos < len(self._text):
            ch = self._text[self._pos]
            if ch in ' \t\n\r,':
                self._pos += 1
            elif ch == ';':
                # Skip to end of line.
                while self._pos < len(self._text) and self._text[self._pos] != '\n':
                    self._pos += 1
            else:
                break

    def _at_end(self) -> bool:
        """Return True if the reader has consumed all input."""
        return self._pos >= len(self._text)

    @property
    def pos(self) -> int:
        """Current reader position in the source text."""
        return self._pos

    def read(self) -> object:
        """Read one EDN / Clojure value."""
        self._skip_whitespace_and_comments()
        if self._at_end():
            msg = 'Unexpected end of EDN input'
            raise ValueError(msg)

        ch = self._peek()

        if ch == '{':
            return self._read_map()
        if ch == '[':
            return self._read_vector()
        if ch == '(':
            return self._read_list()
        if ch == '#':
            return self._read_dispatch()
        if ch == '"':
            return self._read_string()
        if ch == ':':
            return self._read_keyword()
        if ch == '\\':
            return self._read_character()
        if ch == "'":
            return self._read_quote()
        if ch == '@':
            return self._read_deref()
        if ch == '`':
            return self._read_syntax_quote()
        if ch == '~':
            return self._read_unquote()
        if ch == '^':
            return self._read_metadata()
        if ch in ('}', ']', ')'):
            msg = f'Unexpected closing delimiter: {ch!r} at position {self._pos}'
            raise ValueError(msg)
        return self._read_atom()

    def read_string_with_span(self) -> tuple[str, int, int]:
        """Read an EDN string and return ``(value, start, end)``.

        *start* is the position of the opening ``"``, *end* is one
        past the closing ``"``.  This allows callers to do targeted
        text replacement without regex.
        """
        start = self._pos
        value = self._read_string_inner()
        return value, start, self._pos

    def _read_map(self) -> dict[str, object]:
        """Read an EDN map ``{k v ...}``."""
        self._advance()  # consume '{'
        result: dict[str, object] = {}
        while True:
            self._skip_whitespace_and_comments()
            if self._peek() == '}':
                self._advance()
                return result
            if self._at_end():
                msg = 'Unterminated map'
                raise ValueError(msg)
            key = self.read()
            value = self.read()
            result[str(key)] = value
        return result  # pragma: no cover

    def _read_vector(self) -> list[object]:
        """Read an EDN vector ``[...]``."""
        self._advance()  # consume '['
        result: list[object] = []
        while True:
            self._skip_whitespace_and_comments()
            if self._peek() == ']':
                self._advance()
                return result
            if self._at_end():
                msg = 'Unterminated vector'
                raise ValueError(msg)
            result.append(self.read())
        return result  # pragma: no cover

    def _read_list(self) -> list[object]:
        """Read an EDN list ``(...)``."""
        self._advance()  # consume '('
        result: list[object] = []
        while True:
            self._skip_whitespace_and_comments()
            if self._peek() == ')':
                self._advance()
                return result
            if self._at_end():
                msg = 'Unterminated list'
                raise ValueError(msg)
            result.append(self.read())
        return result  # pragma: no cover

    def _read_set(self) -> set[object]:
        """Read an EDN set ``#{...}``."""
        self._advance()  # consume '{'
        result: set[object] = set()
        while True:
            self._skip_whitespace_and_comments()
            if self._peek() == '}':
                self._advance()
                return result
            if self._at_end():
                msg = 'Unterminated set'
                raise ValueError(msg)
            result.add(self.read())
        return result  # pragma: no cover

    def _read_dispatch(self) -> object:
        """Read a ``#``-prefixed form."""
        self._advance()  # consume '#'
        if self._at_end():
            msg = 'Unexpected end of input after #'
            raise ValueError(msg)
        ch = self._peek()

        # #{...} — set
        if ch == '{':
            return self._read_set()

        # #_ — discard
        if ch == '_':
            self._advance()
            self.read()  # read and discard
            return self.read()

        # #"..." — regex (Clojure extension)
        if ch == '"':
            return self._read_regex()

        # #' — var quote (Clojure extension)
        if ch == "'":
            self._advance()
            sym = self.read()
            return ['var', sym]

        # #( — anonymous function (Clojure extension)
        if ch == '(':
            return self._read_anon_fn()

        # #? — reader conditional (Clojure extension)
        if ch == '?':
            return self._read_reader_conditional()

        # #: — namespaced map (Clojure extension)
        if ch == ':':
            return self._read_namespaced_map()

        # #tag value — tagged literal
        tag = self._read_raw_symbol()
        self._skip_whitespace_and_comments()
        value = self.read()

        # Built-in tags.
        if tag == 'inst':
            return self._handle_inst(value)
        if tag == 'uuid':
            return self._handle_uuid(value)

        return Tagged(tag, value)

    @staticmethod
    def _handle_inst(value: object) -> datetime:
        """Convert ``#inst "..."`` to :class:`datetime.datetime`."""
        if not isinstance(value, str):
            msg = f'#inst requires a string, got {type(value).__name__}'
            raise ValueError(msg)
        text = value
        # Handle Z suffix → +00:00 for fromisoformat compatibility.
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        # Python 3.10's fromisoformat only accepts 0, 3, or 6 fractional-
        # second digits.  Normalise to 6 so arbitrary precision works.
        text = re.sub(
            r'(\d{2}:\d{2}:\d{2})\.(\d+)',
            lambda m: f'{m.group(1)}.{m.group(2)[:6].ljust(6, "0")}',
            text,
        )
        try:
            return datetime.fromisoformat(text)
        except (ValueError, TypeError) as exc:
            msg = f'Invalid #inst value: {value!r}'
            raise ValueError(msg) from exc

    @staticmethod
    def _handle_uuid(value: object) -> UUID:
        """Convert ``#uuid "..."`` to :class:`uuid.UUID`."""
        if not isinstance(value, str):
            msg = f'#uuid requires a string, got {type(value).__name__}'
            raise ValueError(msg)
        try:
            return UUID(value)
        except (ValueError, TypeError) as exc:
            msg = f'Invalid #uuid value: {value!r}'
            raise ValueError(msg) from exc

    def _read_regex(self) -> re.Pattern[str]:
        """Read ``#"pattern"`` → compiled regex."""
        # The opening '"' is still pending.
        pattern = self._read_regex_body()
        return re.compile(pattern)

    def _read_regex_body(self) -> str:
        """Read the body of a regex literal ``"..."`` without interpreting escapes."""
        self._advance()  # consume opening '"'
        chars: list[str] = []
        while True:
            if self._at_end():
                msg = 'Unterminated regex literal'
                raise ValueError(msg)
            ch = self._advance()
            if ch == '"':
                return ''.join(chars)
            if ch == '\\':
                if self._at_end():
                    msg = 'Unterminated regex escape'
                    raise ValueError(msg)
                esc = self._advance()
                # In regex literals, pass through escape sequences raw
                # so the regex engine interprets them.
                chars.append('\\')
                chars.append(esc)
            else:
                chars.append(ch)

    def _read_anon_fn(self) -> list[object]:
        """Read ``#(...)`` → ``['fn*', [params...], body...]``."""
        body = self._read_list()  # reads the (...) part
        # Scan body for % parameters to determine arity.
        state: dict[str, object] = {'max': 0, 'rest': False}
        self._scan_anon_params(body, state)
        max_arg = int(cast(int, state['max']))  # narrowed from object
        has_rest = bool(state['rest'])  # narrowed from object
        # Build parameter vector.
        params: list[str] = [f'%{i}' for i in range(1, max_arg + 1)]
        if has_rest:
            params.append('&')
            params.append('%&')
        return ['fn*', params, *body]

    def _scan_anon_params(self, form: object, state: dict[str, object]) -> None:
        """Recursively scan for ``%``, ``%N``, ``%&`` in an anon fn body."""
        if isinstance(form, str):
            if form == '%' or form == '%1':
                state['max'] = max(state['max'], 1)  # type: ignore[arg-type]
            elif form == '%&':
                state['rest'] = True
            elif form.startswith('%') and len(form) > 1 and form[1:].isdigit():
                n = int(form[1:])
                state['max'] = max(state['max'], n)  # type: ignore[arg-type]
        elif isinstance(form, list):
            for item in form:
                self._scan_anon_params(item, state)
        elif isinstance(form, dict):
            for k, v in form.items():
                self._scan_anon_params(k, state)
                self._scan_anon_params(v, state)
        elif isinstance(form, set):
            for item in form:
                self._scan_anon_params(item, state)

    def _read_reader_conditional(self) -> object:
        """Read ``#?(...)`` or ``#?@(...)``."""
        self._advance()  # consume '?'
        splicing = False
        if self._peek() == '@':
            self._advance()
            splicing = True
        form = self._read_list()
        # Return as a tagged structure; actual platform filtering
        # would require knowing the target platform.
        tag = '?@' if splicing else '?'
        return Tagged(tag, form)

    def _read_namespaced_map(self) -> dict[str, object]:
        """Read ``#:ns{...}`` or ``#::ns{...}``."""
        self._advance()  # consume ':'
        auto_resolve = False
        if self._peek() == ':':
            self._advance()
            auto_resolve = True
        # Read the namespace name.
        ns_start = self._pos
        while not self._at_end() and self._text[self._pos] not in _DELIMITERS and self._text[self._pos] != '{':
            self._pos += 1
        ns = self._text[ns_start : self._pos]
        self._skip_whitespace_and_comments()
        if self._peek() != '{':
            msg = f'Expected {{ after namespaced map prefix, got {self._peek()!r}'
            raise ValueError(msg)
        raw_map = self._read_map()
        # Qualify unqualified keyword keys with the namespace.
        if not ns and auto_resolve:
            # #::{} with no ns — keys stay as-is (would need alias resolution).
            return raw_map
        result: dict[str, object] = {}
        for k, v in raw_map.items():
            if k.startswith(':') and '/' not in k:
                # Unqualified keyword → qualify with namespace.
                result[f':{ns}/{k[1:]}'] = v
            else:
                result[k] = v
        return result

    def _read_quote(self) -> list[object]:
        """Read ``'form`` → ``['quote', form]``."""
        self._advance()  # consume "'"
        form = self.read()
        return ['quote', form]

    def _read_deref(self) -> list[object]:
        """Read ``@form`` → ``['deref', form]``."""
        self._advance()  # consume '@'
        form = self.read()
        return ['deref', form]

    def _read_syntax_quote(self) -> list[object]:
        r"""Read :literal:`\\`form` → ``['syntax-quote', form]``."""
        self._advance()  # consume '`'
        form = self.read()
        return ['syntax-quote', form]

    def _read_unquote(self) -> list[object]:
        """Read ``~form`` or ``~@form``."""
        self._advance()  # consume '~'
        if self._peek() == '@':
            self._advance()
            form = self.read()
            return ['unquote-splicing', form]
        form = self.read()
        return ['unquote', form]

    def _read_metadata(self) -> object:
        """Read ``^meta form`` — metadata is read and attached to the form.

        For simplicity, metadata is discarded and the underlying form
        is returned.  This matches the behavior needed for parsing
        ``deps.edn`` and ``project.clj`` files where metadata is
        informational.
        """
        self._advance()  # consume '^'
        self.read()  # read and discard metadata
        return self.read()  # return the actual form

    def _read_string_inner(self) -> str:
        """Read an EDN string ``"..."`` with full escape support."""
        self._advance()  # consume opening '"'
        chars: list[str] = []
        while True:
            if self._at_end():
                msg = 'Unterminated string'
                raise ValueError(msg)
            ch = self._advance()
            if ch == '"':
                return ''.join(chars)
            if ch == '\\':
                if self._at_end():
                    msg = 'Unterminated string escape'
                    raise ValueError(msg)
                esc = self._advance()
                if esc == 'n':
                    chars.append('\n')
                elif esc == 't':
                    chars.append('\t')
                elif esc == 'r':
                    chars.append('\r')
                elif esc == '"':
                    chars.append('"')
                elif esc == '\\':
                    chars.append('\\')
                elif esc == 'u':
                    # Unicode escape \uNNNN.
                    hex_chars = ''
                    for _ in range(4):
                        if self._at_end():
                            msg = 'Unterminated \\u escape'
                            raise ValueError(msg)
                        hex_chars += self._advance()
                    try:
                        chars.append(chr(int(hex_chars, 16)))
                    except ValueError as exc:
                        msg = f'Invalid unicode escape: \\u{hex_chars}'
                        raise ValueError(msg) from exc
                elif esc == 'b':
                    chars.append('\b')
                elif esc == 'f':
                    chars.append('\f')
                else:
                    chars.append(esc)
            else:
                chars.append(ch)

    def _read_string(self) -> str:
        """Read an EDN string ``"..."``."""
        return self._read_string_inner()

    def _read_character(self) -> str:
        r"""Read an EDN character literal ``\\c``, ``\\newline``, ``\\uNNNN``."""
        self._advance()  # consume '\\'
        if self._at_end():
            msg = 'Unexpected end of input after \\'
            raise ValueError(msg)
        # Read the character name/value.
        start = self._pos
        # Consume alphanumeric characters (for named chars like \newline).
        while not self._at_end() and self._text[self._pos] not in _DELIMITERS:
            self._pos += 1
        token = self._text[start : self._pos]
        if not token:
            msg = f'Empty character literal at position {start}'
            raise ValueError(msg)
        # Named characters.
        if token in _NAMED_CHARS:
            return _NAMED_CHARS[token]
        # Unicode character \uNNNN.
        if token.startswith('u') and len(token) == 5:  # noqa: PLR2004
            try:
                return chr(int(token[1:], 16))
            except ValueError:
                pass
        # Single character.
        if len(token) == 1:
            return token
        msg = f'Unknown character literal: \\{token}'
        raise ValueError(msg)

    def _read_keyword(self) -> str:
        """Read an EDN keyword ``:name`` or ``:ns/name``."""
        start = self._pos
        self._advance()  # consume ':'
        while not self._at_end() and self._text[self._pos] not in _DELIMITERS:
            self._pos += 1
        return self._text[start : self._pos]

    def _read_raw_symbol(self) -> str:
        """Read a raw symbol token without interpreting it."""
        start = self._pos
        while not self._at_end() and self._text[self._pos] not in _DELIMITERS and self._text[self._pos] != '#':
            self._pos += 1
        token = self._text[start : self._pos]
        if not token:
            msg = f'Empty token at position {start}'
            raise ValueError(msg)
        return token

    def _read_atom(self) -> object:
        """Read an EDN atom (symbol, number, ratio, nil, true, false)."""
        token = self._read_raw_symbol()

        # Literals.
        if token == 'nil':
            return None
        if token == 'true':
            return True
        if token == 'false':
            return False

        # Arbitrary-precision integer: 42N
        if token.endswith('N') and len(token) > 1:
            try:
                return int(token[:-1])
            except ValueError:
                pass

        # Exact-precision decimal: 3.14M
        if token.endswith('M') and len(token) > 1:
            try:
                return Decimal(token[:-1])
            except Exception:  # noqa: BLE001, S110
                pass

        # Ratio: 22/7 (but not a symbol like my.ns/foo — ratios are
        # digits/digits only).
        if '/' in token:
            parts = token.split('/', 1)
            if len(parts) == 2 and parts[0] and parts[1]:  # noqa: PLR2004
                try:
                    num = int(parts[0])
                    den = int(parts[1])
                    return Fraction(num, den)
                except ValueError:
                    pass

        # Integer.
        try:
            return int(token)
        except ValueError:
            pass

        # Float.
        try:
            return float(token)
        except ValueError:
            pass

        # Symbol — return as string.
        return token
