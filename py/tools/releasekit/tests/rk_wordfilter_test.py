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

"""Tests for the trie-based WordFilter used in codename safety checking."""

from __future__ import annotations

import importlib.resources
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from releasekit._wordfilter import (
    WordFilter,
    _enforce_hsts,
    _gcs_to_https,
    _is_gcs_url,
    _is_url,
    get_default_filter,
    get_filter,
    get_filter_async,
)


class TestWordFilterConstruction:
    """Tests for building a WordFilter."""

    def test_empty_filter(self) -> None:
        """Test empty filter."""
        wf = WordFilter()
        assert len(wf) == 0
        assert not wf

    def test_from_lines_skips_comments_and_blanks(self) -> None:
        """Test from lines skips comments and blanks."""
        lines = [
            '# comment',
            '',
            '  ',
            'foo',
            '  # another comment  ',
            'bar',
        ]
        wf = WordFilter.from_lines(lines)
        assert len(wf) == 2
        assert wf

    def test_from_lines_exact(self) -> None:
        """Test from lines exact."""
        wf = WordFilter.from_lines(['foo', 'bar'])
        assert wf.contains_blocked('foo')
        assert wf.contains_blocked('bar')

    def test_from_lines_prefix(self) -> None:
        """Test from lines prefix."""
        wf = WordFilter.from_lines(['quux*'])
        assert wf.contains_blocked('quux')
        assert wf.contains_blocked('quuxing')
        assert wf.contains_blocked('quuxed')

    def test_from_file(self, tmp_path: Path) -> None:
        """Test from file."""
        f = tmp_path / 'words.txt'
        f.write_text('foo\nbar\nquux*\n', encoding='utf-8')
        wf = WordFilter.from_file(f)
        assert len(wf) == 3
        assert wf.contains_blocked('foo')
        assert wf.contains_blocked('quuxing')

    def test_from_stream(self, tmp_path: Path) -> None:
        """Test from stream."""
        f = tmp_path / 'words.txt'
        f.write_text('# header\nfoo\n\nbar\n', encoding='utf-8')
        with f.open(encoding='utf-8') as stream:
            wf = WordFilter.from_stream(stream)
        assert len(wf) == 2

    def test_add_empty_string_ignored(self) -> None:
        """Test add empty string ignored."""
        wf = WordFilter()
        wf.add('')
        wf.add('   ')
        assert len(wf) == 0

    def test_add_star_only_ignored(self) -> None:
        """Test add star only ignored."""
        wf = WordFilter()
        wf.add('*')
        assert len(wf) == 0


class TestExactMatching:
    """Tests for exact (non-prefix) word matching."""

    def test_standalone_word(self) -> None:
        """Test standalone word."""
        wf = WordFilter.from_lines(['foo'])
        assert wf.contains_blocked('foo')

    def test_case_insensitive(self) -> None:
        """Test case insensitive."""
        wf = WordFilter.from_lines(['foo'])
        assert wf.contains_blocked('Foo')
        assert wf.contains_blocked('FOO')
        assert wf.contains_blocked('fOo')

    def test_word_in_phrase(self) -> None:
        """Test word in phrase."""
        wf = WordFilter.from_lines(['foo'])
        assert wf.contains_blocked('Operation Foo Storm')
        assert wf.contains_blocked('foo the bug')
        assert wf.contains_blocked('must foo')

    def test_no_substring_match(self) -> None:
        """Test no substring match."""
        wf = WordFilter.from_lines(['bar'])
        assert not wf.contains_blocked('rebar')
        assert not wf.contains_blocked('barley')
        assert not wf.contains_blocked('embargo')

    def test_word_boundary_at_start(self) -> None:
        """Test word boundary at start."""
        wf = WordFilter.from_lines(['zap'])
        assert wf.contains_blocked('zap')
        assert not wf.contains_blocked('Zapata')
        assert not wf.contains_blocked('unzap')

    def test_word_boundary_at_end(self) -> None:
        """Test word boundary at end."""
        wf = WordFilter.from_lines(['baz'])
        assert wf.contains_blocked('baz')
        assert wf.contains_blocked('Project Baz')
        assert not wf.contains_blocked('bazaar')
        assert not wf.contains_blocked('bazooka')

    def test_word_boundary_with_punctuation(self) -> None:
        """Test word boundary with punctuation."""
        wf = WordFilter.from_lines(['foo'])
        assert wf.contains_blocked('foo!')
        assert wf.contains_blocked('(foo)')
        assert wf.contains_blocked('foo, bar')
        assert wf.contains_blocked('the-foo-zone')

    def test_word_boundary_with_hyphens(self) -> None:
        """Test word boundary with hyphens."""
        wf = WordFilter.from_lines(['nix'])
        assert wf.contains_blocked('Nix Fire')
        assert wf.contains_blocked('nix-fire')
        assert not wf.contains_blocked('Nixcraft')
        assert not wf.contains_blocked('unix')

    def test_empty_text(self) -> None:
        """Test empty text."""
        wf = WordFilter.from_lines(['foo'])
        assert not wf.contains_blocked('')
        assert not wf.contains_blocked(None)  # type: ignore[arg-type]

    def test_no_match(self) -> None:
        """Test no match."""
        wf = WordFilter.from_lines(['foo', 'bar'])
        assert not wf.contains_blocked('Denali')
        assert not wf.contains_blocked('Rainier')
        assert not wf.contains_blocked('Andromeda')


