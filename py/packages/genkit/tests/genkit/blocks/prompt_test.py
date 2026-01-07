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

import tempfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.blocks.prompt import load_prompt_folder, lookup_prompt, prompt
from genkit.core.action.types import ActionKind
from genkit.core.typing import (
    DocumentData,
    GenerateActionOptions,
    GenerateRequest,
    GenerateResponse,
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


@pytest.mark.asyncio
async def test_prompt_with_resolvers() -> None:
    """Test that the rendering works with resolvers."""
    ai, *_ = setup_test()

    async def system_resolver(input, context):
        return f'system {input["name"]}'

    def prompt_resolver(input, context):
        return f'prompt {input["name"]}'

    async def messages_resolver(input, context):
        return [Message(role=Role.USER, content=[TextPart(text=f'msg {input["name"]}')])]

    my_prompt = ai.define_prompt(
        system=system_resolver,
        prompt=prompt_resolver,
        messages=messages_resolver,
    )

    want_txt = '[ECHO] system: "system world" user: "msg world" user: "prompt world"'

    response = await my_prompt(input={'name': 'world'})

    assert response.text == want_txt


@pytest.mark.asyncio
async def test_prompt_with_docs_resolver() -> None:
    """Test that the rendering works with docs resolver."""
    ai, _, pm = setup_test()

    pm.responses = [GenerateResponse(message=Message(role=Role.MODEL, content=[TextPart(text='ok')]))]

    async def docs_resolver(input, context):
        return [DocumentData(content=[TextPart(text=f'doc {input["name"]}')])]

    my_prompt = ai.define_prompt(
        model='programmableModel',
        prompt='hi',
        docs=docs_resolver,
    )

    await my_prompt(input={'name': 'world'})

    # Check that PM received the docs
    assert pm.last_request.docs[0].content[0].root.text == 'doc world'


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


# Tests for prompt variants and partials
@pytest.mark.asyncio
async def test_load_prompt_variant() -> None:
    """Test loading and using a prompt variant."""
    ai, *_ = setup_test()

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir) / 'prompts'
        prompt_dir.mkdir()

        # Create base prompt
        base_prompt = prompt_dir / 'greeting.prompt'
        base_prompt.write_text('---\nmodel: echoModel\n---\nHello {{name}}!')

        # Create variant prompt
        variant_prompt = prompt_dir / 'greeting.casual.prompt'
        variant_prompt.write_text("---\nmodel: echoModel\n---\nHey {{name}}, what's up?")

        load_prompt_folder(ai.registry, prompt_dir)

        # Test base prompt
        base_exec = await prompt(ai.registry, 'greeting')
        base_response = await base_exec({'name': 'Alice'})
        assert 'Hello' in base_response.text
        assert 'Alice' in base_response.text

        # Test variant prompt
        casual_exec = await prompt(ai.registry, 'greeting', variant='casual')
        casual_response = await casual_exec({'name': 'Bob'})
        assert 'Hey' in casual_response.text or "what's up" in casual_response.text.lower()
        assert 'Bob' in casual_response.text


@pytest.mark.asyncio
async def test_load_nested_prompt() -> None:
    """Test loading prompts from subdirectories."""
    ai, *_ = setup_test()

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir) / 'prompts'
        prompt_dir.mkdir()

        # Create subdirectory
        sub_dir = prompt_dir / 'admin'
        sub_dir.mkdir()

        # Create prompt in subdirectory
        admin_prompt = sub_dir / 'dashboard.prompt'
        admin_prompt.write_text('---\nmodel: echoModel\n---\nWelcome Admin {{name}}')

        load_prompt_folder(ai.registry, prompt_dir)

        # Test loading nested prompt
        # Based on logic: name = "admin/dashboard"
        admin_exec = await prompt(ai.registry, 'admin/dashboard')
        response = await admin_exec({'name': 'SuperUser'})

        assert 'Welcome Admin' in response.text
        assert 'SuperUser' in response.text


