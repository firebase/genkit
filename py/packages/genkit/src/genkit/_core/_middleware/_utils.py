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

"""Shared middleware utilities and constants."""

import ipaddress
from urllib.parse import urlparse

from genkit._ai._document import Document
from genkit._ai._model import Message, text_from_content
from genkit._core._error import StatusName

_CONTEXT_PREFACE = '\n\nUse the following information to complete your task:\n\n'

_DEFAULT_RETRY_STATUSES: list[StatusName] = [
    'UNAVAILABLE',
    'DEADLINE_EXCEEDED',
    'RESOURCE_EXHAUSTED',
    'ABORTED',
    'INTERNAL',
]

_DEFAULT_FALLBACK_STATUSES: list[StatusName] = [
    'UNAVAILABLE',
    'DEADLINE_EXCEEDED',
    'RESOURCE_EXHAUSTED',
    'ABORTED',
    'INTERNAL',
    'NOT_FOUND',
    'UNIMPLEMENTED',
]

_SSRF_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(('metadata.google.internal', 'metadata', '169.254.169.254'))


def _is_safe_url(url: str) -> bool:
    """Check if URL is safe for download (blocks SSRF: private IPs, loopback, cloud metadata)."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        host_lower = hostname.lower()
        blocked = ('localhost', 'localhost.', 'ip6-localhost', 'ip6-loopback')
        if host_lower in blocked or host_lower in _SSRF_BLOCKED_HOSTNAMES:
            return False
        try:
            addr = ipaddress.ip_address(hostname)
        except ValueError:
            return True  # Hostname (e.g. example.com); caller can use filter_fn to restrict
        return not (addr.is_private or addr.is_loopback or addr.is_link_local)
    except Exception:
        return False


def _last_user_message(messages: list[Message]) -> Message | None:
    """Find the last user message in a list."""
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == 'user':
            return messages[i]
    return None


def _context_item_template(d: Document, index: int) -> str:
    """Render a document as a citation line for context injection."""
    out = '- '
    ref = (d.metadata and (d.metadata.get('ref') or d.metadata.get('id'))) or index
    out += f'[{ref}]: '
    out += text_from_content(d.content) + '\n'
    return out
