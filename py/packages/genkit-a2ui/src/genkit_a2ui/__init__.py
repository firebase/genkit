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

"""A2UI generate middleware for Genkit."""

from ._middleware import A2ui, A2uiConfig
from ._parser import A2uiParseError
from ._part import a2ui_part, envelopes_from_parts, is_a2ui_part
from ._types import A2UI_MIME_TYPE

__all__ = [
    'A2UI_MIME_TYPE',
    'A2ui',
    'A2uiConfig',
    'A2uiParseError',
    'a2ui_part',
    'envelopes_from_parts',
    'is_a2ui_part',
]
