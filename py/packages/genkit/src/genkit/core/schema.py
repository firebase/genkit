#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Functions for working with schema."""

from typing import Any

from pydantic import TypeAdapter


def to_json_schema(schema: type | dict[str, Any]) -> dict[str, Any]:
    """
    Converts a Python type to a JSON schema.

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
