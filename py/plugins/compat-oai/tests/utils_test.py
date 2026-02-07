# Copyright 2025 Google LLC
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

"""Exhaustive tests for models/utils.py utility functions."""

import base64

import pytest

from genkit.plugins.compat_oai.models.utils import (
    _extract_media,
    _extract_text,
    _find_text,
    decode_data_uri_bytes,
    extract_config_dict,
    parse_data_uri_content_type,
)
from genkit.types import (
    GenerateRequest,
    Media,
    MediaPart,
    Message,
    Part,
    Role,
    TextPart,
)


class TestParseDataUriContentType:
    """Tests for parse_data_uri_content_type."""

    def test_audio_mpeg_with_base64(self) -> None:
        """Parse content type from a standard audio data URI."""
        url = 'data:audio/mpeg;base64,AAAA'
        assert parse_data_uri_content_type(url) == 'audio/mpeg'

    def test_text_plain_without_base64(self) -> None:
        """Parse content type from a data URI without ;base64 qualifier."""
        url = 'data:text/plain,hello world'
        assert parse_data_uri_content_type(url) == 'text/plain'

    def test_image_png_with_base64(self) -> None:
        """Parse content type from an image data URI."""
        url = 'data:image/png;base64,iVBOR...'
        assert parse_data_uri_content_type(url) == 'image/png'

    def test_empty_content_type_with_base64(self) -> None:
        """Return empty string when content type is missing from data URI."""
        url = 'data:;base64,AAAA'
        assert parse_data_uri_content_type(url) == ''

    def test_no_data_prefix(self) -> None:
        """Return empty string for non-data-URI URLs."""
        assert parse_data_uri_content_type('https://example.com/file.mp3') == ''

    def test_raw_base64_string(self) -> None:
        """Return empty string for raw base64 strings."""
        assert parse_data_uri_content_type('AAAA') == ''

    def test_empty_string(self) -> None:
        """Return empty string for empty input."""
        assert parse_data_uri_content_type('') == ''

    def test_data_prefix_no_comma(self) -> None:
        """Return empty string for malformed data URI without comma."""
        assert parse_data_uri_content_type('data:audio/mpeg;base64') == ''

    def test_application_json(self) -> None:
        """Parse content type from a JSON data URI."""
        url = 'data:application/json;base64,eyJ0ZXN0IjogdHJ1ZX0='
        assert parse_data_uri_content_type(url) == 'application/json'

    def test_audio_wav_with_extra_params(self) -> None:
        """Parse content type from a data URI with extra parameters."""
        url = 'data:audio/wav;rate=44100;base64,AAAA'
        assert parse_data_uri_content_type(url) == 'audio/wav'

    def test_content_type_with_charset(self) -> None:
        """Parse content type from a data URI with charset parameter."""
        url = 'data:text/html;charset=utf-8,<h1>hi</h1>'
        assert parse_data_uri_content_type(url) == 'text/html'


class TestDecodeDataUriBytes:
    """Tests for decode_data_uri_bytes."""

    def test_valid_data_uri(self) -> None:
        """Decode bytes from a valid base64 data URI."""
        payload = b'hello world'
        b64 = base64.b64encode(payload).decode('ascii')
        url = f'data:audio/mpeg;base64,{b64}'
        assert decode_data_uri_bytes(url) == payload

    def test_raw_base64(self) -> None:
        """Decode bytes from a raw base64 string without data: prefix."""
        payload = b'test data'
        b64 = base64.b64encode(payload).decode('ascii')
        assert decode_data_uri_bytes(b64) == payload

    def test_remote_http_url_raises(self) -> None:
        """Raise ValueError for http:// URLs."""
        with pytest.raises(ValueError, match='Remote URLs are not supported'):
            decode_data_uri_bytes('http://example.com/audio.mp3')

    def test_remote_https_url_raises(self) -> None:
        """Raise ValueError for https:// URLs."""
        with pytest.raises(ValueError, match='Remote URLs are not supported'):
            decode_data_uri_bytes('https://example.com/audio.mp3')

    def test_invalid_data_uri_format_raises(self) -> None:
        """Raise ValueError for data URI with invalid base64 payload."""
        with pytest.raises(ValueError, match='Invalid data URI format'):
            decode_data_uri_bytes('data:audio/mpeg;base64,NOT_VALID_B64!!!')

    def test_invalid_raw_base64_raises(self) -> None:
        """Raise ValueError for invalid raw base64 strings."""
        with pytest.raises(ValueError, match='Invalid base64 data'):
            decode_data_uri_bytes('NOT_VALID_B64!!!')

    def test_empty_payload_data_uri(self) -> None:
        """Decode empty bytes from a data URI with empty payload."""
        url = 'data:audio/mpeg;base64,'
        assert decode_data_uri_bytes(url) == b''

    def test_data_uri_without_base64_qualifier(self) -> None:
        """Decode bytes from a data URI that omits ;base64 qualifier."""
        payload = b'test'
        b64 = base64.b64encode(payload).decode('ascii')
        url = f'data:text/plain,{b64}'
        assert decode_data_uri_bytes(url) == payload

    def test_data_uri_with_no_content_type(self) -> None:
        """Decode bytes from a data URI with empty content type."""
        payload = b'data'
        b64 = base64.b64encode(payload).decode('ascii')
        url = f'data:;base64,{b64}'
        assert decode_data_uri_bytes(url) == payload


