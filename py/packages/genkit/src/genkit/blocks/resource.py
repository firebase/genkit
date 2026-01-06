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

"""Resource types and functions for Genkit."""

import re
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from genkit.core.typing import Part


class ResourceOptions(BaseModel):
    """Options for defining a resource.

    Attributes:
        name: The name of the resource.
        uri: Optional fixed URI for the resource (e.g., "my://resource").
        template: Optional URI template with placeholders (e.g., "file://{path}").
        description: Optional description of the resource.
    """

    name: str
    uri: str | None = None
    template: str | None = None
    description: str | None = None


class ResourceContent(BaseModel):
    """Content returned by a resource.

    Attributes:
        content: List of content parts (text, media, etc.).
    """

    content: list[Part]


# Type for resource function
ResourceFn = Callable[[dict[str, Any]], Awaitable[ResourceContent] | ResourceContent]


def matches_uri_template(template: str, uri: str) -> dict[str, str] | None:
    """Check if a URI matches a template and extract parameters.

    Args:
        template: URI template with {param} placeholders (e.g., "file://{path}").
        uri: The URI to match against the template.

    Returns:
        Dictionary of extracted parameters if match, None otherwise.

    Examples:
        >>> matches_uri_template('file://{path}', 'file:///home/user/doc.txt')
        {'path': '/home/user/doc.txt'}
        >>> matches_uri_template('user://{id}/profile', 'user://123/profile')
        {'id': '123'}
    """
    # Split template into parts: text and {param} placeholders
    parts = re.split(r'(\{[\w]+\})', template)
    pattern_parts = []
    for part in parts:
        if part.startswith('{') and part.endswith('}'):
            param_name = part[1:-1]
            # Use .+? (non-greedy) to match parameters
            pattern_parts.append(f'(?P<{param_name}>.+?)')
        else:
            pattern_parts.append(re.escape(part))

    pattern = f'^{"".join(pattern_parts)}$'

    match = re.match(pattern, uri)
    if match:
        return match.groupdict()
    return None
