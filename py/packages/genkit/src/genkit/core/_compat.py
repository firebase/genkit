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

"""Compatibility module for Python version differences.

This module provides imports that work across different Python versions,
allowing the codebase to support Python 3.10+ while using newer typing features.
"""

import sys

# StrEnum - Added in Python 3.11
# Used for string enums throughout the codebase
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from strenum import StrEnum

# override decorator - Added in Python 3.12
# We use this throughout the codebase to mark methods that override parent methods
if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override

__all__ = ['StrEnum', 'override']