class TestPrefixMatching:
    """Tests for prefix/stem matching (entries ending with *)."""

    def test_stem_exact(self) -> None:
        """Test stem exact."""
        wf = WordFilter.from_lines(['quux*'])
        assert wf.contains_blocked('quux')

    def test_stem_with_suffix(self) -> None:
        """Test stem with suffix."""
        wf = WordFilter.from_lines(['quux*'])
        assert wf.contains_blocked('quuxing')
        assert wf.contains_blocked('quuxed')
        assert wf.contains_blocked('quuxer')
        assert wf.contains_blocked('quuxery')

    def test_stem_case_insensitive(self) -> None:
        """Test stem case insensitive."""
        wf = WordFilter.from_lines(['quux*'])
        assert wf.contains_blocked('QUUXING')
        assert wf.contains_blocked('Quuxed')

    def test_stem_in_phrase(self) -> None:
        """Test stem in phrase."""
        wf = WordFilter.from_lines(['waldo*'])
        assert wf.contains_blocked('waldoing release')
        assert wf.contains_blocked('total waldo')

    def test_stem_word_boundary(self) -> None:
        """Test stem word boundary."""
        wf = WordFilter.from_lines(['grault*'])
        assert wf.contains_blocked('graulting')
        assert wf.contains_blocked('graulted')
        assert wf.contains_blocked('grault')

    def test_stem_no_substring_match(self) -> None:
        """Test stem no substring match."""
        wf = WordFilter.from_lines(['corge*'])
        assert wf.contains_blocked('corgeous')
        assert wf.contains_blocked('corge')
        # 'corge' should not match inside a word that doesn't start at boundary
        assert not wf.contains_blocked('Scorgeon')

    def test_prefix_subsumes_exact(self) -> None:
        """Test prefix subsumes exact."""
        wf = WordFilter.from_lines(['quux', 'quux*'])
        assert wf.contains_blocked('quux')
        assert wf.contains_blocked('quuxing')


class TestMultipleEntries:
    """Tests with multiple blocked words."""

    def test_any_match_returns_true(self) -> None:
        """Test any match returns true."""
        wf = WordFilter.from_lines(['foo', 'bar', 'baz'])
        assert wf.contains_blocked('bar fight')
        assert wf.contains_blocked('top baz')
        assert wf.contains_blocked('foo bill')

    def test_mixed_exact_and_prefix(self) -> None:
        """Test mixed exact and prefix."""
        wf = WordFilter.from_lines(['foo', 'quux*', 'bar'])
        assert wf.contains_blocked('foo')
        assert wf.contains_blocked('quuxing')
        assert wf.contains_blocked('bar')
        assert not wf.contains_blocked('Denali')


class TestBlockedWordsFile:
    """Tests that the shipped blocked_words.txt loads without error.

    The actual word list is maintained separately and reviewed via its
    own PR.  These tests only verify structural correctness of the file
    and the loading path — they do NOT assert specific blocked words.
    """

    def test_file_loads_without_error(self) -> None:
        """Test file loads without error."""
        path = importlib.resources.files('releasekit') / 'data' / 'blocked_words.txt'
        wf = WordFilter.from_file(Path(str(path)))
        # File should parse without raising; size depends on word list content.
        assert isinstance(wf, WordFilter)

    def test_get_default_filter_returns_singleton(self) -> None:
        """Test get default filter returns singleton."""
        f1 = get_default_filter()
        f2 = get_default_filter()
        assert f1 is f2


