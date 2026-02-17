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

r"""SPDX license expression parser per SPDX Specification 3.0.1 Annex B.

Parses SPDX license expressions into an abstract syntax tree (AST) that
can be evaluated for license compatibility checks.

Grammar (ABNF from the spec)::

    idstring            = 1*(ALPHA / DIGIT / "-" / ".")
    license-id          = <short form license identifier>
    license-exception-id = <short form license exception identifier>
    license-ref         = ["DocumentRef-"idstring":"]"LicenseRef-"idstring
    addition-ref        = ["DocumentRef-"idstring":"]"AdditionRef-"idstring
    simple-expression   = license-id / license-id"+" / license-ref
    addition-expression = license-exception-id / addition-ref
    compound-expression = simple-expression
                        / simple-expression "WITH" addition-expression
                        / compound-expression "AND" compound-expression
                        / compound-expression "OR" compound-expression
                        / "(" compound-expression ")"
    license-expression  = simple-expression / compound-expression

Operator precedence (tightest to loosest)::

    +  >  WITH  >  AND  >  OR

Case rules:
    - Operators: case-sensitive, all-upper or all-lower (AND/and, OR/or, WITH/with)
    - License IDs: case-insensitive for matching

Key Concepts (ELI5)::

    ┌─────────────────────┬──────────────────────────────────────────────┐
    │ Concept              │ Plain-English                                │
    ├─────────────────────┼──────────────────────────────────────────────┤
    │ OR (disjunctive)     │ User may choose either license.             │
    │                      │ Compatible if ANY choice is compatible.     │
    ├─────────────────────┼──────────────────────────────────────────────┤
    │ AND (conjunctive)    │ User must comply with ALL licenses.         │
    │                      │ Compatible only if ALL are compatible.      │
    ├─────────────────────┼──────────────────────────────────────────────┤
    │ WITH (exception)     │ License + exception that relaxes terms.     │
    │                      │ Treat as the base license for compat.       │
    │                      │                                              │
    │                      │ Examples:                                    │
    │                      │   GPL-2.0 WITH Classpath-exception-2.0      │
    │                      │   GPL-2.0 WITH GCC-exception-3.1            │
    │                      │   LGPL-2.1 WITH OCaml-LGPL-linking-exception│
    │                      │                                              │
    │                      │ **Design decision**: We use the CONSERVATIVE│
    │                      │ approach — strip the exception and check     │
    │                      │ compat against the BASE license only.        │
    │                      │ This is language-agnostic and safe: if the   │
    │                      │ base license is compat, so is base+exception.│
    │                      │ If base is NOT compat, the exception may     │
    │                      │ relax terms enough (e.g. for Java classpath  │
    │                      │ linking), but that requires ecosystem-aware  │
    │                      │ legal analysis. Failing conservatively is    │
    │                      │ safer than false-positive compatibility.     │
    ├─────────────────────┼──────────────────────────────────────────────┤
    │ + (or-later)         │ "This version or any later version."        │
    │                      │ Expands the set of acceptable versions.     │
    └─────────────────────┴──────────────────────────────────────────────┘

Usage::

    from releasekit.spdx_expr import parse, LicenseId, Or, And, With

    expr = parse('MIT OR (Apache-2.0 AND BSD-3-Clause)')
    assert isinstance(expr, Or)
    assert expr.left == LicenseId('MIT')

    expr2 = parse('GPL-2.0-or-later WITH Classpath-exception-2.0')
    assert isinstance(expr2, With)
    assert expr2.license == LicenseId('GPL-2.0-or-later')
    assert expr2.exception == 'Classpath-exception-2.0'

    # Collect all license IDs from an expression.
    ids = license_ids(expr)
    assert ids == {'MIT', 'Apache-2.0', 'BSD-3-Clause'}
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    'And',
    'CompatibilityChecker',
    'ExprNode',
    'LicenseId',
    'LicenseRef',
    'Or',
    'ParseError',
    'With',
    'license_ids',
    'parse',
]


# ---------------------------------------------------------------------------
# AST node types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LicenseId:
    """A simple SPDX license identifier, optionally with ``+`` (or-later).

    Attributes:
        id: The SPDX short identifier (e.g. ``"MIT"``, ``"GPL-3.0-only"``).
        or_later: ``True`` if the ``+`` suffix was present.
    """

    id: str
    or_later: bool = False

    def __str__(self) -> str:
        """Return the SPDX identifier, with ``+`` suffix if or-later."""
        return f'{self.id}+' if self.or_later else self.id


@dataclass(frozen=True)
class LicenseRef:
    """A user-defined license reference (``LicenseRef-...``).

    Attributes:
        ref: The full reference string (e.g. ``"LicenseRef-Custom"``).
        document_ref: Optional ``DocumentRef-`` prefix.
    """

    ref: str
    document_ref: str = ''

    def __str__(self) -> str:
        """Return the license reference string."""
        if self.document_ref:
            return f'{self.document_ref}:{self.ref}'
        return self.ref


@dataclass(frozen=True)
class With:
    """A license with an exception (``license WITH exception``).

    Attributes:
        license: The base license (simple expression).
        exception: The exception identifier string.
    """

    license: LicenseId | LicenseRef
    exception: str

    def __str__(self) -> str:
        """Return ``license WITH exception`` string."""
        return f'{self.license} WITH {self.exception}'


@dataclass(frozen=True)
class And:
    """Conjunctive combination — must comply with both.

    Attributes:
        left: Left operand.
        right: Right operand.
    """

    left: ExprNode
    right: ExprNode

    def __str__(self) -> str:
        """Return ``left AND right`` with parentheses around nested OR."""
        left_s = f'({self.left})' if isinstance(self.left, Or) else str(self.left)
        right_s = f'({self.right})' if isinstance(self.right, Or) else str(self.right)
        return f'{left_s} AND {right_s}'


@dataclass(frozen=True)
class Or:
    """Disjunctive combination — may choose either.

    Attributes:
        left: Left operand.
        right: Right operand.
    """

    left: ExprNode
    right: ExprNode

    def __str__(self) -> str:
        """Return ``left OR right`` string."""
        return f'{self.left} OR {self.right}'


# Union of all AST node types.
ExprNode = LicenseId | LicenseRef | With | And | Or


# ---------------------------------------------------------------------------
# Parse errors
# ---------------------------------------------------------------------------


class ParseError(ValueError):
    """Raised when an SPDX expression cannot be parsed.

    Attributes:
        expression: The original expression string.
        position: Character offset where the error was detected.
        detail: Human-readable description of the problem.
    """

    def __init__(self, expression: str, position: int, detail: str) -> None:
        """Initialize with expression text, error position, and detail message."""
        self.expression = expression
        self.position = position
        self.detail = detail
        # Build a caret-style error message.
        marker = ' ' * position + '^'
        super().__init__(f'SPDX parse error at position {position}: {detail}\n  {expression}\n  {marker}')


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Matches: AND, and, OR, or, WITH, with, (, ), or an idstring (license ID).
# The idstring pattern also captures the trailing + if present.
_TOKEN_RE = re.compile(
    r"""
    \s*                          # skip leading whitespace
    (?:
        (AND|and)                # group 1: AND operator
      | (OR|or)                  # group 2: OR operator
      | (WITH|with)              # group 3: WITH operator
      | (\()                     # group 4: left paren
      | (\))                     # group 5: right paren
      | (                        # group 6: idstring (license-id, LicenseRef, etc.)
          (?:DocumentRef-[A-Za-z0-9.\-]+:)?
          (?:LicenseRef-|AdditionRef-)?
          [A-Za-z0-9.\-]+
        )
        (\+)?                    # group 7: optional or-later suffix
    )
    """,
    re.VERBOSE,
)

_TOK_AND = 'AND'
_TOK_OR = 'OR'
_TOK_WITH = 'WITH'
_TOK_LPAREN = '('
_TOK_RPAREN = ')'
_TOK_ID = 'ID'
_TOK_EOF = 'EOF'


@dataclass
class _Token:
    kind: str
    value: str
    or_later: bool
    pos: int


def _tokenize(expr: str) -> list[_Token]:
    """Tokenize an SPDX license expression string."""
    tokens: list[_Token] = []
    pos = 0
    while pos < len(expr):
        # Skip whitespace.
        if expr[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(expr, pos)
        if m is None:
            raise ParseError(expr, pos, f'unexpected character {expr[pos]!r}')
        if m.group(1):
            tokens.append(_Token(_TOK_AND, 'AND', False, m.start(1)))
        elif m.group(2):
            tokens.append(_Token(_TOK_OR, 'OR', False, m.start(2)))
        elif m.group(3):
            tokens.append(_Token(_TOK_WITH, 'WITH', False, m.start(3)))
        elif m.group(4):
            tokens.append(_Token(_TOK_LPAREN, '(', False, m.start(4)))
        elif m.group(5):
            tokens.append(_Token(_TOK_RPAREN, ')', False, m.start(5)))
        elif m.group(6):
            or_later = m.group(7) is not None
            tokens.append(_Token(_TOK_ID, m.group(6), or_later, m.start(6)))
        else:
            raise ParseError(expr, pos, 'internal tokenizer error')  # pragma: no cover
        pos = m.end()
    tokens.append(_Token(_TOK_EOF, '', False, len(expr)))
    return tokens


# ---------------------------------------------------------------------------
# Recursive descent parser
# ---------------------------------------------------------------------------
#
# Precedence (tightest first):  +  >  WITH  >  AND  >  OR
#
# Grammar rewritten for recursive descent (left-recursive eliminated):
#
#   expression     = and_expr ("OR" and_expr)*
#   and_expr       = with_expr ("AND" with_expr)*
#   with_expr      = simple_expr ("WITH" idstring)?
#   simple_expr    = "(" expression ")" / license_id
#   license_id     = idstring "+"?


class _Parser:
    """Recursive descent parser for SPDX license expressions."""

    def __init__(self, expr: str, tokens: list[_Token]) -> None:
        self._expr = expr
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> _Token:
        return self._tokens[self._pos]

    def _advance(self) -> _Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, kind: str) -> _Token:
        tok = self._peek()
        if tok.kind != kind:
            raise ParseError(
                self._expr,
                tok.pos,
                f'expected {kind}, got {tok.kind} ({tok.value!r})',
            )
        return self._advance()

    # expression = and_expr ("OR" and_expr)*
    def parse_expression(self) -> ExprNode:
        left = self._parse_and_expr()
        while self._peek().kind == _TOK_OR:
            self._advance()
            right = self._parse_and_expr()
            left = Or(left, right)
        return left

    # and_expr = with_expr ("AND" with_expr)*
    def _parse_and_expr(self) -> ExprNode:
        left = self._parse_with_expr()
        while self._peek().kind == _TOK_AND:
            self._advance()
            right = self._parse_with_expr()
            left = And(left, right)
        return left

    # with_expr = simple_expr ("WITH" idstring)?
    def _parse_with_expr(self) -> ExprNode:
        node = self._parse_simple_expr()
        if self._peek().kind == _TOK_WITH:
            self._advance()
            exc_tok = self._expect(_TOK_ID)
            if not isinstance(node, (LicenseId, LicenseRef)):
                raise ParseError(
                    self._expr,
                    exc_tok.pos,
                    'WITH operator requires a simple license expression on the left',
                )
            node = With(license=node, exception=exc_tok.value)
        return node

    # simple_expr = "(" expression ")" / license_id
    def _parse_simple_expr(self) -> ExprNode:
        tok = self._peek()
        if tok.kind == _TOK_LPAREN:
            self._advance()
            node = self.parse_expression()
            self._expect(_TOK_RPAREN)
            return node
        if tok.kind == _TOK_ID:
            return self._parse_license_id()
        raise ParseError(
            self._expr,
            tok.pos,
            f'expected license identifier or "(", got {tok.kind} ({tok.value!r})',
        )

    # license_id = idstring "+"?
    def _parse_license_id(self) -> LicenseId | LicenseRef:
        tok = self._advance()
        if tok.kind != _TOK_ID:
            raise ParseError(
                self._expr,
                tok.pos,
                f'expected license identifier, got {tok.kind} ({tok.value!r})',
            )
        value = tok.value
        # Detect LicenseRef / AdditionRef / DocumentRef patterns.
        if 'LicenseRef-' in value or 'AdditionRef-' in value:
            doc_ref = ''
            ref = value
            if ':' in value:
                doc_ref, ref = value.split(':', 1)
            return LicenseRef(ref=ref, document_ref=doc_ref)
        return LicenseId(id=value, or_later=tok.or_later)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(expression: str) -> ExprNode:
    """Parse an SPDX license expression into an AST.

    Args:
        expression: An SPDX license expression string
            (e.g. ``"MIT OR Apache-2.0"``).

    Returns:
        The root :data:`ExprNode` of the parsed AST.

    Raises:
        ParseError: If the expression is syntactically invalid.

    Examples::

        >>> parse("MIT")
        LicenseId(id='MIT', or_later=False)

        >>> parse("GPL-2.0-only OR MIT")
        Or(left=LicenseId(id='GPL-2.0-only', or_later=False),
           right=LicenseId(id='MIT', or_later=False))

        >>> parse("GPL-2.0-or-later WITH Classpath-exception-2.0")
        With(license=LicenseId(id='GPL-2.0-or-later', or_later=False),
             exception='Classpath-exception-2.0')
    """
    stripped = expression.strip()
    if not stripped:
        raise ParseError(expression, 0, 'empty expression')
    tokens = _tokenize(stripped)
    parser = _Parser(stripped, tokens)
    result = parser.parse_expression()
    # Ensure all tokens were consumed.
    end_tok = parser._peek()  # noqa: SLF001
    if end_tok.kind != _TOK_EOF:
        raise ParseError(
            stripped,
            end_tok.pos,
            f'unexpected token after expression: {end_tok.kind} ({end_tok.value!r})',
        )
    return result


def license_ids(node: ExprNode) -> set[str]:
    """Collect all license identifier strings from an AST.

    Returns the canonical ID strings (without ``+`` suffix).
    ``LicenseRef-*`` values are included as-is.

    Args:
        node: The root of a parsed SPDX expression AST.

    Returns:
        A set of license identifier strings.

    Examples::

        >>> license_ids(parse("MIT OR Apache-2.0"))
        {'MIT', 'Apache-2.0'}

        >>> license_ids(parse("GPL-2.0+ WITH Bison-exception-2.2"))
        {'GPL-2.0'}
    """
    ids: set[str] = set()
    _collect_ids(node, ids)
    return ids


def _collect_ids(node: ExprNode, acc: set[str]) -> None:
    """Recursively collect license IDs into *acc*."""
    if isinstance(node, LicenseId):
        acc.add(node.id)
    elif isinstance(node, LicenseRef):
        full = f'{node.document_ref}:{node.ref}' if node.document_ref else node.ref
        acc.add(full)
    elif isinstance(node, With):
        _collect_ids(node.license, acc)
    elif isinstance(node, And):
        _collect_ids(node.left, acc)
        _collect_ids(node.right, acc)
    elif isinstance(node, Or):
        _collect_ids(node.left, acc)
        _collect_ids(node.right, acc)


class CompatibilityChecker(Protocol):
    """Protocol for objects that can check license compatibility."""

    def is_compatible(
        self,
        project_license: str,
        dep: LicenseId | LicenseRef,
    ) -> bool:
        """Return whether *dep* is compatible with *project_license*."""  # pragma: no cover
        ...


def is_compatible(
    node: ExprNode,
    checker: CompatibilityChecker,
    project_license: str,
) -> bool:
    """Evaluate whether an SPDX expression is compatible with a project license.

    Semantics:
        - ``OR``: compatible if **any** branch is compatible.
        - ``AND``: compatible only if **all** branches are compatible.
        - ``WITH``: treat as the base license (exceptions only relax terms).
        - ``+`` (or-later): expand to check current and later versions.

    Args:
        node: Parsed SPDX expression AST.
        checker: A compatibility graph with an
            ``is_compatible(project: str, dep: LicenseId | LicenseRef) -> bool``
            method. The checker receives the full AST node so it can
            inspect ``or_later`` and ``document_ref``.
        project_license: The SPDX ID of the project's own license.

    Returns:
        ``True`` if the expression is compatible with *project_license*.
    """
    check = checker.is_compatible
    return _eval_compat(node, check, project_license)


def _eval_compat(
    node: ExprNode,
    check: Callable[[str, LicenseId | LicenseRef], bool],
    project_license: str,
) -> bool:
    """Recursively evaluate compatibility."""
    if isinstance(node, (LicenseId, LicenseRef)):
        # Pass the full node so the checker can inspect or_later / document_ref.
        return check(project_license, node)
    if isinstance(node, With):
        # WITH exceptions (e.g. Classpath-exception-2.0, GCC-exception-3.1)
        # only RELAX the base license's terms — they never make a license
        # MORE restrictive. The conservative approach is to check compat
        # against the base license only.
        #
        # Why not model exceptions explicitly?
        #   1. Exceptions are language/linking-model dependent:
        #      - C/C++: static linking creates combined works → exception matters
        #      - Java: classpath loading → Classpath-exception-2.0 is critical
        #      - Python: `import` ≠ linking (no static/dynamic distinction) →
        #        LGPL/GPL linking exceptions are legally ambiguous
        #      - Go/Rust: always statically compiled → exception matters
        #   2. If the base license is already compatible (e.g. MIT, Apache-2.0),
        #      the exception is irrelevant — it only relaxes further.
        #   3. If the base license is incompatible (e.g. GPL-2.0 with an
        #      Apache-2.0 project), the exception *might* make it compatible
        #      for certain linking models, but that requires ecosystem-specific
        #      legal analysis that we intentionally do not automate.
        #
        # Users who need exception-aware checking can use `allow_licenses`
        # or `license_overrides` in releasekit.toml to explicitly allow
        # specific WITH expressions for their ecosystem.
        return _eval_compat(node.license, check, project_license)
    if isinstance(node, Or):
        # Disjunctive: compatible if EITHER branch is compatible.
        return _eval_compat(node.left, check, project_license) or _eval_compat(node.right, check, project_license)
    if isinstance(node, And):
        # Conjunctive: compatible only if BOTH branches are compatible.
        return _eval_compat(node.left, check, project_license) and _eval_compat(node.right, check, project_license)
    return False  # pragma: no cover
