#!/usr/bin/env python3
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def simplify_schema(schema: dict) -> dict:
    """Remove anyOf patterns for optional fields and title fields from
    properties."""
    properties = schema.get('properties', {})
    for prop in properties.values():
        if 'anyOf' in prop and len(prop['anyOf']) == 2:
            # Find the non-null type definition
            non_null_type = next(
                (item for item in prop['anyOf'] if item.get('type') != 'null'),
                None,
            )
            if non_null_type:
                # Replace the anyOf with just the non-null type definition
                prop.clear()
                prop.update(non_null_type)

        # Remove title, default regardless of whether it was an anyOf field
        if 'title' in prop:
            del prop['title']
        if 'default' in prop:
            del prop['default']

    return schema


class InstrumentationLibrary(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        populate_by_name=True,
    )

    name: str
    version: str | None = Field(default=None)
    schema_url: str | None = Field(default=None, alias='schemaUrl')


class SpanContext(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    trace_id: str = Field(..., alias='traceId')
    span_id: str = Field(..., alias='spanId')
    is_remote: bool | None = Field(None, alias='isRemote')
    trace_flags: float = Field(..., alias='traceFlags')


class Link(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    context: SpanContext | None = None
    attributes: dict[str, Any] | None = None
    dropped_attributes_count: float | None = Field(
        None, alias='droppedAttributesCount'
    )


if __name__ == '__main__':
    from pprint import pprint

    pprint(simplify_schema(InstrumentationLibrary.model_json_schema()))
    pprint(
        InstrumentationLibrary.model_validate_json(
            '{"name":"foo", "version":null, "schemaUrl": null}'
        )
    )
    pprint(InstrumentationLibrary(name='foo').model_dump(by_alias=True))
    pprint(InstrumentationLibrary(name='foo').model_dump_json(by_alias=True))
