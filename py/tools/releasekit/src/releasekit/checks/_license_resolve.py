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

r"""Fuzzy SPDX license name resolver.

Resolves messy, ambiguous, or misspelled license strings to canonical
SPDX identifiers using a 5-stage pipeline:

    1. **Exact match** — case-insensitive lookup against SPDX IDs.
    2. **Alias match** — case-insensitive lookup against known aliases
       (legacy names, PyPI classifiers, abbreviations).
    3. **Normalized match** — strip punctuation/whitespace, compare.
    4. **Edit-distance match** — Levenshtein distance against all
       known IDs and aliases; pick the closest within a threshold.
    5. **Unresolved** — no match found; return with suggestions.

Each stage produces a :class:`ResolvedLicense` with a confidence score
(1.0 for exact, decreasing for fuzzier matches) and the resolution
method used.

Usage::

    from releasekit.checks._license_resolve import LicenseResolver
    from releasekit.checks._license_graph import LicenseGraph

    graph = LicenseGraph.load()
    resolver = LicenseResolver(graph)

    r = resolver.resolve('MIT License')
    assert r.spdx_id == 'MIT'
    assert r.confidence == 1.0

    r = resolver.resolve('Apache 2')
    assert r.spdx_id == 'Apache-2.0'

    r = resolver.resolve('Apche-2.0')  # typo
    assert r.spdx_id == 'Apache-2.0'
    assert r.method == 'edit-distance'
"""

from __future__ import annotations

import functools
import re
import unicodedata
from dataclasses import dataclass

from releasekit.checks._license_graph import LicenseGraph

__all__ = [
    'LicenseResolver',
    'ResolvedLicense',
]

# Minimum trigram similarity ratio (0.0–1.0) to consider a match.
# Sørensen–Dice over trigrams scores lower than SequenceMatcher for
# equivalent similarity, so 0.55 here ≈ 0.75 with SequenceMatcher.
_MIN_SIMILARITY = 0.55

# Maximum number of suggestions to return for unresolved licenses.
_MAX_SUGGESTIONS = 3

# Pre-compiled regex for _normalize (avoid re-compiling per call).
_NORMALIZE_RE = re.compile(r'[^a-z0-9]')


def _trigrams(s: str) -> frozenset[str]:
    """Return the set of character trigrams for *s*.

    Trigram similarity is O(n) via set intersection, much faster than
    SequenceMatcher's O(n²) dynamic programming for fuzzy matching.
    """
    if len(s) < 3:
        return frozenset({s}) if s else frozenset()
    return frozenset(s[i : i + 3] for i in range(len(s) - 2))


def _trigram_similarity(a_tri: frozenset[str], b_tri: frozenset[str]) -> float:
    """Sørensen–Dice coefficient over trigram sets. Returns 0.0–1.0."""
    if not a_tri or not b_tri:
        return 0.0
    return 2.0 * len(a_tri & b_tri) / (len(a_tri) + len(b_tri))


@dataclass(frozen=True)
class ResolvedLicense:
    """Result of resolving a license string.

    Attributes:
        spdx_id: The canonical SPDX identifier, or ``""`` if unresolved.
        confidence: Confidence score from 0.0 to 1.0.
        method: How the resolution was achieved:
            ``"exact"``, ``"alias"``, ``"normalized"``,
            ``"edit-distance"``, or ``"unresolved"``.
        original: The original input string.
        suggestions: For unresolved/ambiguous cases, a list of
            ``(spdx_id, similarity)`` tuples of close matches.
    """

    spdx_id: str
    confidence: float
    method: str
    original: str
    suggestions: tuple[tuple[str, float], ...] = ()

    @property
    def resolved(self) -> bool:
        """``True`` if the license was successfully resolved."""
        return self.method != 'unresolved'


def _normalize(s: str) -> str:
    """Normalize a string for fuzzy comparison.

    - Lowercase.
    - Strip accents / diacritics.
    - Remove all non-alphanumeric characters.
    - Collapse whitespace.
    """
    s = s.lower().strip()
    # Decompose unicode and strip combining marks (accents).
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    # Remove non-alphanumeric (keep digits and letters).
    s = _NORMALIZE_RE.sub('', s)
    return s


