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

"""Functions for working with schema."""

from typing import Any

from pydantic import TypeAdapter


def to_json_schema(schema: type | dict[str, Any]) -> dict[str, Any]:
    """Converts a Python type to a JSON schema.

    If the input `schema` is already a dictionary (assumed json schema), it is
    returned directly. Otherwise, it is assumed to be a Python type, and a
    Pydantic `TypeAdapter` is used to generate the corresponding JSON schema.

    Args:
        schema: A Python type or a dictionary representing a JSON schema.

    Returns:
        A dictionary representing the JSON schema.

    Examples:
        Assuming you have a Pydantic model like this:

        >>> from pydantic import BaseModel
        >>> class MyModel(BaseModel):
        ...     id: int
        ...     name: str

        You can generate the JSON schema:

        >>> schema = to_json_schema(MyModel)
        >>> print(schema)
        {'properties': {'id': {'title': 'Id', 'type': 'integer'}, 'name': {'title': 'Name', 'type': 'string'}}, 'required': ['id', 'name'], 'title': 'MyModel', 'type': 'object'}

        If you pass in a dictionary:

        >>> existing_schema = {'type': 'string'}
        >>> result = to_json_schema(existing_schema)
        >>> print(result)
        {'type': 'string'}
    """
    if isinstance(schema, dict):
        return schema
    type_adapter = TypeAdapter(schema)
    return type_adapter.json_schema()
