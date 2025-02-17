#!/usr/bin/env python3
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


from genkit.core.schema import InstrumentationLibrary, Link, SpanContext


def test_instrumentation_library() -> None:
    m = InstrumentationLibrary(name='foo')
    jstr = m.model_dump_json(by_alias=True)
    assert m == InstrumentationLibrary.model_validate_json(jstr)


def test_link() -> None:
    m = Link(
        context=SpanContext(
            trace_id='foo',
            span_id='bar',
            is_remote=False,
            trace_flags=0,
        )
    )
    jstr = m.model_dump_json(by_alias=True)
    assert m == Link.model_validate_json(jstr)
