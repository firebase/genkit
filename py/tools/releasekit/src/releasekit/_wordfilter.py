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

"""Aho-Corasick word filter for codename safety checking.

Uses the Aho-Corasick automaton for **O(n + m)** multi-pattern matching
in a single pass over the input text, where *n* is the text length and
*m* is the number of matches found.  This replaces the previous
regex-based blocklist with a data-structure approach that:

- Loads blocked words from a plain-text file (one per line).
- Supports **exact** whole-word matches (``kill``) and **prefix/stem**
  matches (``fuck*`` matches ``fuck``, ``fucking``, ``fucked``, …).
- Respects word boundaries so that ``"ass"`` does not match inside
  ``"Assassin"`` or ``"Classic"``.

How it works:

1. **Build** — Insert all blocked words into a character-level trie,
   then compute *failure links* via BFS (like KMP's failure function
   generalized to multiple patterns).  Each node also stores an
   *output link* pointing to the nearest terminal ancestor reachable
   through the failure chain.

2. **Search** — Walk the text character by character.  On mismatch,
   follow failure links (never backtrack in the text).  At each node,
   check the output chain for matches, verifying word-boundary
   constraints.

Complexity:

- **Build**: O(W) where W = total characters in all blocked words.
- **Query** (``contains_blocked``): O(n + m).
- **Space**: O(W) for the automaton.

The automaton is built once at module load time and reused for every
call.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib.resources
from collections import deque
from pathlib import Path
from typing import TextIO
from urllib.parse import urlparse

# Sentinel values stored in trie nodes.
_EXACT = 1  # Matches only at a word boundary after the last char.
_PREFIX = 2  # Matches the stem and any word-char continuation.


class _TrieNode:
    """A single node in the Aho-Corasick automaton."""

    __slots__ = ('children', 'match_type', 'depth', 'fail', 'output')

    def __init__(self, depth: int = 0) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.match_type: int = 0  # 0 = not a terminal
        self.depth: int = depth  # distance from root (= pattern length at terminal)
        self.fail: _TrieNode | None = None  # failure link
        self.output: _TrieNode | None = None  # output link (nearest terminal via fail chain)


class WordFilter:
    """Aho-Corasick blocked-word filter with word-boundary semantics.

    Example::

        wf = WordFilter.from_file(Path('blocked_words.txt'))
        wf.contains_blocked('Operation Kill Storm')  # True
        wf.contains_blocked('Skilled Artisan')  # False
    """

    def __init__(self) -> None:
        self._root = _TrieNode(depth=0)
        self._size = 0  # number of entries
        self._built = False  # whether failure links have been computed

    def add(self, entry: str) -> None:
        """Add a single entry to the filter.

        Args:
            entry: A blocked word.  Trailing ``*`` means prefix/stem
                match; otherwise exact whole-word match.
        """
        entry = entry.strip()
        if not entry:
            return

        if entry.endswith('*'):
            word = entry[:-1].lower()
            match_type = _PREFIX
        else:
            word = entry.lower()
            match_type = _EXACT

        if not word:
            return

        node = self._root
        for i, ch in enumerate(word):
            if ch not in node.children:
                node.children[ch] = _TrieNode(depth=i + 1)
            node = node.children[ch]

        # A prefix match subsumes an exact match on the same word.
        if match_type == _PREFIX or node.match_type == 0:
            node.match_type = match_type
        self._size += 1
        self._built = False  # invalidate automaton

    def _build(self) -> None:
        """Compute failure and output links via BFS (Aho-Corasick)."""
        root = self._root
        root.fail = root
        root.output = None

        queue: deque[_TrieNode] = deque()

        # Initialize depth-1 nodes: their failure links point to root.
        for child in root.children.values():
            child.fail = root
            child.output = None
            queue.append(child)

        # BFS to compute failure links for deeper nodes.
        while queue:
            node = queue.popleft()
            for ch, child in node.children.items():
                # Walk up the failure chain of `node` to find the
                # longest proper suffix that has a transition on `ch`.
                fail = node.fail
                assert fail is not None  # guaranteed by BFS initialization
                while fail is not root and ch not in fail.children:
                    assert fail.fail is not None  # root.fail == root, never None
                    fail = fail.fail
                child.fail = fail.children[ch] if ch in fail.children else root
                # Avoid self-loop (can happen for root's direct children).
                if child.fail is child:
                    child.fail = root

                # Output link: nearest terminal reachable via fail chain.
                f = child.fail
                if f.match_type != 0:
                    child.output = f
                else:
                    child.output = f.output

                queue.append(child)

        self._built = True

    @classmethod
    def from_lines(cls, lines: list[str]) -> WordFilter:
        """Build a filter from a list of entry strings.

        Applies safety limits:

        - Entries longer than :data:`_MAX_ENTRY_LENGTH` are silently
          skipped (prevents memory abuse via pathological trie depth).
        - At most :data:`_MAX_BLOCKLIST_ENTRIES` entries are loaded
          (prevents DoS via enormous files).
        - Non-printable / control characters (except ``*`` for prefix
          matching) are stripped from each entry.
        """
        wf = cls()
        count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            # Skip entries that are too long.
            if len(stripped) > _MAX_ENTRY_LENGTH:
                continue
            # Strip non-printable / control characters (keep * for prefix).
            sanitized = ''.join(ch for ch in stripped if ch.isprintable())
            if not sanitized:
                continue
            wf.add(sanitized)
            count += 1
            if count >= _MAX_BLOCKLIST_ENTRIES:
                break
        wf._build()
        return wf

    @classmethod
    def from_stream(cls, stream: TextIO) -> WordFilter:
        """Build a filter from a readable text stream."""
        return cls.from_lines(stream.readlines())

    @classmethod
    def from_file(cls, path: Path) -> WordFilter:
        """Build a filter by reading a blocked-words text file."""
        with path.open(encoding='utf-8') as f:
            return cls.from_stream(f)

    @classmethod
    async def from_url(cls, url: str) -> WordFilter:
        """Build a filter by fetching a blocked-words file from a URL.

        Accepted URL schemes:

        - ``https://`` — fetched directly.  HSTS is checked.
        - ``gs://bucket/path`` — converted to an HTTPS
          ``storage.googleapis.com`` URL and fetched.

        Plaintext HTTP is rejected to prevent MITM injection.
        The response body is capped at :data:`_MAX_REMOTE_SIZE` bytes.

        Args:
            url: HTTPS or ``gs://`` URL pointing to a blocked-words file.

        Returns:
            A new :class:`WordFilter` built from the remote file.

        Raises:
            ValueError: If the URL uses an unsupported scheme.
            httpx.HTTPStatusError: If the server returns a non-2xx status.
        """
        parsed = urlparse(url)
        if parsed.scheme == 'gs':
            fetch_url = _gcs_to_https(url)
        elif parsed.scheme == 'https':
            fetch_url = url
        else:
            msg = (
                f'Blocklist URLs must use HTTPS or gs:// (got {parsed.scheme!r}). '
                'Plaintext HTTP is rejected to prevent MITM injection.'
            )
            raise ValueError(msg)

        from releasekit.net import http_client, request_with_retry

        async with http_client() as client:
            response = await request_with_retry(client, 'GET', fetch_url)
            response.raise_for_status()
            _enforce_hsts(response.headers, fetch_url)
            if len(response.content) > _MAX_REMOTE_SIZE:
                msg = f'Remote blocklist too large: {len(response.content)} bytes (limit: {_MAX_REMOTE_SIZE} bytes).'
                raise ValueError(msg)
            lines = response.text.splitlines()
            return cls.from_lines(lines)

    def _check_match(self, node: _TrieNode, text: str, pos: int) -> bool:
        """Check if a terminal node represents a valid word-boundary match.

        Args:
            node: A terminal trie node (match_type != 0).
            text: The lowercased input text.
            pos: The current position in text (one past the last matched char).

        Returns:
            ``True`` if word-boundary constraints are satisfied.
        """
        n = len(text)
        start = pos - node.depth

        # Left boundary: start must be at position 0 or preceded by
        # a non-alphanumeric character.
        if start > 0 and text[start - 1].isalnum():
            return False

        if node.match_type == _PREFIX:
            # Prefix/stem: left boundary is sufficient.
            return True

        # Exact: also need a right boundary.
        return pos >= n or not text[pos].isalnum()

    def contains_blocked(self, text: str) -> bool:
        """Return ``True`` if *text* contains any blocked word.

        Scans the text in a **single pass** using the Aho-Corasick
        automaton.  Matching respects word boundaries:

        - **Exact** entries match only when the matched substring is
          surrounded by non-word characters (or string edges).
        - **Prefix** entries match when the stem starts at a word
          boundary.  The stem may be followed by additional word
          characters (e.g. ``fuck*`` matches ``fucking``).

        Args:
            text: The text to scan (e.g. a codename or tagline).

        Returns:
            ``True`` if a blocked word is found, ``False`` otherwise.
        """
        if not text:
            return False

        if not self._built:
            self._build()

        lower = text.lower()
        n = len(lower)
        node = self._root
        root = self._root

        for i in range(n):
            ch = lower[i]

            # Follow failure links until we find a transition or reach root.
            while node is not root and ch not in node.children:
                assert node.fail is not None  # always set after _build()
                node = node.fail

            if ch in node.children:
                node = node.children[ch]
            # else: node is root, no transition — continue.

            pos = i + 1  # one past the last matched character

            # Check this node and its output chain for matches.
            check: _TrieNode | None = node
            while check is not None and check is not root:
                if check.match_type != 0:
                    if self._check_match(check, lower, pos):
                        return True
                check = check.output

        return False

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0


def _is_url(value: str) -> bool:
    """Return ``True`` if *value* is a remote blocklist URL.

    Accepted schemes:

    - ``https://`` — standard HTTPS endpoints.
    - ``gs://`` — Google Cloud Storage buckets (converted to HTTPS
      via ``storage.googleapis.com`` at fetch time).

    Plaintext HTTP is rejected to prevent MITM injection.
    """
    try:
        parsed = urlparse(value)
        return parsed.scheme in ('https', 'gs') and bool(parsed.netloc)
    except ValueError:
        return False


def _is_gcs_url(value: str) -> bool:
    """Return ``True`` if *value* is a ``gs://`` Cloud Storage URL."""
    try:
        parsed = urlparse(value)
        return parsed.scheme == 'gs' and bool(parsed.netloc)
    except ValueError:
        return False


