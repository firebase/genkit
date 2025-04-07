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

"""Encoding/decoding functions."""

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel


def dump_dict(obj: Any, fallback: Callable[[Any], Any] | None = None):
    """Converts an object or Pydantic to a dictionary.

    If the input object is a Pydantic BaseModel, it returns a dictionary
    representation of the model, excluding fields with `None` values and using
    aliases for field names.  For any other object type, it returns the object
    unchanged.

    Args:
        obj: The object to potentially convert to a dictionary.
        fallback: A function to call when an unknown value is encountered. If not provided, error is raised.

    Returns:
        A dictionary if the input is a Pydantic BaseModel, otherwise the
        original object.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=True, by_alias=True, fallback=fallback)
    else:
        return obj


def dump_json(obj: Any, indent=None, fallback: Callable[[Any], Any] | None = None) -> str:
    """Dumps an object to a JSON string.

    If the object is a Pydantic BaseModel, it will be dumped using the
    model_dump_json method using the by_alias flag set to True.  Otherwise, the
    object will be dumped using the json.dumps method.

    Args:
        obj: The object to dump.
        indent: The indentation level for the JSON string.
        fallback: A function to call when an unknown value is encountered. If not provided, error is raised.

    Returns:
        A JSON string.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump_json(by_alias=True, exclude_none=True, indent=indent, fallback=fallback)
    else:
        return json.dumps(obj, indent=indent, default=fallback)
