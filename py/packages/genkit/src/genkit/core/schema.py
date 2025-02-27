#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Functions for working with schema."""

from typing import Any

from pydantic import TypeAdapter


def to_json_schema(schema: type | dict[str, Any]) -> dict[str, Any]:
    if isinstance(schema, dict):
        return schema
    type_adapter = TypeAdapter(schema)
    return type_adapter.json_schema()