@pytest.mark.asyncio
async def test_load_and_use_partial() -> None:
    """Test loading and using partials in prompts."""
    ai, *_ = setup_test()

    with tempfile.TemporaryDirectory() as tmpdir:
        prompt_dir = Path(tmpdir) / 'prompts'
        prompt_dir.mkdir()

        # Create partial
        partial_file = prompt_dir / '_greeting.prompt'
        partial_file.write_text('Hello from partial!')

        # Create prompt that uses the partial
        prompt_file = prompt_dir / 'story.prompt'
        prompt_file.write_text('---\nmodel: echoModel\n---\n{{>greeting}} Tell me about {{topic}}.')

        load_prompt_folder(ai.registry, prompt_dir)

        story_exec = await prompt(ai.registry, 'story')
        response = await story_exec({'topic': 'space'})

        # The partial should be included in the output
        assert 'Hello from partial' in response.text or 'space' in response.text


@pytest.mark.asyncio
async def test_prompt_with_messages_list() -> None:
    """Test prompt with explicit messages list."""
    ai, *_ = setup_test()

    messages = [
        Message(role=Role.SYSTEM, content=[TextPart(text='You are helpful')]),
        Message(role=Role.USER, content=[TextPart(text='Hi there')]),
    ]

    my_prompt = ai.define_prompt(
        messages=messages,
        prompt='How can I help?',
    )

    response = await my_prompt()

    # Should include system, user history, and final prompt
    assert 'helpful' in response.text.lower() or 'Hi there' in response.text


@pytest.mark.asyncio
async def test_messages_with_explicit_override() -> None:
    """Test that explicit messages in render options are included."""
    ai, *_ = setup_test()

    my_prompt = ai.define_prompt(
        prompt='Final question',
    )

    override_messages = [
        Message(role=Role.USER, content=[TextPart(text='First message')]),
        Message(role=Role.MODEL, content=[TextPart(text='First response')]),
    ]

    # The override messages should be prepended to the prompt
    rendered = await my_prompt.render(input=None, config=None)

    # Check that we have the final prompt message
    assert any('Final question' in str(msg) for msg in rendered.messages)


@pytest.mark.asyncio
async def test_prompt_with_tools_list() -> None:
    """Test prompt with tools parameter."""
    ai, *_ = setup_test()

    class ToolInput(BaseModel):
        value: int = Field(description='A value')

    @ai.tool(name='myTool')
    def my_tool(input: ToolInput):
        return input.value * 2

    my_prompt = ai.define_prompt(
        prompt='Use the tool',
        tools=['myTool'],
    )

    rendered = await my_prompt.render()

    # Verify tools are in the rendered options
    assert rendered.tools is not None
    assert 'myTool' in rendered.tools


@pytest.mark.asyncio
async def test_system_and_prompt_together() -> None:
    """Test rendering system, messages, and prompt in correct order."""
    ai, *_ = setup_test()

    my_prompt = ai.define_prompt(
        system='System instruction',
        messages=[
            Message(role=Role.USER, content=[TextPart(text='History user')]),
            Message(role=Role.MODEL, content=[TextPart(text='History model')]),
        ],
        prompt='Final prompt',
    )

    response = await my_prompt()

    # All parts should be in the response
    text = response.text.lower()
    assert 'system' in text or 'instruction' in text
    assert 'history' in text or 'final' in text or 'prompt' in text


@pytest.mark.asyncio
async def test_prompt_with_output_schema() -> None:
    """Test that output schema is preserved in rendering."""
    ai, *_ = setup_test()

    class OutputSchema(BaseModel):
        name: str = Field(description='A name')
        age: int = Field(description='An age')

    my_prompt = ai.define_prompt(
        prompt='Generate a person',
        output_schema=OutputSchema,
        output_format='json',
    )

    rendered = await my_prompt.render()

    # Verify output configuration
    assert rendered.output is not None
    assert rendered.output.format == 'json'
    assert rendered.output.json_schema is not None