def _gcs_to_https(gs_url: str) -> str:
    """Convert ``gs://bucket/path`` to an HTTPS ``storage.googleapis.com`` URL.

    Example::

        >>> _gcs_to_https('gs://my-bucket/blocklists/words.txt')
        'https://storage.googleapis.com/my-bucket/blocklists/words.txt'
    """
    parsed = urlparse(gs_url)
    bucket = parsed.netloc
    path = parsed.path.lstrip('/')
    return f'https://storage.googleapis.com/{bucket}/{path}' if path else f'https://storage.googleapis.com/{bucket}'


# Hosts that are exempt from the HSTS requirement by default.
# ``storage.googleapis.com`` is exempt because ``gs://`` URLs are
# converted to this host and GCS does not always send HSTS headers.
_HSTS_EXEMPT_HOSTS: frozenset[str] = frozenset({
    'storage.googleapis.com',
})


def _enforce_hsts(
    headers: dict[str, str] | object,
    url: str,
    *,
    exempt_hosts: frozenset[str] = _HSTS_EXEMPT_HOSTS,
) -> None:
    """Warn if the server does not send a ``Strict-Transport-Security`` header.

    HSTS tells the client to *always* use HTTPS for this host in the
    future, preventing protocol-downgrade attacks.  We log a warning
    rather than raising because some internal servers or GCS may not
    set the header.

    Args:
        headers: Response headers (any object with a ``.get()`` method).
        url: The URL that was fetched (for logging).
        exempt_hosts: Set of hostnames that are exempt from the HSTS
            check.  Defaults to :data:`_HSTS_EXEMPT_HOSTS` which
            includes ``storage.googleapis.com``.
    """
    # Skip check for exempt hosts.
    try:
        parsed = urlparse(url)
        if parsed.hostname and parsed.hostname in exempt_hosts:
            return
    except ValueError:
        pass

    from releasekit.logging import get_logger

    log = get_logger('releasekit._wordfilter')

    hsts = None
    if hasattr(headers, 'get'):
        hsts = headers.get('strict-transport-security')  # type: ignore[union-attr]
    if not hsts:
        log.warning(
            'blocklist_missing_hsts',
            url=url,
            hint=(
                'Remote blocklist server does not send a '
                'Strict-Transport-Security header. Consider '
                'enabling HSTS on the server to prevent '
                'protocol-downgrade attacks.'
            ),
        )


