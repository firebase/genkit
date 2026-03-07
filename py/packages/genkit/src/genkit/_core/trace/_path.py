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

"""Path utilities for Genkit tracing.

This module provides functions for building and manipulating hierarchical
trace paths used by Genkit's telemetry system.

Path Format:
    Paths follow the format: /{name,t:type,s:subtype}
    Example: /{myFlow,t:flow}/{myTool,t:action,s:tool}

Functions:
    - build_path: Build a hierarchical path with type annotations
    - decorate_path_with_subtype: Add subtype to leaf node
    - to_display_path: Convert qualified path to human-readable format
"""

import re
from urllib.parse import quote


def build_path(
    name: str,
    parent_path: str,
    type_str: str,
    subtype: str | None = None,
) -> str:
    """Build a hierarchical path with type annotations.

    Args:
        name: The name of the action/flow/step.
        parent_path: The path of the parent span (empty string for root).
        type_str: The type (e.g., 'flow', 'action', 'flowStep').
        subtype: Optional subtype (e.g., 'tool', 'model', 'flow').

    Returns:
        Annotated path string.

    Examples:
        >>> build_path('myFlow', '', 'flow')
        '/{myFlow,t:flow}'

        >>> build_path('myTool', '/{myFlow,t:flow}', 'action', 'tool')
        '/{myFlow,t:flow}/{myTool,t:action,s:tool}'
    """
    # URL-encode name to handle special characters
    name = quote(name, safe='')

    # Build the path segment with type annotation
    if type_str:
        path_segment = f'{name},t:{type_str}'
    else:
        path_segment = name

    # Add subtype if provided
    if subtype:
        path_segment = f'{path_segment},s:{subtype}'

    # Wrap in braces and append to parent path
    path_segment = '{' + path_segment + '}'
    return parent_path + '/' + path_segment


def decorate_path_with_subtype(path: str, subtype: str) -> str:
    """Add subtype annotation to the leaf node of a path.

    Args:
        path: The path to decorate.
        subtype: The subtype to add (e.g., 'tool', 'model', 'flow').

    Returns:
        Decorated path string.

    Examples:
        >>> decorate_path_with_subtype('/{myFlow,t:flow}/{myTool,t:action}', 'tool')
        '/{myFlow,t:flow}/{myTool,t:action,s:tool}'
    """
    if not path or not subtype:
        return path

    # Find the last opening brace
    last_brace_idx = path.rfind('{')
    if last_brace_idx == -1:
        return path  # No braces found

    # Find the closing brace after the last opening brace
    closing_brace_idx = path.find('}', last_brace_idx)
    if closing_brace_idx == -1:
        return path  # No closing brace found

    # Extract the content of the last segment (without braces)
    segment_content = path[last_brace_idx + 1 : closing_brace_idx]

    # Check if subtype already exists
    if any(p.strip().startswith('s:') for p in segment_content.split(',')[1:]):
        return path

    # Add subtype annotation
    decorated_content = segment_content + ',s:' + subtype

    # Rebuild the path with the decorated last segment
    return path[: last_brace_idx + 1] + decorated_content + path[closing_brace_idx:]


def to_display_path(qualified_path: str) -> str:
    """Convert a qualified Genkit path to a display path.

    Simplifies paths like '/{myFlow,t:flow}/{step,t:flowStep}' to 'myFlow > step'.

    Args:
        qualified_path: The full Genkit path.

    Returns:
        A simplified display path with ' > ' separators.
    """
    if not qualified_path:
        return ''

    # Extract names from path segments like '{name,t:type}'
    path_part_regex = r'\{([^,}]+),[^}]+\}'
    matches = re.findall(path_part_regex, qualified_path)
    return ' > '.join(matches)
