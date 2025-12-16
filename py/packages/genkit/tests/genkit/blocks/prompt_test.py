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


"""Tests for the action module."""

from typing import Any
import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.blocks.prompt import load_prompt_folder, lookup_prompt, prompt
from genkit.core.action.types import ActionKind
from genkit.core.typing import (
    GenerateActionOptions,
    GenerateRequest,
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
    ToolChoice,
    ToolDefinition,
)
from genkit.testing import (
    define_echo_model,
    define_programmable_model,
)


def setup_test():
    """Setup a test fixture for the veneer tests."""
    ai = Genkit(model='echoModel')

    pm, _ = define_programmable_model(ai)
    echo, _ = define_echo_model(ai)

    return (ai, echo, pm)


@pytest.mark.asyncio
async def test_simple_prompt() -> None:
    """Test simple prompt rendering."""
    ai, *_ = setup_test()

    want_txt = '[ECHO] user: "hi" {"temperature":11.0}'

    my_prompt = ai.define_prompt(prompt='hi', config={'temperature': 11})

    response = await my_prompt()

    assert response.text == want_txt

    _, response = my_prompt.stream()

    assert (await response).text == want_txt


@pytest.mark.asyncio
async def test_simple_prompt_with_override_config() -> None:
    """Test the config provided at render time is used."""
    ai, *_ = setup_test()

    want_txt = '[ECHO] user: "hi" {"temperature":12.0}'

    my_prompt = ai.define_prompt(prompt='hi', config={'banana': True})

    response = await my_prompt(config={'temperature': 12})

    assert response.text == want_txt

    _, response = my_prompt.stream(config={'temperature': 12})

    assert (await response).text == want_txt


@pytest.mark.asyncio
async def test_prompt_with_system() -> None:
    """Test that the propmt utilises both prompt and system prompt."""
    ai, *_ = setup_test()

    want_txt = '[ECHO] system: "talk like a pirate" user: "hi"'

    my_prompt = ai.define_prompt(prompt='hi', system='talk like a pirate')

    response = await my_prompt()

    assert response.text == want_txt

    _, response = my_prompt.stream()

    assert (await response).text == want_txt


@pytest.mark.asyncio
async def test_prompt_with_kitchensink() -> None:
    """Test that the rendering works with all the options."""
    ai, *_ = setup_test()

    class PromptInput(BaseModel):
        name: str = Field(None, description='the name')

    class ToolInput(BaseModel):
        value: int = Field(None, description='value field')

    @ai.tool(name='testTool')
    def test_tool(input: ToolInput):
        """The tool."""
        return 'abc'

    my_prompt = ai.define_prompt(
        system='pirate',
        prompt='hi',
        messages=[Message(role=Role.USER, content=[TextPart(text='history')])],
        tools=['testTool'],
        tool_choice=ToolChoice.REQUIRED,
        max_turns=5,
        input_schema=PromptInput.model_json_schema(),
        output_constrained=True,
        output_format='json',
        description='a prompt descr',
    )

    want_txt = '[ECHO] system: "pirate" user: "history" user: "hi" tools=testTool tool_choice=required output={"format":"json","constrained":true,"contentType":"application/json"}'

    response = await my_prompt()

    assert response.text == want_txt

    _, response = my_prompt.stream()

    assert (await response).text == want_txt


test_cases_parse_partial_json = [
    (
        'renders system prompt',
        {
            'model': 'echoModel',
            'config': {'banana': 'ripe'},
            'input_schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                },
            },  # Note: Schema representation might need adjustment
            'system': 'hello {{name}} ({{@state.name}})',
            'metadata': {'state': {'name': 'bar'}},
        },
        {'name': 'foo'},
        GenerationCommonConfig.model_validate({'temperature': 11}),
        {},
        """[ECHO] system: "hello foo (bar)" {"temperature":11.0}""",
    ),
    (
        'renders user prompt',
        {
            'model': 'echoModel',
            'config': {'banana': 'ripe'},
            'input_schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                },
            },  # Note: Schema representation might need adjustment
            'prompt': 'hello {{name}} ({{@state.name}})',
            'metadata': {'state': {'name': 'bar_system'}},
        },
        {'name': 'foo'},
        GenerationCommonConfig.model_validate({'temperature': 11}),
        {},
        """[ECHO] user: "hello foo (bar_system)" {"temperature":11.0}""",
    ),
    (
        'renders user prompt with context',
        {
            'model': 'echoModel',
            'config': {'banana': 'ripe'},
            'input_schema': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                },
            },  # Note: Schema representation might need adjustment
            'prompt': 'hello {{name}} ({{@state.name}}, {{@auth.email}})',
            'metadata': {'state': {'name': 'bar'}},
        },
        {'name': 'foo'},
        GenerationCommonConfig.model_validate({'temperature': 11}),
        {'auth': {'email': 'a@b.c'}},
        """[ECHO] user: "hello foo (bar, a@b.c)" {"temperature":11.0}""",
    ),
]