class TestExtractConfigDict:
    """Tests for extract_config_dict."""

    def _make_request(self, config: object = None) -> GenerateRequest:
        """Create a minimal GenerateRequest with the given config."""
        return GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hello'))],
                )
            ],
            config=config,
        )

    def test_no_config_returns_empty_dict(self) -> None:
        """Return empty dict when request has no config."""
        request = self._make_request(config=None)
        assert extract_config_dict(request) == {}

    def test_dict_config_returns_copy(self) -> None:
        """Return a copy of the config when it is a dict."""
        original = {'temperature': 0.5, 'model': 'gpt-4'}
        request = self._make_request(config=original)
        result = extract_config_dict(request)
        assert result == original
        assert result is not original

    def test_dict_config_mutation_does_not_affect_original(self) -> None:
        """Verify that mutating the returned dict does not affect the original."""
        original = {'temperature': 0.5}
        request = self._make_request(config=original)
        result = extract_config_dict(request)
        result['temperature'] = 1.0
        assert original['temperature'] == 0.5

    def test_empty_dict_config(self) -> None:
        """Return empty dict when config is an empty dict."""
        request = self._make_request(config={})
        assert extract_config_dict(request) == {}


class TestFindText:
    """Tests for _find_text."""

    def test_returns_text_from_first_message(self) -> None:
        """Find and return text from the first message's text part."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hello'))],
                )
            ]
        )
        assert _find_text(request) == 'hello'

    def test_returns_none_for_no_messages(self) -> None:
        """Return None when there are no messages."""
        request = GenerateRequest(messages=[])
        assert _find_text(request) is None

    def test_returns_none_for_no_text_parts(self) -> None:
        """Return None when message has only media parts."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=MediaPart(media=Media(url='data:audio/mpeg;base64,AAAA')))],
                )
            ]
        )
        assert _find_text(request) is None

    def test_returns_first_text_part(self) -> None:
        """Return the first text part when multiple exist."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[
                        Part(root=TextPart(text='first')),
                        Part(root=TextPart(text='second')),
                    ],
                )
            ]
        )
        assert _find_text(request) == 'first'


class TestExtractText:
    """Tests for _extract_text."""

    def test_returns_text_when_present(self) -> None:
        """Extract and return text when present."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='hello'))],
                )
            ]
        )
        assert _extract_text(request) == 'hello'

    def test_raises_for_no_messages(self) -> None:
        """Raise ValueError when request has no messages."""
        request = GenerateRequest(messages=[])
        with pytest.raises(ValueError, match='No messages found'):
            _extract_text(request)

    def test_raises_for_no_text_content(self) -> None:
        """Raise ValueError when no text parts exist."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=MediaPart(media=Media(url='data:audio/mpeg;base64,AAAA')))],
                )
            ]
        )
        with pytest.raises(ValueError, match='No text content found'):
            _extract_text(request)


class TestExtractMedia:
    """Tests for _extract_media."""

    def test_extracts_media_url_and_content_type(self) -> None:
        """Extract URL and content type from a media part."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[
                        Part(
                            root=MediaPart(
                                media=Media(
                                    url='data:audio/mpeg;base64,AAAA',
                                    content_type='audio/mpeg',
                                )
                            )
                        )
                    ],
                )
            ]
        )
        url, ct = _extract_media(request)
        assert url == 'data:audio/mpeg;base64,AAAA'
        assert ct == 'audio/mpeg'

    def test_parses_content_type_from_data_uri_when_missing(self) -> None:
        """Parse content type from data URI when not explicitly provided."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[
                        Part(
                            root=MediaPart(
                                media=Media(
                                    url='data:audio/wav;base64,AAAA',
                                )
                            )
                        )
                    ],
                )
            ]
        )
        url, ct = _extract_media(request)
        assert url == 'data:audio/wav;base64,AAAA'
        assert ct == 'audio/wav'

    def test_raises_for_no_messages(self) -> None:
        """Raise ValueError when request has no messages."""
        request = GenerateRequest(messages=[])
        with pytest.raises(ValueError, match='No messages found'):
            _extract_media(request)

    def test_raises_for_no_media_parts(self) -> None:
        """Raise ValueError when message has no media parts."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='just text'))],
                )
            ]
        )
        with pytest.raises(ValueError, match='No media content found'):
            _extract_media(request)

    def test_skips_text_parts_finds_media(self) -> None:
        """Find media part even when text parts come first."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[
                        Part(root=TextPart(text='instructions')),
                        Part(
                            root=MediaPart(
                                media=Media(
                                    url='data:image/png;base64,iVBOR',
                                    content_type='image/png',
                                )
                            )
                        ),
                    ],
                )
            ]
        )
        url, ct = _extract_media(request)
        assert ct == 'image/png'

    def test_content_type_from_data_uri_without_base64_qualifier(self) -> None:
        """Parse content type from data URI that omits ;base64 qualifier."""
        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=MediaPart(media=Media(url='data:text/plain,hello')))],
                )
            ]
        )
        _, ct = _extract_media(request)
        assert ct == 'text/plain'