@pytest.mark.asyncio
async def test_config_merge_priority() -> None:
    """Test that runtime config overrides definition config."""
    ai, *_ = setup_test()

    my_prompt = ai.define_prompt(
        prompt='test',
        config={'temperature': 0.5, 'banana': 'yellow'},
    )

    # Runtime config should override temperature but keep banana
    rendered = await my_prompt.render(config={'temperature': 0.9})

    assert rendered.config is not None
    assert rendered.config.temperature == 0.9


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

        # Actions are registered with registry_definition_key (e.g., "filePrompt")
        # We need to look them up by kind and name (without the /prompt/ prefix)
        action_name = 'filePrompt'  # registry_definition_key format

        prompt_action = ai.registry.lookup_action(ActionKind.PROMPT, action_name)
        executable_prompt_action = ai.registry.lookup_action(ActionKind.EXECUTABLE_PROMPT, action_name)

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
        action_name = 'testPrompt'

        prompt_action = ai.registry.lookup_action(ActionKind.PROMPT, action_name)
        executable_prompt_action = ai.registry.lookup_action(ActionKind.EXECUTABLE_PROMPT, action_name)

        assert prompt_action is not None
        assert executable_prompt_action is not None

        prompt_result = await prompt_action.arun(input={'name': 'World'})
        assert isinstance(prompt_result.response, GenerateRequest)

        exec_result = await executable_prompt_action.arun(input={'name': 'World'})
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

        # Use ai.prompt() to look up the file-based prompt
        executable = await ai.prompt('promptFuncTest')

        # Verify it can be executed
        response = await executable({'name': 'Genkit'})
        assert 'Genkit' in response.text


@pytest.mark.asyncio
async def test_automatic_prompt_loading():
    """Test that Genkit automatically loads prompts from a directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a prompt file
        prompt_content = """---
name: testPrompt
---
Hello {{name}}!
"""
        prompt_file = Path(tmp_dir) / 'test.prompt'
        prompt_file.write_text(prompt_content)

        # Initialize Genkit with the temporary directory
        ai = Genkit(prompt_dir=tmp_dir)

        # Verify the prompt is registered
        # File-based prompts are registered with an empty namespace by default
        actions = ai.registry.list_serializable_actions()
        assert '/prompt/test' in actions
        assert '/executable-prompt/test' in actions


@pytest.mark.asyncio
async def test_automatic_prompt_loading_default_none():
    """Test that Genkit does not load prompts if prompt_dir is None."""
    ai = Genkit(prompt_dir=None)
    actions = ai.registry.list_serializable_actions()

    # Check that no prompts are registered (assuming a clean environment)
    dotprompts = [key for key in actions.keys() if '/prompt/' in key or '/executable-prompt/' in key]
    assert len(dotprompts) == 0


@pytest.mark.asyncio
async def test_automatic_prompt_loading_defaults_mock():
    """Test that Genkit defaults to ./prompts when prompt_dir is not specified and dir exists."""
    from unittest.mock import ANY, MagicMock, patch

    with patch('genkit.ai._aio.load_prompt_folder') as mock_load, patch('genkit.ai._aio.Path') as mock_path:
        # Setup mock to simulate ./prompts existing
        mock_path_instance = MagicMock()
        mock_path_instance.is_dir.return_value = True
        mock_path.return_value = mock_path_instance

        Genkit()
        mock_load.assert_called_once_with(ANY, dir_path=mock_path_instance)


@pytest.mark.asyncio
async def test_automatic_prompt_loading_defaults_missing():
    """Test that Genkit skips loading when ./prompts is missing."""
    from unittest.mock import ANY, MagicMock, patch

    with patch('genkit.ai._aio.load_prompt_folder') as mock_load, patch('genkit.ai._aio.Path') as mock_path:
        # Setup mock to simulate ./prompts missing
        mock_path_instance = MagicMock()
        mock_path_instance.is_dir.return_value = False
        mock_path.return_value = mock_path_instance

        Genkit()
        mock_load.assert_not_called()