@pytest.mark.skip(reason='issues when running on CI')
@pytest.mark.asyncio
@pytest.mark.parametrize(
    'test_case, prompt, input, input_option, context, want_rendered',
    test_cases_parse_partial_json,
    ids=[tc[0] for tc in test_cases_parse_partial_json],
)
async def test_prompt_rendering_dotprompt(
    test_case: str,
    prompt: dict[str, Any],
    input: dict[str, Any],
    input_option: GenerationCommonConfig,
    context: dict[str, Any],
    want_rendered: str,
) -> None:
    """Test prompt rendering."""
    ai, *_ = setup_test()

    my_prompt = ai.define_prompt(**prompt)

    response = await my_prompt(input, input_option, context=context)

    assert response.text == want_rendered


# Tests for file-based prompt loading and two-action structure
@pytest.mark.asyncio
async def test_file_based_prompt_registers_two_actions() -> None:
    """File-based prompts create both PROMPT and EXECUTABLE_PROMPT actions."""
    ai, *_ = setup_test()

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir) / 'prompts'
        prompt_dir.mkdir()

        # Simple prompt file: name is "filePrompt"
        prompt_file = prompt_dir / 'filePrompt.prompt'
        prompt_file.write_text('hello {{name}}')

        # Load prompts from directory
        load_prompt_folder(ai.registry, prompt_dir)

        # Actions are registered with registry_definition_key (e.g., "dotprompt/filePrompt")
        # We need to look them up by kind and name (without the /prompt/ prefix)
        action_name = 'dotprompt/filePrompt'  # registry_definition_key format

        prompt_action = ai.registry.lookup_action(ActionKind.PROMPT, action_name)
        executable_prompt_action = ai.registry.lookup_action(
            ActionKind.EXECUTABLE_PROMPT, action_name
        )

        assert prompt_action is not None
        assert executable_prompt_action is not None


@pytest.mark.asyncio
async def test_prompt_and_executable_prompt_return_types() -> None:
    """PROMPT action returns GenerateRequest, EXECUTABLE_PROMPT returns GenerateActionOptions."""
    ai, *_ = setup_test()

    # Test with file-based prompt (which creates both actions)
    # Programmatic prompts don't create actions - they're just ExecutablePrompt instances
    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir) / 'prompts'
        prompt_dir.mkdir()

        prompt_file = prompt_dir / 'testPrompt.prompt'
        prompt_file.write_text('hello {{name}}')

        load_prompt_folder(ai.registry, prompt_dir)
        action_name = 'dotprompt/testPrompt'

        prompt_action = ai.registry.lookup_action(ActionKind.PROMPT, action_name)
        executable_prompt_action = ai.registry.lookup_action(
            ActionKind.EXECUTABLE_PROMPT, action_name
        )

        assert prompt_action is not None
        assert executable_prompt_action is not None

        prompt_result = await prompt_action.arun(
            input={'name': 'World'}
        )
        assert isinstance(prompt_result.response, GenerateRequest)

        exec_result = await executable_prompt_action.arun(
            input={'name': 'World'}
        )
        assert isinstance(exec_result.response, GenerateActionOptions)


@pytest.mark.asyncio
async def test_lookup_prompt_returns_executable_prompt() -> None:
    """lookup_prompt should return an ExecutablePrompt that can be called."""
    ai, *_ = setup_test()

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir) / 'prompts'
        prompt_dir.mkdir()

        prompt_file = prompt_dir / 'lookupTest.prompt'
        prompt_file.write_text('hi {{name}}')

        load_prompt_folder(ai.registry, prompt_dir)

        executable = await lookup_prompt(ai.registry, 'lookupTest')

        response = await executable({'name': 'World'})
        assert 'World' in response.text


@pytest.mark.asyncio
async def test_prompt_function_uses_lookup_prompt() -> None:
    ai, *_ = setup_test()

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir) / 'prompts'
        prompt_dir.mkdir()

        prompt_file = prompt_dir / 'promptFuncTest.prompt'
        prompt_file.write_text('hello {{name}}')

        load_prompt_folder(ai.registry, prompt_dir)

        # Use prompt() function to look up the file-based prompt
        executable = await prompt(ai.registry, 'promptFuncTest')
        response = await executable({'name': 'World'})
        assert 'World' in response.text