class TestGetFilter:
    """Tests for get_filter() with optional custom blocklist files."""

    def test_empty_blocklist_file_returns_default(self) -> None:
        """Test empty blocklist file returns default."""
        wf = get_filter('')
        assert wf is get_default_filter()

    def test_none_workspace_root_returns_default(self) -> None:
        """Test none workspace root returns default."""
        wf = get_filter('', workspace_root=None)
        assert wf is get_default_filter()

    def test_custom_file_merges_with_builtin(self, tmp_path: Path) -> None:
        """Test custom file merges with builtin."""
        custom = tmp_path / 'extra.txt'
        custom.write_text('xyzzy\nplugh*\n', encoding='utf-8')
        wf = get_filter(str(custom))
        # Custom words are present.
        assert wf.contains_blocked('xyzzy')
        assert wf.contains_blocked('plughish')

    def test_custom_file_relative_to_workspace_root(self, tmp_path: Path) -> None:
        """Test custom file relative to workspace root."""
        custom = tmp_path / 'my_blocklist.txt'
        custom.write_text('wibble\n', encoding='utf-8')
        wf = get_filter('my_blocklist.txt', workspace_root=tmp_path)
        assert wf.contains_blocked('wibble')

    def test_custom_file_cached_by_resolved_path(self, tmp_path: Path) -> None:
        """Test custom file cached by resolved path."""
        custom = tmp_path / 'cached.txt'
        custom.write_text('thud\n', encoding='utf-8')
        wf1 = get_filter(str(custom))
        wf2 = get_filter(str(custom))
        assert wf1 is wf2

    def test_missing_custom_file_raises(self, tmp_path: Path) -> None:
        """Test missing custom file raises."""
        with pytest.raises(FileNotFoundError, match='Custom blocklist file not found'):
            get_filter(str(tmp_path / 'nonexistent.txt'))

    def test_url_raises_value_error(self) -> None:
        """get_filter() with a URL should raise ValueError."""
        with pytest.raises(ValueError, match='Use get_filter_async'):
            get_filter('https://example.com/blocklist.txt')


class TestIsUrl:
    """Tests for the _is_url helper."""

    def test_https_url(self) -> None:
        """Https url."""
        assert _is_url('https://example.com/blocklist.txt') is True

    def test_http_url_rejected(self) -> None:
        """Http url rejected."""
        assert _is_url('http://internal.corp/words.txt') is False

    def test_local_path(self) -> None:
        """Local path."""
        assert _is_url('/home/user/blocklist.txt') is False

    def test_relative_path(self) -> None:
        """Relative path."""
        assert _is_url('custom_blocklist.txt') is False

    def test_empty_string(self) -> None:
        """Empty string."""
        assert _is_url('') is False

    def test_ftp_not_supported(self) -> None:
        """Ftp not supported."""
        assert _is_url('ftp://example.com/file.txt') is False

    def test_gs_url(self) -> None:
        """Gs url."""
        assert _is_url('gs://my-bucket/blocklist.txt') is True

    def test_gs_bucket_only(self) -> None:
        """Gs bucket only."""
        assert _is_url('gs://my-bucket') is True


class TestIsGcsUrl:
    """Tests for the _is_gcs_url helper."""

    def test_gs_url(self) -> None:
        """Gs url."""
        assert _is_gcs_url('gs://my-bucket/path/words.txt') is True

    def test_https_not_gcs(self) -> None:
        """Https not gcs."""
        assert _is_gcs_url('https://example.com/words.txt') is False

    def test_empty(self) -> None:
        """Empty."""
        assert _is_gcs_url('') is False


class TestGcsToHttps:
    """Tests for the _gcs_to_https helper."""

    def test_bucket_and_path(self) -> None:
        """Bucket and path."""
        result = _gcs_to_https('gs://my-bucket/blocklists/words.txt')
        assert result == 'https://storage.googleapis.com/my-bucket/blocklists/words.txt'

    def test_bucket_only(self) -> None:
        """Bucket only."""
        result = _gcs_to_https('gs://my-bucket')
        assert result == 'https://storage.googleapis.com/my-bucket'

    def test_nested_path(self) -> None:
        """Nested path."""
        result = _gcs_to_https('gs://corp-bucket/safety/v2/blocked.txt')
        assert result == 'https://storage.googleapis.com/corp-bucket/safety/v2/blocked.txt'