# Maximum number of entries allowed in a single blocklist file.
_MAX_BLOCKLIST_ENTRIES: int = 50_000
# Maximum length of a single blocklist entry (characters).
_MAX_ENTRY_LENGTH: int = 200
# Maximum response size for remote blocklist files (bytes).
_MAX_REMOTE_SIZE: int = 5 * 1024 * 1024  # 5 MiB


@dataclasses.dataclass(frozen=True)
class RemoteBlocklistConfig:
    """Configuration for remote blocklist fetching.

    All fields have sensible defaults.  Pass an instance to
    :func:`get_filter_async` to override any of them.

    Attributes:
        max_size: Maximum response body size in bytes.
        max_entries: Maximum number of blocklist entries to load.
        max_entry_length: Maximum length of a single entry in characters.
        hsts_exempt_hosts: Hostnames exempt from the HSTS header check.
    """

    max_size: int = _MAX_REMOTE_SIZE
    max_entries: int = _MAX_BLOCKLIST_ENTRIES
    max_entry_length: int = _MAX_ENTRY_LENGTH
    hsts_exempt_hosts: frozenset[str] = _HSTS_EXEMPT_HOSTS


@dataclasses.dataclass
class _RemoteCacheEntry:
    """Per-URL cache entry for HTTP 304 conditional requests."""

    etag: str = ''
    last_modified: str = ''
    sha256: str = ''
    words: frozenset[str] = dataclasses.field(default_factory=frozenset)
    wf: WordFilter | None = None


