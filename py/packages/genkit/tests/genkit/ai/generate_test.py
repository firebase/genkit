#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import pathlib

import pytest
import yaml
from genkit.ai.generate import generate_action
from genkit.ai.testing_utils import define_programmable_model
from genkit.core.action import ActionRunContext
from genkit.core.codec import dump_dict, dump_json
from genkit.core.typing import (
    FinishReason,
    GenerateActionOptions,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    Role,
    TextPart,
)
from genkit.veneer.veneer import Genkit
from pydantic import TypeAdapter


@pytest.fixture
def setup_test():
    ai = Genkit()

    pm, _ = define_programmable_model(ai)

    @ai.tool('the tool')
    def testTool():
        return 'abc'

    return (ai, pm)


@pytest.mark.asyncio
async def test_simple_text_generate_request(setup_test) -> None:
    ai, pm = setup_test

    pm.responses.append(
        GenerateResponse(
            finishReason=FinishReason.STOP,
            message=Message(role=Role.MODEL, content=[TextPart(text='bye')]),
        )
    )

    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model='programmableModel',
            messages=[
                Message(
                    role=Role.USER,
                    content=[TextPart(text='hi')],
                ),
            ],
        ),
    )

    assert response.text == 'bye'


##########################################################################
# run tests from /tests/specs/generate.yaml
##########################################################################

specs = []
with open(
    pathlib.Path(__file__)
    .parent.joinpath('../../../../../../tests/specs/generate.yaml')
    .resolve()
) as stream:
    testsSpec = yaml.safe_load(stream)
    specs = testsSpec['tests']
    specs = [x for x in testsSpec['tests'] if x['name'] == 'calls tools']


@pytest.mark.parametrize(
    'spec',
    specs,
)
@pytest.mark.asyncio
async def test_generate_action_spec(spec) -> None:
    ai = Genkit()

    pm, _ = define_programmable_model(ai)

    @ai.tool('description')
    def testTool():
        return 'tool called'

    if 'modelResponses' in spec:
        pm.responses = [
            TypeAdapter(GenerateResponse).validate_python(resp)
            for resp in spec['modelResponses']
        ]

    if 'streamChunks' in spec:
        pm.chunks = []
        for chunks in spec['streamChunks']:
            converted = []
            for chunk in chunks:
                converted.append(
                    TypeAdapter(GenerateResponseChunk).validate_python(chunk)
                )
            pm.chunks.append(converted)

    response = None
    chunks = None
    if 'stream' in spec and spec['stream']:
        chunks = []

        def on_chunk(chunk):
            chunks.append(chunk)

        response = await generate_action(
            ai.registry,
            TypeAdapter(GenerateActionOptions).validate_python(spec['input']),
            on_chunk=on_chunk,
        )
    else:
        response = await generate_action(
            ai.registry,
            TypeAdapter(GenerateActionOptions).validate_python(spec['input']),
        )

    if 'expectChunks' in spec:
        got = clean_schema(chunks)
        want = clean_schema(spec['expectChunks'])
        if not is_equal_lists(got, want):
            raise AssertionError(
                f'{dump_json(got, indent=2)}\n\nis not equal to expected:\n\n{dump_json(want, indent=2)}'
            )

    if 'expectResponse' in spec:
        got = clean_schema(dump_dict(response))
        want = clean_schema(spec['expectResponse'])
        if got != want:
            raise AssertionError(
                f'{dump_json(got, indent=2)}\n\nis not equal to expected:\n\n{dump_json(want, indent=2)}'
            )


def is_equal_lists(a, b):
    if len(a) != len(b):
        return False

    for i in range(len(a)):
        if dump_dict(a[i]) != dump_dict(b[i]):
            return False

    return True


primitives = (bool, str, int, float, type(None))


def is_primitive(obj):
    return isinstance(obj, primitives)


def clean_schema(d):
    if is_primitive(d):
        return d
    if isinstance(d, dict):
        out = {}
        for key in d:
            if key != '$schema':
                out[key] = clean_schema(d[key])
        return out
    elif hasattr(d, '__len__'):
        return [clean_schema(i) for i in d]
    else:
        return d