class TestEnforceHsts:
    """Tests for the _enforce_hsts helper."""

    def test_hsts_present_no_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No warning when HSTS header is present."""
        from unittest.mock import MagicMock

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)
        headers = {'strict-transport-security': 'max-age=31536000'}
        _enforce_hsts(headers, 'https://example.com/words.txt')
        mock_log.warning.assert_not_called()

    def test_hsts_missing_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Warning logged when HSTS header is missing."""
        from unittest.mock import MagicMock

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)
        headers: dict[str, str] = {}
        _enforce_hsts(headers, 'https://example.com/words.txt')
        mock_log.warning.assert_called_once()
        assert mock_log.warning.call_args[0][0] == 'blocklist_missing_hsts'

    def test_hsts_empty_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Warning logged when HSTS header is empty string."""
        from unittest.mock import MagicMock

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)
        headers = {'strict-transport-security': ''}
        _enforce_hsts(headers, 'https://example.com/words.txt')
        mock_log.warning.assert_called_once()

    def test_no_get_method_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Warning logged when headers object has no get method."""
        from unittest.mock import MagicMock

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)
        _enforce_hsts(object(), 'https://example.com/words.txt')
        mock_log.warning.assert_called_once()

    def test_gcs_host_exempt_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """storage.googleapis.com is exempt from HSTS by default."""
        from unittest.mock import MagicMock

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)
        headers: dict[str, str] = {}
        _enforce_hsts(headers, 'https://storage.googleapis.com/bucket/words.txt')
        mock_log.warning.assert_not_called()

    def test_custom_exempt_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Custom exempt_hosts skips HSTS check for that host."""
        from unittest.mock import MagicMock

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)
        headers: dict[str, str] = {}
        _enforce_hsts(
            headers,
            'https://internal.corp/words.txt',
            exempt_hosts=frozenset({'internal.corp'}),
        )
        mock_log.warning.assert_not_called()

    def test_non_exempt_host_still_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-exempt host without HSTS still warns."""
        from unittest.mock import MagicMock

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)
        headers: dict[str, str] = {}
        _enforce_hsts(
            headers,
            'https://other.example.com/words.txt',
            exempt_hosts=frozenset({'internal.corp'}),
        )
        mock_log.warning.assert_called_once()

    def test_empty_exempt_hosts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty exempt_hosts means all hosts are checked."""
        from unittest.mock import MagicMock

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)
        headers: dict[str, str] = {}
        _enforce_hsts(
            headers,
            'https://storage.googleapis.com/bucket/words.txt',
            exempt_hosts=frozenset(),
        )
        mock_log.warning.assert_called_once()


class TestBlocklistInjectionHardening:
    """Tests that blocklist parsing is safe against injection attacks."""

    def test_control_characters_stripped(self) -> None:
        """Non-printable / control characters are stripped from entries."""
        wf = WordFilter.from_lines(['bad\x00word', 'evi\x01l'])
        assert wf.contains_blocked('badword')
        assert wf.contains_blocked('evil')

    def test_null_bytes_in_entry(self) -> None:
        """Null bytes don't break parsing or cause trie corruption."""
        wf = WordFilter.from_lines(['\x00', '\x00\x00\x00', 'real'])
        # Null-only entries are stripped to empty and skipped.
        assert not wf.contains_blocked('\x00')
        assert wf.contains_blocked('real')

    def test_oversized_entry_skipped(self) -> None:
        """Entries longer than _MAX_ENTRY_LENGTH are silently skipped."""
        long_word = 'a' * 201
        wf = WordFilter.from_lines([long_word, 'short'])
        assert not wf.contains_blocked(long_word)
        assert wf.contains_blocked('short')

    def test_max_entry_count_enforced(self) -> None:
        """At most _MAX_BLOCKLIST_ENTRIES entries are loaded."""
        from releasekit._wordfilter import _MAX_BLOCKLIST_ENTRIES

        lines = [f'word{i}' for i in range(_MAX_BLOCKLIST_ENTRIES + 100)]
        wf = WordFilter.from_lines(lines)
        assert len(wf) == _MAX_BLOCKLIST_ENTRIES

    def test_comment_lines_ignored(self) -> None:
        """Lines starting with # are treated as comments."""
        wf = WordFilter.from_lines(['# this is a comment', 'real'])
        assert not wf.contains_blocked('comment')
        assert wf.contains_blocked('real')
        assert len(wf) == 1

    def test_empty_and_whitespace_lines_ignored(self) -> None:
        """Empty and whitespace-only lines are skipped."""
        wf = WordFilter.from_lines(['', '   ', '\t', 'real'])
        assert wf.contains_blocked('real')
        assert len(wf) == 1

    def test_unicode_normalization_attack(self) -> None:
        """Unicode lookalikes don't bypass the filter."""
        # Add the ASCII word, then check a lookalike doesn't match.
        wf = WordFilter.from_lines(['kill'])
        assert wf.contains_blocked('kill')
        # Cyrillic к (U+043A) looks like Latin k but is a different char.
        assert not wf.contains_blocked('\u043aill')

    @pytest.mark.asyncio
    async def test_from_url_rejects_http(self) -> None:
        """from_url() rejects plaintext HTTP URLs."""
        with pytest.raises(ValueError, match='HTTPS or gs://'):
            await WordFilter.from_url('http://evil.com/blocklist.txt')

    @pytest.mark.asyncio
    async def test_from_url_rejects_ftp(self) -> None:
        """from_url() rejects non-HTTPS schemes."""
        with pytest.raises(ValueError, match='HTTPS or gs://'):
            await WordFilter.from_url('ftp://evil.com/blocklist.txt')

    @pytest.mark.asyncio
    async def test_from_url_accepts_gs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_url() accepts gs:// URLs and converts to HTTPS."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx

        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.text = 'gcsword\n'
        fake_response.content = b'gcsword\n'
        fake_response.raise_for_status = MagicMock()
        fake_response.headers = {'strict-transport-security': 'max-age=31536000'}

        fake_client = AsyncMock()

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        mock_request = AsyncMock(return_value=fake_response)
        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr('releasekit.net.request_with_retry', mock_request)

        wf = await WordFilter.from_url('gs://my-bucket/words.txt')
        assert wf.contains_blocked('gcsword')
        # Verify the actual fetch URL was the HTTPS conversion.
        call_args = mock_request.call_args
        assert 'storage.googleapis.com/my-bucket/words.txt' in call_args[0][2]

    def test_path_traversal_in_entry(self) -> None:
        """Path traversal sequences in entries are harmless (just trie data)."""
        wf = WordFilter.from_lines(['../../../etc/passwd', '..\\windows'])
        # These are just strings in the trie, not file paths.
        assert wf.contains_blocked('../../../etc/passwd')
        assert len(wf) == 2

    def test_html_script_injection_harmless(self) -> None:
        """HTML/script tags in entries are just trie data, not executed."""
        wf = WordFilter.from_lines(['<script>alert(1)</script>', 'normal'])
        assert wf.contains_blocked('<script>alert(1)</script>')
        assert wf.contains_blocked('normal')


