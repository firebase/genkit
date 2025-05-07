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

"""Helpers for managing deprecations.

This module provides a metaclass for creating deprecated enums. It allows
developers to mark enum members as deprecated and provides warnings when those
members are accessed.

The metaclass works by overriding the __getattribute__ method of the enum class.
When a deprecated member is accessed, a deprecation warning is issued.

## Example

    ```python
    Deprecations = deprecated_enum_metafactory({
        'OLD_THING': DeprecationInfo(recommendation='NEW_THING', status=DeprecationStatus.DEPRECATED),
    })


    class TestEnum(StrEnum, metaclass=Deprecations): ...
    ```
"""

import enum
import warnings
from dataclasses import dataclass


class DeprecationStatus(enum.Enum):
    """Defines the deprecation status of an enum member."""

    SUPPORTED = 'supported'
    DEPRECATED = 'deprecated'
    LEGACY = 'legacy'


@dataclass
class DeprecationInfo:
    """Holds information about a deprecated enum member."""

    recommendation: str | None
    status: DeprecationStatus


def deprecated_enum_metafactory(
    deprecated_map: dict[str, DeprecationInfo],
) -> type[enum.EnumMeta]:
    """Creates an EnumMeta metaclass to handle deprecated enum members.

    Args:
        deprecated_map: Dict mapping enum member names to DeprecationInfo.

    Returns:
        An EnumMeta subclass that warns on deprecated member access.
    """

    class DeprecatedEnumMeta(enum.EnumMeta):
        def __getattribute__(cls, name: str) -> object:
            """Get an attribute of the enum class.

            Args:
                cls: The enum class.
                name: The name of the attribute to get.

            Returns:
                The attribute value.
            """
            # This __getattribute__ is called when accessing attributes
            # directly on the Enum class itself (e.g., MyEnum.MEMBER).
            if name in deprecated_map:
                info = deprecated_map[name]
                if info.status in (
                    DeprecationStatus.DEPRECATED,
                    DeprecationStatus.LEGACY,
                ):
                    status_str = info.status.value
                    message = (
                        (f'{cls.__name__}.{name} is {status_str}; use {cls.__name__}.{info.recommendation} instead')
                        if info.recommendation is not None
                        else f'{cls.__name__}.{name} is {status_str}'
                    )
                    # Start with stacklevel=4; adjust if needed based on test
                    # results (factory adds a frame, metaclass __getattribute__
                    # adds a frame)
                    warnings.warn(
                        message,
                        DeprecationWarning,
                        stacklevel=4,
                    )
            return super().__getattribute__(name)

    return DeprecatedEnumMeta