_default_filter: WordFilter | None = None
_custom_filters: dict[str, WordFilter] = {}
_remote_cache: dict[str, _RemoteCacheEntry] = {}


def _builtin_words_path() -> Path:
    """Return the path to the bundled ``blocked_words.txt``."""
    return Path(str(importlib.resources.files('releasekit') / 'data' / 'blocked_words.txt'))


def _load_builtin_into(wf: WordFilter) -> None:
    """Load built-in blocked words into an existing :class:`WordFilter`."""
    builtin_path = _builtin_words_path()
    if builtin_path.exists():
        with builtin_path.open(encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    wf.add(stripped)


def get_default_filter() -> WordFilter:
    """Return the shared :class:`WordFilter` loaded from ``blocked_words.txt``.

    The filter is built once on first call and cached for the lifetime
    of the process.  All modules that need safety filtering should use
    :func:`get_filter` (which accepts an optional custom blocklist)
    rather than calling this directly.
    """
    global _default_filter  # noqa: PLW0603
    if _default_filter is None:
        _default_filter = WordFilter.from_file(_builtin_words_path())
    return _default_filter


def get_filter(blocklist_file: str = '', workspace_root: Path | None = None) -> WordFilter:
    """Return a :class:`WordFilter` that merges the built-in list with an optional custom file.

    When *blocklist_file* is empty (the default), this returns the same
    singleton as :func:`get_default_filter`.  When a custom file is
    specified, the built-in words and the custom words are merged into a
    single filter, cached by resolved path so the merge only happens once.

    For URL-based blocklists, use :func:`get_filter_async` instead.

    Args:
        blocklist_file: Relative or absolute path to a custom
            blocked-words file.  Resolved against *workspace_root*
            when relative.  Empty string means no custom file.
        workspace_root: Directory to resolve *blocklist_file* against.
            Ignored when *blocklist_file* is empty or absolute.

    Returns:
        A :class:`WordFilter` containing the union of built-in and
        custom blocked words.

    Raises:
        FileNotFoundError: If *blocklist_file* is set but does not exist.
        ValueError: If *blocklist_file* is a URL (use :func:`get_filter_async`).
    """
    if not blocklist_file:
        return get_default_filter()

    if _is_url(blocklist_file):
        msg = f'blocklist_file is a URL ({blocklist_file}). Use get_filter_async() for URL-based blocklists.'
        raise ValueError(msg)

    custom_path = Path(blocklist_file)
    if not custom_path.is_absolute() and workspace_root is not None:
        custom_path = workspace_root / custom_path
    custom_path = custom_path.resolve()

    cache_key = str(custom_path)
    if cache_key in _custom_filters:
        return _custom_filters[cache_key]

    # Build a merged filter: built-in words + custom words.
    merged = WordFilter()
    _load_builtin_into(merged)

    # Load custom words (extends the built-in list).
    if not custom_path.exists():
        msg = f'Custom blocklist file not found: {custom_path}'
        raise FileNotFoundError(msg)
    with custom_path.open(encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                merged.add(stripped)

    merged._build()  # noqa: SLF001 — internal API, build the automaton
    _custom_filters[cache_key] = merged
    return merged


def _resolve_fetch_url(blocklist_file: str) -> str:
    """Resolve *blocklist_file* to an HTTPS fetch URL.

    ``gs://`` URLs are converted via :func:`_gcs_to_https`.
    ``https://`` URLs are returned as-is.
    All other schemes raise :class:`ValueError`.
    """
    parsed = urlparse(blocklist_file)
    if parsed.scheme == 'gs':
        return _gcs_to_https(blocklist_file)
    if parsed.scheme == 'https':
        return blocklist_file
    msg = (
        f'Blocklist URLs must use HTTPS or gs:// (got {parsed.scheme!r}). '
        'Plaintext HTTP is rejected to prevent MITM injection.'
    )
    raise ValueError(msg)


def _parse_remote_words(
    text: str,
    cfg: RemoteBlocklistConfig,
) -> frozenset[str]:
    """Parse and sanitize blocklist text into a frozen set of words."""
    words: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if len(stripped) > cfg.max_entry_length:
            continue
        sanitized = ''.join(ch for ch in stripped if ch.isprintable())
        if not sanitized:
            continue
        words.append(sanitized)
        if len(words) >= cfg.max_entries:
            break
    return frozenset(words)


def _log_blocklist_diff(
    url: str,
    old_words: frozenset[str],
    new_words: frozenset[str],
    old_sha: str,
    new_sha: str,
) -> None:
    """Log a warning with the diff when a remote blocklist changes."""
    from releasekit.logging import get_logger

    log = get_logger('releasekit._wordfilter')

    added = sorted(new_words - old_words)
    removed = sorted(old_words - new_words)

    diff_lines: list[str] = []
    for w in added:
        diff_lines.append(f'+ {w}')
    for w in removed:
        diff_lines.append(f'- {w}')
    diff_text = '\n'.join(diff_lines) if diff_lines else '(no entry changes)'

    log.warning(
        'blocklist_checksum_changed',
        url=url,
        old_sha256=old_sha,
        new_sha256=new_sha,
        added_count=len(added),
        removed_count=len(removed),
        diff=diff_text,
        hint=(
            'The remote blocklist content has changed. Review the diff to ensure no malicious entries were injected.'
        ),
    )


async def _fetch_remote_blocklist(
    fetch_url: str,
    original_url: str,
    cfg: RemoteBlocklistConfig,
) -> frozenset[str]:
    """Fetch a remote blocklist with HTTP 304 caching and checksum tracking.

    Uses ``If-None-Match`` / ``If-Modified-Since`` headers for
    conditional requests.  When the server returns 304 Not Modified,
    the cached word set is returned without re-parsing.

    When content changes, the SHA-256 checksum is compared to the
    previous fetch.  If it differs, a warning with a diff is logged.

    Args:
        fetch_url: The resolved HTTPS URL to fetch.
        original_url: The original URL (for cache key / logging).
        cfg: Remote blocklist configuration.

    Returns:
        A frozen set of sanitized blocklist words.
    """
    from releasekit.net import http_client, request_with_retry

    cached = _remote_cache.get(original_url)

    # Build conditional request headers.
    extra_headers: dict[str, str] = {}
    if cached:
        if cached.etag:
            extra_headers['If-None-Match'] = cached.etag
        if cached.last_modified:
            extra_headers['If-Modified-Since'] = cached.last_modified

    async with http_client() as client:
        response = await request_with_retry(
            client,
            'GET',
            fetch_url,
            headers=extra_headers,
        )

        # 304 Not Modified — return cached words.
        if response.status_code == 304 and cached is not None:
            return cached.words

        response.raise_for_status()
        _enforce_hsts(
            response.headers,
            fetch_url,
            exempt_hosts=cfg.hsts_exempt_hosts,
        )

        if len(response.content) > cfg.max_size:
            msg = f'Remote blocklist too large: {len(response.content)} bytes (limit: {cfg.max_size} bytes).'
            raise ValueError(msg)

        # Parse words and compute checksum.
        new_words = _parse_remote_words(response.text, cfg)
        new_sha = hashlib.sha256(response.content).hexdigest()

        # Check for checksum change.
        if cached and cached.sha256 and cached.sha256 != new_sha:
            _log_blocklist_diff(
                original_url,
                cached.words,
                new_words,
                cached.sha256,
                new_sha,
            )

        # Update cache entry.
        etag = ''
        last_modified = ''
        if hasattr(response.headers, 'get'):
            etag = response.headers.get('etag', '') or ''
            last_modified = response.headers.get('last-modified', '') or ''

        _remote_cache[original_url] = _RemoteCacheEntry(
            etag=etag,
            last_modified=last_modified,
            sha256=new_sha,
            words=new_words,
        )

        return new_words


async def get_filter_async(
    blocklist_file: str = '',
    workspace_root: Path | None = None,
    *,
    config: RemoteBlocklistConfig | None = None,
) -> WordFilter:
    """Return a :class:`WordFilter`, loading from a URL or local file.

    Like :func:`get_filter`, but also supports HTTPS and ``gs://``
    URLs for *blocklist_file*.  Plaintext HTTP is rejected to prevent
    MITM injection.  HSTS is checked on the response.

    Remote blocklists use HTTP 304 conditional requests (ETag /
    Last-Modified) to avoid re-downloading unchanged content.  When
    content *does* change, the SHA-256 checksum is compared and a
    warning with a diff of added/removed entries is logged.

    For local files, this delegates to :func:`get_filter` (synchronous).

    Args:
        blocklist_file: Path, HTTPS URL, or ``gs://`` URL to a custom
            blocked-words file.  Empty string means no custom file
            (built-in only).
        workspace_root: Directory to resolve local paths against.
        config: Optional :class:`RemoteBlocklistConfig` to override
            default limits (max_size, max_entries, etc.).

    Returns:
        A :class:`WordFilter` containing the union of built-in and
        custom blocked words.

    Raises:
        ValueError: If *blocklist_file* is a non-HTTPS/non-gs URL.
    """
    if not blocklist_file:
        return get_default_filter()

    if not _is_url(blocklist_file):
        return get_filter(blocklist_file, workspace_root)

    cfg = config or RemoteBlocklistConfig()
    fetch_url = _resolve_fetch_url(blocklist_file)

    # Fetch (or revalidate) remote words.
    remote_words = await _fetch_remote_blocklist(
        fetch_url,
        blocklist_file,
        cfg,
    )

    # Check if we already have a built filter for this exact word set.
    cached_entry = _remote_cache.get(blocklist_file)
    if cached_entry and cached_entry.wf is not None and cached_entry.words == remote_words:
        return cached_entry.wf

    # Build a merged filter: built-in words + remote words.
    merged = WordFilter()
    _load_builtin_into(merged)
    for word in remote_words:
        merged.add(word)
    merged._build()  # noqa: SLF001 — internal API, build the automaton

    # Store the built filter in the cache entry.
    if cached_entry:
        cached_entry.wf = merged

    _custom_filters[blocklist_file] = merged
    return merged