class TestGetFilterAsync:
    """Tests for get_filter_async() with URL and local file support."""

    @pytest.mark.asyncio
    async def test_empty_returns_default(self) -> None:
        """Empty blocklist_file returns the default filter."""
        wf = await get_filter_async('')
        assert wf is get_default_filter()

    @pytest.mark.asyncio
    async def test_local_file_delegates_to_sync(self, tmp_path: Path) -> None:
        """Local file path delegates to get_filter (sync)."""
        custom = tmp_path / 'local.txt'
        custom.write_text('localword\n', encoding='utf-8')
        wf = await get_filter_async(str(custom))
        assert wf.contains_blocked('localword')

    @pytest.mark.asyncio
    async def test_url_fetches_and_merges(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """URL-based blocklist is fetched and merged with built-in words."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx
        from releasekit import _wordfilter

        _wordfilter._custom_filters.pop('https://example.com/remote.txt', None)
        _wordfilter._remote_cache.pop('https://example.com/remote.txt', None)

        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.text = 'remoteword\nanotherword*\n'
        fake_response.content = b'remoteword\nanotherword*\n'
        fake_response.raise_for_status = MagicMock()
        fake_response.headers = {'strict-transport-security': 'max-age=31536000', 'etag': '"abc"'}

        fake_client = AsyncMock()

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr(
            'releasekit.net.request_with_retry',
            AsyncMock(return_value=fake_response),
        )

        wf = await get_filter_async('https://example.com/remote.txt')
        assert wf.contains_blocked('remoteword')
        assert wf.contains_blocked('anotherwordish')  # prefix match
        assert len(wf) >= 2

    @pytest.mark.asyncio
    async def test_gs_url_fetches_and_merges(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """gs:// URL is converted to HTTPS and fetched."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx
        from releasekit import _wordfilter

        _wordfilter._custom_filters.pop('gs://my-bucket/words.txt', None)
        _wordfilter._remote_cache.pop('gs://my-bucket/words.txt', None)

        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.text = 'gcsword\n'
        fake_response.content = b'gcsword\n'
        fake_response.raise_for_status = MagicMock()
        fake_response.headers = {'strict-transport-security': 'max-age=31536000'}

        fake_client = AsyncMock()
        mock_request = AsyncMock(return_value=fake_response)

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr('releasekit.net.request_with_retry', mock_request)

        wf = await get_filter_async('gs://my-bucket/words.txt')
        assert wf.contains_blocked('gcsword')
        # Verify the fetch URL was converted to HTTPS.
        call_args = mock_request.call_args
        assert 'storage.googleapis.com/my-bucket/words.txt' in call_args[0][2]

    @pytest.mark.asyncio
    async def test_url_304_returns_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """HTTP 304 Not Modified returns the previously cached filter."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx
        from releasekit import _wordfilter

        url = 'https://example.com/cached304.txt'
        sentinel = WordFilter.from_lines(['cachedword'])

        # Pre-populate remote cache with ETag.
        _wordfilter._remote_cache[url] = _wordfilter._RemoteCacheEntry(
            etag='"etag-v1"',
            last_modified='Mon, 01 Jan 2026 00:00:00 GMT',
            sha256='abc123',
            words=frozenset({'cachedword'}),
            wf=sentinel,
        )
        _wordfilter._custom_filters[url] = sentinel

        # Server returns 304.
        fake_304 = MagicMock(spec=httpx.Response)
        fake_304.status_code = 304
        fake_304.headers = {}

        fake_client = AsyncMock()
        mock_request = AsyncMock(return_value=fake_304)

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr('releasekit.net.request_with_retry', mock_request)

        wf = await get_filter_async(url)
        assert wf is sentinel

        # Verify conditional headers were sent.
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['headers']['If-None-Match'] == '"etag-v1"'
        assert 'If-Modified-Since' in call_kwargs['headers']

        # Cleanup.
        _wordfilter._custom_filters.pop(url, None)
        _wordfilter._remote_cache.pop(url, None)


class TestChecksumChangeDetection:
    """Tests for SHA-256 checksum tracking and diff logging."""

    @pytest.mark.asyncio
    async def test_checksum_change_logs_diff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When remote content changes, a warning with diff is logged."""
        import hashlib
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx
        from releasekit import _wordfilter

        url = 'https://example.com/changing.txt'
        old_content = b'oldword\nshared\n'
        old_sha = hashlib.sha256(old_content).hexdigest()

        # Pre-populate cache with old content.
        _wordfilter._remote_cache[url] = _wordfilter._RemoteCacheEntry(
            etag='"old-etag"',
            last_modified='',
            sha256=old_sha,
            words=frozenset({'oldword', 'shared'}),
        )
        _wordfilter._custom_filters.pop(url, None)

        # New content has a different word set.
        new_content = b'newword\nshared\n'
        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.text = 'newword\nshared\n'
        fake_response.content = new_content
        fake_response.raise_for_status = MagicMock()
        fake_response.headers = {
            'strict-transport-security': 'max-age=31536000',
            'etag': '"new-etag"',
        }

        fake_client = AsyncMock()

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr(
            'releasekit.net.request_with_retry',
            AsyncMock(return_value=fake_response),
        )

        # Mock the logger to capture the diff warning.
        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)

        wf = await get_filter_async(url)
        assert wf.contains_blocked('newword')
        assert wf.contains_blocked('shared')

        # Verify checksum change warning was logged.
        mock_log.warning.assert_called()
        call_kwargs = mock_log.warning.call_args[1]
        assert call_kwargs['old_sha256'] == old_sha
        assert call_kwargs['added_count'] == 1
        assert call_kwargs['removed_count'] == 1
        assert '+ newword' in call_kwargs['diff']
        assert '- oldword' in call_kwargs['diff']

        # Cleanup.
        _wordfilter._custom_filters.pop(url, None)
        _wordfilter._remote_cache.pop(url, None)

    @pytest.mark.asyncio
    async def test_first_fetch_no_checksum_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """First fetch (no prior cache) does not log a checksum warning."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx
        from releasekit import _wordfilter

        url = 'https://example.com/firstfetch.txt'
        _wordfilter._remote_cache.pop(url, None)
        _wordfilter._custom_filters.pop(url, None)

        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.text = 'word1\n'
        fake_response.content = b'word1\n'
        fake_response.raise_for_status = MagicMock()
        fake_response.headers = {'strict-transport-security': 'max-age=31536000'}

        fake_client = AsyncMock()

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr(
            'releasekit.net.request_with_retry',
            AsyncMock(return_value=fake_response),
        )

        mock_log = MagicMock()
        monkeypatch.setattr('releasekit.logging.get_logger', lambda _: mock_log)

        await get_filter_async(url)
        # No checksum change warning on first fetch.
        for call in mock_log.warning.call_args_list:
            assert call[0][0] != 'blocklist_checksum_changed'

        # Cleanup.
        _wordfilter._custom_filters.pop(url, None)
        _wordfilter._remote_cache.pop(url, None)


class TestRemoteBlocklistConfig:
    """Tests for RemoteBlocklistConfig integration."""

    @pytest.mark.asyncio
    async def test_custom_max_size_rejects_large(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Custom max_size rejects responses that exceed the limit."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx
        from releasekit import _wordfilter
        from releasekit._wordfilter import RemoteBlocklistConfig

        url = 'https://example.com/big.txt'
        _wordfilter._remote_cache.pop(url, None)
        _wordfilter._custom_filters.pop(url, None)

        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.text = 'word\n'
        fake_response.content = b'x' * 100  # 100 bytes
        fake_response.raise_for_status = MagicMock()
        fake_response.headers = {'strict-transport-security': 'max-age=31536000'}

        fake_client = AsyncMock()

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr(
            'releasekit.net.request_with_retry',
            AsyncMock(return_value=fake_response),
        )

        cfg = RemoteBlocklistConfig(max_size=50)
        with pytest.raises(ValueError, match='too large'):
            await get_filter_async(url, config=cfg)

        # Cleanup.
        _wordfilter._custom_filters.pop(url, None)
        _wordfilter._remote_cache.pop(url, None)

    @pytest.mark.asyncio
    async def test_custom_max_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Custom max_entries limits how many words are loaded."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx
        from releasekit import _wordfilter
        from releasekit._wordfilter import RemoteBlocklistConfig

        url = 'https://example.com/many.txt'
        _wordfilter._remote_cache.pop(url, None)
        _wordfilter._custom_filters.pop(url, None)

        text = '\n'.join(f'word{i}' for i in range(100))
        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.text = text
        fake_response.content = text.encode()
        fake_response.raise_for_status = MagicMock()
        fake_response.headers = {'strict-transport-security': 'max-age=31536000'}

        fake_client = AsyncMock()

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr(
            'releasekit.net.request_with_retry',
            AsyncMock(return_value=fake_response),
        )

        cfg = RemoteBlocklistConfig(max_entries=5)
        await get_filter_async(url, config=cfg)
        # Only 5 remote words loaded (plus any built-in words).
        cached = _wordfilter._remote_cache.get(url)
        assert cached is not None
        assert len(cached.words) == 5

        # Cleanup.
        _wordfilter._custom_filters.pop(url, None)
        _wordfilter._remote_cache.pop(url, None)


class TestWordFilterFromUrl:
    """Tests for WordFilter.from_url() async classmethod."""

    @pytest.mark.asyncio
    async def test_from_url_builds_filter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """from_url() fetches text and builds a WordFilter."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock

        import httpx

        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.text = 'badword\nevil*\n# comment\n'
        fake_response.content = b'badword\nevil*\n# comment\n'
        fake_response.raise_for_status = MagicMock()
        fake_response.headers = {'strict-transport-security': 'max-age=31536000'}

        fake_client = AsyncMock()

        @asynccontextmanager
        async def fake_http_client(**kwargs: Any) -> AsyncIterator[Any]:  # noqa: ANN401
            yield fake_client

        monkeypatch.setattr('releasekit.net.http_client', fake_http_client)
        monkeypatch.setattr(
            'releasekit.net.request_with_retry',
            AsyncMock(return_value=fake_response),
        )

        wf = await WordFilter.from_url('https://example.com/words.txt')
        assert wf.contains_blocked('badword')
        assert wf.contains_blocked('evildoer')  # prefix
        assert not wf.contains_blocked('comment')  # comment line skipped
        assert len(wf) == 2