class LicenseResolver:
    """Resolves messy license strings to canonical SPDX identifiers.

    Args:
        graph: A loaded :class:`LicenseGraph` providing the alias map.
    """

    def __init__(self, graph: LicenseGraph) -> None:
        self._graph = graph
        # Build lookup tables once.
        self._alias_map: dict[str, str] = graph.all_aliases()
        # Normalized form → SPDX ID.
        self._normalized_map: dict[str, str] = {}
        for spdx_id in graph.nodes:
            self._normalized_map[_normalize(spdx_id)] = spdx_id
        for alias, spdx_id in self._alias_map.items():
            norm = _normalize(alias)
            # First writer wins (SPDX ID takes priority over aliases).
            self._normalized_map.setdefault(norm, spdx_id)
        # Precompute trigram sets for all candidates (O(1) per query comparison).
        self._candidates: list[tuple[str, str, frozenset[str]]] = []
        for spdx_id in graph.nodes:
            low = spdx_id.lower()
            self._candidates.append((low, spdx_id, _trigrams(low)))
        for alias, spdx_id in self._alias_map.items():
            self._candidates.append((alias, spdx_id, _trigrams(alias)))
        # Bind the cached resolver (per-instance LRU cache).
        self._resolve_cached = functools.lru_cache(maxsize=512)(self._resolve_impl)

    def resolve(self, raw: str) -> ResolvedLicense:
        """Resolve a license string to a canonical SPDX ID.

        Results are LRU-cached (up to 512 unique inputs) so repeated
        lookups for the same string are O(1).

        Args:
            raw: The raw license string (e.g. ``"MIT License"``,
                ``"Apache 2"``, ``"Apche-2.0"``).

        Returns:
            A :class:`ResolvedLicense` with the result.
        """
        return self._resolve_cached(raw)

    def _resolve_impl(self, raw: str) -> ResolvedLicense:
        """Core resolution logic (called via LRU cache)."""
        if not raw or not raw.strip():
            return ResolvedLicense(
                spdx_id='',
                confidence=0.0,
                method='unresolved',
                original=raw,
            )

        stripped = raw.strip()

        # Stage 1: Exact match (case-insensitive against SPDX IDs).
        if stripped in self._graph.nodes:
            return ResolvedLicense(
                spdx_id=stripped,
                confidence=1.0,
                method='exact',
                original=raw,
            )

        # Stage 2: Alias match (case-insensitive).
        lower = stripped.lower()
        if lower in self._alias_map:
            return ResolvedLicense(
                spdx_id=self._alias_map[lower],
                confidence=1.0,
                method='alias',
                original=raw,
            )

        # Stage 3: Normalized match (strip punctuation/whitespace).
        norm = _normalize(stripped)
        if norm and norm in self._normalized_map:
            return ResolvedLicense(
                spdx_id=self._normalized_map[norm],
                confidence=0.95,
                method='normalized',
                original=raw,
            )

        # Stage 4: Trigram similarity match (Sørensen–Dice coefficient).
        best_matches = self._find_closest(lower)
        if best_matches:
            top_id, top_score = best_matches[0]
            # Check for ambiguity: if top two are from different SPDX IDs
            # and very close in score, flag it.
            if (
                len(best_matches) >= 2
                and best_matches[0][0] != best_matches[1][0]
                and best_matches[1][1] >= top_score - 0.05
            ):
                # Ambiguous — return with suggestions.
                return ResolvedLicense(
                    spdx_id=top_id,
                    confidence=top_score * 0.8,
                    method='edit-distance',
                    original=raw,
                    suggestions=tuple(best_matches[:_MAX_SUGGESTIONS]),
                )
            return ResolvedLicense(
                spdx_id=top_id,
                confidence=top_score * 0.9,
                method='edit-distance',
                original=raw,
            )

        # Stage 5: Unresolved.
        return ResolvedLicense(
            spdx_id='',
            confidence=0.0,
            method='unresolved',
            original=raw,
        )

    def _find_closest(self, query: str) -> list[tuple[str, float]]:
        """Find the closest SPDX IDs by trigram similarity.

        Uses Sørensen–Dice coefficient over character trigrams — O(n)
        per comparison via set intersection, vs O(n²) for SequenceMatcher.
        Trigram sets for all candidates are precomputed at init time.

        Returns a list of ``(spdx_id, similarity)`` sorted by
        descending similarity, filtered to those above the threshold.
        Deduplicates by SPDX ID (keeps highest score).
        """
        query_tri = _trigrams(query)
        scores: dict[str, float] = {}
        for _candidate, spdx_id, cand_tri in self._candidates:
            ratio = _trigram_similarity(query_tri, cand_tri)
            if ratio >= _MIN_SIMILARITY:
                if spdx_id not in scores or ratio > scores[spdx_id]:
                    scores[spdx_id] = ratio
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def resolve_all(self, raw_licenses: list[str]) -> list[ResolvedLicense]:
        """Resolve a list of license strings.

        Args:
            raw_licenses: List of raw license strings.

        Returns:
            List of :class:`ResolvedLicense` results in the same order.
        """
        return [self.resolve(r) for r in raw_licenses]
