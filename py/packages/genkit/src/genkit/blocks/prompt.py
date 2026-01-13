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


"""Prompt management and templating for the Genkit framework.

This module provides types and utilities for managing prompts and templates
used with AI models in the Genkit framework. It enables consistent prompt
generation and management across different parts of the application.
"""

import os
import weakref
from asyncio import Future
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Awaitable

import structlog
from dotpromptz.typing import (
    DataArgument,
    PromptFunction,
    PromptInputConfig,
    PromptMetadata,
    ToolDefinition as DotPromptzToolDefinition,
)
from pydantic import BaseModel, ConfigDict

from genkit.aio import Channel, ensure_async
from genkit.blocks.generate import (
    StreamingCallback as ModelStreamingCallback,
    generate_action,
)
from genkit.blocks.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
    ModelMiddleware,
)
from genkit.core.action import Action, ActionRunContext, create_action_key
from genkit.core.action.types import ActionKind
from genkit.core.error import GenkitError
from genkit.core.registry import Registry
from genkit.core.schema import to_json_schema
from genkit.core.typing import (
    DocumentData,
    GenerateActionOptions,
    GenerateActionOutputConfig,
    GenerateRequest,
    GenerationCommonConfig,
    Message,
    OutputConfig,
    Part,
    Resume,
    Role,
    ToolChoice,
    Tools,
)

logger = structlog.get_logger(__name__)


class PromptCache:
    """Model for a prompt cache."""

    user_prompt: PromptFunction | None = None
    system: PromptFunction | None = None
    messages: PromptFunction | None = None


class PromptConfig(BaseModel):
    """Model for a prompt action."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    variant: str | None = None
    model: str | None = None
    config: GenerationCommonConfig | dict[str, Any] | None = None
    description: str | None = None
    input_schema: type | dict[str, Any] | None = None
    system: str | Part | list[Part] | Callable | None = None
    prompt: str | Part | list[Part] | Callable | None = None
    messages: str | list[Message] | Callable | None = None
    output_format: str | None = None
    output_content_type: str | None = None
    output_instructions: bool | str | None = None
    output_schema: type | dict[str, Any] | None = None
    output_constrained: bool | None = None
    max_turns: int | None = None
    return_tool_requests: bool | None = None
    metadata: dict[str, Any] | None = None
    tools: list[str] | None = None
    tool_choice: ToolChoice | None = None
    use: list[ModelMiddleware] | None = None
    docs: list[DocumentData] | Callable | None = None
    tool_responses: list[Part] | None = None


class ExecutablePrompt:
    """A prompt that can be executed with a given input and configuration."""

    def __init__(
        self,
        registry: Registry,
        variant: str | None = None,
        model: str | None = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        description: str | None = None,
        input_schema: type | dict[str, Any] | None = None,
        system: str | Part | list[Part] | Callable | None = None,
        prompt: str | Part | list[Part] | Callable | None = None,
        messages: str | list[Message] | Callable | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: type | dict[str, Any] | None = None,
        output_constrained: bool | None = None,
        max_turns: int | None = None,
        return_tool_requests: bool | None = None,
        metadata: dict[str, Any] | None = None,
        tools: list[str] | None = None,
        tool_choice: ToolChoice | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | Callable | None = None,
        _name: str | None = None,  # prompt name for action lookup
        _ns: str | None = None,  # namespace for action lookup
        _prompt_action: Action | None = None,  # reference to PROMPT action
        # TODO:
        #  docs: list[Document]):
    ):
        """Initializes an ExecutablePrompt instance.

        Args:
            registry: The registry to use for resolving models and tools.
            variant: The variant of the prompt.
            model: The model to use for generation.
            config: The generation configuration.
            description: A description of the prompt.
            input_schema: The input schema for the prompt.
            system: The system message for the prompt.
            prompt: The user prompt.
            messages: A list of messages to include in the prompt.
            output_format: The output format.
            output_content_type: The output content type.
            output_instructions: Instructions for formatting the output.
            output_schema: The output schema.
            output_constrained: Whether the output should be constrained to the output schema.
            max_turns: The maximum number of turns in a conversation.
            return_tool_requests: Whether to return tool requests.
            metadata: Metadata to associate with the prompt.
            tools: A list of tool names to use with the prompt.
            tool_choice: The tool choice strategy.
            use: A list of model middlewares to apply.
            docs: A list of documents to be used for grounding.
        """
        self._registry = registry
        self._variant = variant
        self._model = model
        self._config = config
        self._description = description
        self._input_schema = input_schema
        self._system = system
        self._prompt = prompt
        self._messages = messages
        self._output_format = output_format
        self._output_content_type = output_content_type
        self._output_instructions = output_instructions
        self._output_schema = output_schema
        self._output_constrained = output_constrained
        self._max_turns = max_turns
        self._return_tool_requests = return_tool_requests
        self._metadata = metadata
        self._tools = tools
        self._tool_choice = tool_choice
        self._use = use
        self._docs = docs
        self._cache_prompt = PromptCache()
        self._name = _name  # Store name/ns for action lookup (used by as_tool())
        self._ns = _ns
        self._prompt_action = _prompt_action

    @property
    def ref(self) -> dict[str, Any]:
        """Returns a reference object for this prompt.

        The reference object contains the prompt's name and metadata.
        """
        return {
            'name': registry_definition_key(self._name, self._variant, self._ns) if self._name else None,
            'metadata': self._metadata,
        }

    async def __call__(
        self,
        input: Any | None = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        on_chunk: ModelStreamingCallback | None = None,
        context: dict[str, Any] | None = None,
    ) -> GenerateResponseWrapper:
        """Executes the prompt with the given input and configuration.

        Args:
            input: The input to the prompt.
            config: The generation configuration.
            on_chunk: A callback function to be called for each chunk of the
                response.
            context: The action run context.

        Returns:
            The generated response.
        """
        return await generate_action(
            self._registry,
            await self.render(input=input, config=config, context=context),
            on_chunk=on_chunk,
            middleware=self._use,
            context=context if context else ActionRunContext._current_context(),
        )

    def stream(
        self,
        input: Any | None = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> tuple[
        AsyncIterator[GenerateResponseChunkWrapper],
        Future[GenerateResponseWrapper],
    ]:
        """Streams the prompt with the given input and configuration.

        Args:
            input: The input to the prompt.
            config: The generation configuration.
            context: The action run context.
            timeout: The timeout for the streaming action.

        Returns:
            A tuple containing an async iterator of response chunks and a future
            that resolves to the complete response.
        """
        stream = Channel(timeout=timeout)

        resp = self.__call__(
            input=input,
            config=config,
            context=context,
            on_chunk=lambda c: stream.send(c),
        )
        stream.set_close_future(resp)

        return (stream, stream.closed)

    async def render(
        self,
        input: dict[str, Any] | None = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> GenerateActionOptions:
        """Renders the prompt with the given input and configuration.

        Args:
            input: The input to the prompt.
            config: The generation configuration.

        Returns:
            The rendered prompt as a GenerateActionOptions object.
        """
        # TODO: run str prompt/system/message through dotprompt using input

        options = PromptConfig(
            model=self._model,
            prompt=self._prompt,
            system=self._system,
            messages=self._messages,
            tools=self._tools,
            return_tool_requests=self._return_tool_requests,
            tool_choice=self._tool_choice,
            config=config if config else self._config,
            max_turns=self._max_turns,
            output_format=self._output_format,
            output_content_type=self._output_content_type,
            output_instructions=self._output_instructions,
            output_schema=self._output_schema,
            output_constrained=self._output_constrained,
            input_schema=self._input_schema,
            metadata=self._metadata,
            docs=self._docs,
        )

        model = options.model or self._registry.default_model
        if model is None:
            raise Exception('No model configured.')
        resolved_msgs: list[Message] = []
        if options.system:
            result = await render_system_prompt(self._registry, input, options, self._cache_prompt, context)
            resolved_msgs.append(result)
        if options.messages:
            resolved_msgs.extend(
                await render_message_prompt(self._registry, input, options, self._cache_prompt, context)
            )
        if options.prompt:
            result = await render_user_prompt(self._registry, input, options, self._cache_prompt, context)
            resolved_msgs.append(result)

        # If is schema is set but format is not explicitly set, default to
        # `json` format.
        if options.output_schema and not options.output_format:
            output_format = 'json'
        else:
            output_format = options.output_format

        output = GenerateActionOutputConfig()
        if output_format:
            output.format = output_format
        if options.output_content_type:
            output.content_type = options.output_content_type
        if options.output_instructions is not None:
            output.instructions = options.output_instructions
        if options.output_schema:
            output.json_schema = to_json_schema(options.output_schema)
        if options.output_constrained is not None:
            output.constrained = options.output_constrained

        resume = None
        if options.tool_responses:
            resume = Resume(respond=[r.root for r in options.tool_responses])

        return GenerateActionOptions(
            model=model,
            messages=resolved_msgs,
            config=options.config,
            tools=options.tools,
            return_tool_requests=options.return_tool_requests,
            tool_choice=options.tool_choice,
            output=output,
            max_turns=options.max_turns,
            docs=await render_docs(input, options, context),
            resume=resume,
        )

    async def as_tool(self) -> Action:
        """Expose this prompt as a tool.

        Returns the PROMPT action, which can be used as a tool.
        """
        # If we have a direct reference to the action, use it
        if self._prompt_action is not None:
            return self._prompt_action

        # Otherwise, try to look it up using name/variant/ns
        if self._name is None:
            raise GenkitError(
                status='FAILED_PRECONDITION',
                message='Prompt name not available. This prompt was not created via define_prompt_async() or load_prompt().',
            )

        lookup_key = registry_lookup_key(self._name, self._variant, self._ns)

        action = self._registry.lookup_action_by_key(lookup_key)

        if action is None or action.kind != ActionKind.PROMPT:
            raise GenkitError(
                status='NOT_FOUND',
                message=f'PROMPT action not found for prompt "{self._name}"',
            )

        return action


def define_prompt(
    registry: Registry,
    name: str | None = None,
    variant: str | None = None,
    model: str | None = None,
    config: GenerationCommonConfig | dict[str, Any] | None = None,
    description: str | None = None,
    input_schema: type | dict[str, Any] | None = None,
    system: str | Part | list[Part] | Callable | None = None,
    prompt: str | Part | list[Part] | Callable | None = None,
    messages: str | list[Message] | Callable | None = None,
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_schema: type | dict[str, Any] | None = None,
    output_constrained: bool | None = None,
    max_turns: int | None = None,
    return_tool_requests: bool | None = None,
    metadata: dict[str, Any] | None = None,
    tools: list[str] | None = None,
    tool_choice: ToolChoice | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[DocumentData] | Callable | None = None,
) -> ExecutablePrompt:
    """Defines an executable prompt.

    Args:
        registry: The registry to use for resolving models and tools.
        name: The name of the prompt.
        variant: The variant of the prompt.
        model: The model to use for generation.
        config: The generation configuration.
        description: A description of the prompt.
        input_schema: The input schema for the prompt.
        system: The system message for the prompt.
        prompt: The user prompt.
        messages: A list of messages to include in the prompt.
        output_format: The output format.
        output_content_type: The output content type.
        output_instructions: Instructions for formatting the output.
        output_schema: The output schema.
        output_constrained: Whether the output should be constrained to the output schema.
        max_turns: The maximum number of turns in a conversation.
        return_tool_requests: Whether to return tool requests.
        metadata: Metadata to associate with the prompt.
        tools: A list of tool names to use with the prompt.
        tool_choice: The tool choice strategy.
        use: A list of model middlewares to apply.
        docs: A list of documents to be used for grounding.

    Returns:
        An ExecutablePrompt instance.
    """
    executable_prompt = ExecutablePrompt(
        registry,
        variant=variant,
        model=model,
        config=config,
        description=description,
        input_schema=input_schema,
        system=system,
        prompt=prompt,
        messages=messages,
        output_format=output_format,
        output_content_type=output_content_type,
        output_instructions=output_instructions,
        output_schema=output_schema,
        output_constrained=output_constrained,
        max_turns=max_turns,
        return_tool_requests=return_tool_requests,
        metadata=metadata,
        tools=tools,
        tool_choice=tool_choice,
        use=use,
        docs=docs,
        _name=name,
    )

    if name:
        # Register actions for this prompt
        action_metadata = {
            'type': 'prompt',
            'source': 'programmatic',
            'prompt': {
                'name': name,
                'variant': variant or '',
            },
        }

        async def prompt_action_fn(input: Any = None) -> GenerateRequest:
            """PROMPT action function - renders prompt and returns GenerateRequest."""
            options = await executable_prompt.render(input=input)
            return await to_generate_request(registry, options)

        async def executable_prompt_action_fn(input: Any = None) -> GenerateActionOptions:
            """EXECUTABLE_PROMPT action function - renders prompt and returns GenerateActionOptions."""
            return await executable_prompt.render(input=input)

        action_name = registry_definition_key(name, variant)
        prompt_action = registry.register_action(
            kind=ActionKind.PROMPT,
            name=action_name,
            fn=prompt_action_fn,
            metadata=action_metadata,
        )

        executable_prompt_action = registry.register_action(
            kind=ActionKind.EXECUTABLE_PROMPT,
            name=action_name,
            fn=executable_prompt_action_fn,
            metadata=action_metadata,
        )

        # Link them
        executable_prompt._prompt_action = prompt_action
        prompt_action._executable_prompt = weakref.ref(executable_prompt)
        executable_prompt_action._executable_prompt = weakref.ref(executable_prompt)

    return executable_prompt


async def to_generate_action_options(registry: Registry, options: PromptConfig) -> GenerateActionOptions:
    """Converts the given parameters to a GenerateActionOptions object.

    Args:
        registry: The registry to use for resolving models and tools.
        options: The prompt configuration.

    Returns:
        A GenerateActionOptions object.
    """
    model = options.model or registry.default_model
    if model is None:
        raise Exception('No model configured.')

    cache = PromptCache()
    resolved_msgs: list[Message] = []
    if options.system:
        result = await render_system_prompt(registry, None, options, cache)
        resolved_msgs.append(result)
    if options.messages:
        resolved_msgs.extend(await render_message_prompt(registry, None, options, cache))
    if options.prompt:
        result = await render_user_prompt(registry, None, options, cache)
        resolved_msgs.append(result)

    # If is schema is set but format is not explicitly set, default to
    # `json` format.
    if options.output_schema and not options.output_format:
        output_format = 'json'
    else:
        output_format = options.output_format

    output = GenerateActionOutputConfig()
    if output_format:
        output.format = output_format
    if options.output_content_type:
        output.content_type = options.output_content_type
    if options.output_instructions is not None:
        output.instructions = options.output_instructions
    if options.output_schema:
        output.json_schema = to_json_schema(options.output_schema)
    if options.output_constrained is not None:
        output.constrained = options.output_constrained

    resume = None
    if options.tool_responses:
        resume = Resume(respond=[r.root for r in options.tool_responses])

    return GenerateActionOptions(
        model=model,
        messages=resolved_msgs,
        config=options.config,
        tools=options.tools,
        return_tool_requests=options.return_tool_requests,
        tool_choice=options.tool_choice,
        output=output,
        max_turns=options.max_turns,
        docs=await render_docs(None, options),
        resume=resume,
    )


async def to_generate_request(registry: Registry, options: GenerateActionOptions) -> GenerateRequest:
    """Converts GenerateActionOptions to a GenerateRequest.

    This function resolves tool names into their respective tool definitions
    by looking them up in the provided registry. it also validates that the
    provided options contain at least one message.

    Args:
        registry: The Registry instance used to look up tool actions.
        options: The GenerateActionOptions containing the configuration,
            messages, and tool references to be converted.

    Returns:
        A GenerateRequest object populated with messages, config, resolved
        tools, and output configurations.

    Raises:
        Exception: If a tool name provided in options cannot be found in
            the registry.
        GenkitError: If the options do not contain any messages.
    """

    tools: list[Action] = []
    if options.tools:
        for tool_name in options.tools:
            tool_action = registry.lookup_action(ActionKind.TOOL, tool_name)
            if tool_action is None:
                raise GenkitError(status='NOT_FOUND', message=f'Unable to resolve tool {tool_name}')
            tools.append(tool_action)

    tool_defs = [to_tool_definition(tool) for tool in tools] if tools else []

    if not options.messages:
        raise GenkitError(
            status='INVALID_ARGUMENT',
            message='at least one message is required in generate request',
        )

    return GenerateRequest(
        messages=options.messages,
        config=options.config if options.config is not None else {},
        docs=options.docs,
        tools=tool_defs,
        tool_choice=options.tool_choice,
        output=OutputConfig(
            content_type=options.output.content_type if options.output else None,
            format=options.output.format if options.output else None,
            schema_=options.output.json_schema if options.output else None,
            constrained=options.output.constrained if options.output else None,
        ),
    )


def _normalize_prompt_arg(
    prompt: str | Part | list[Part] | None,
) -> list[Part] | None:
    """Normalizes different prompt input types into a list of Parts.

    Ensures that the prompt content, whether provided as a string, a single Part,
    or a list of Parts, is consistently represented as a list of Part objects.

    Args:
        prompt: The prompt input, which can be a string, a Part, a list of Parts,
            or None.

    Returns:
        A list containing the normalized Part(s), or None if the input `prompt`
        was None.
    """
    if not prompt:
        return None
    if isinstance(prompt, str):
        return [Part(text=prompt)]
    elif hasattr(prompt, '__len__'):
        return prompt
    else:
        return [prompt]


async def render_system_prompt(
    registry: Registry,
    input: dict[str, Any],
    options: PromptConfig,
    prompt_cache: PromptCache,
    context: dict[str, Any] | None = None,
) -> Message:
    """Renders the system prompt for a prompt action.

    This function handles rendering system prompts by either:
    1. Processing dotprompt templates if the system prompt is a string
    2. Normalizing the system prompt into a list of Parts if it's a Part or list of Parts

    Args:
        registry: Registry instance for resolving models and tools
        input: Dictionary of input values for template rendering
        options: Configuration options for the prompt
        prompt_cache: Cache for compiled prompt templates
        context: Optional dictionary of context values for template rendering

    Returns:
        Message: A Message object containing the rendered system prompt with Role.SYSTEM

    """

    if isinstance(options.system, str):
        if prompt_cache.system is None:
            prompt_cache.system = await registry.dotprompt.compile(options.system)

        if options.metadata:
            context = {**(context or {}), 'state': options.metadata.get('state')}

        return Message(
            role=Role.SYSTEM,
            content=await render_dotprompt_to_parts(
                context,
                prompt_cache.system,
                input,
                PromptMetadata(
                    input=PromptInputConfig(
                        schema=to_json_schema(options.input_schema) if options.input_schema else None,
                    )
                ),
            ),
        )

    if callable(options.system):
        resolved = await ensure_async(options.system)(input, context)
        return Message(role=Role.SYSTEM, content=_normalize_prompt_arg(resolved))

    return Message(role=Role.SYSTEM, content=_normalize_prompt_arg(options.system))


async def render_dotprompt_to_parts(
    context: dict[str, Any],
    prompt_function: PromptFunction,
    input_: dict[str, Any],
    options: PromptMetadata | None = None,
) -> list[Part]:
    """Renders a prompt template into a list of content parts using dotprompt.

    Args:
        context: Dictionary containing context variables available to the prompt template.
        prompt_function: The compiled dotprompt function to execute.
        input_: Dictionary containing input variables for the prompt template.
        options: Optional prompt metadata configuration.

    Returns:
        A list of Part objects containing the rendered content.

    Raises:
        Exception: If the template produces more than one message.
    """
    # Flatten input and context for template resolution
    flattened_data = {**(context or {}), **(input_ or {})}
    rendered = await prompt_function(
        data=DataArgument[dict[str, Any]](
            input=flattened_data,
            context=context,
        ),
        options=options,
    )

    if len(rendered.messages) > 1:
        raise Exception('parts template must produce only one message')

    part_rendered = []
    for message in rendered.messages:
        for part in message.content:
            part_rendered.append(part.model_dump())

    return part_rendered


async def render_message_prompt(
    registry: Registry,
    input: dict[str, Any],
    options: PromptConfig,
    prompt_cache: PromptCache,
    context: dict[str, Any] | None = None,
) -> list[Message]:
    """
    Render a message prompt using a given registry, input data, options, and a context.

    This function processes different types of message options (string or list) to render
    appropriate messages using a prompt registry and cache. If the `messages` option is of type
    string, the function compiles the dotprompt messages from the `registry` and applies data
    and metadata context. If the `messages` option is of type list, it either validates and
    returns the list or processes it for message rendering. The function ensures correct message
    output using the provided input, prompt configuration, and caching mechanism.

    Arguments:
        registry (Registry): The registry used to compile dotprompt messages.
        input (dict[str, Any]): The input data to render messages.
        options (PromptConfig): Configuration containing prompt options and message settings.
        prompt_cache (PromptCache): Cache to store compiled prompt results.
        context (dict[str, Any] | None): Optional additional context to be used for rendering.
            Defaults to None.

    Returns:
        list[Message]: A list of rendered or validated message objects.
    """
    if isinstance(options.messages, str):
        if prompt_cache.messages is None:
            prompt_cache.messages = await registry.dotprompt.compile(options.messages)

        if options.metadata:
            context = {**(context or {}), 'state': options.metadata.get('state')}

        messages_ = None
        if isinstance(options.messages, list):
            messages_ = [e.model_dump() for e in options.messages]

        # Flatten input and context for template resolution
        flattened_data = {**(context or {}), **(input or {})}
        rendered = await prompt_cache.messages(
            data=DataArgument[dict[str, Any]](
                input=flattened_data,
                context=context,
                messages=messages_,
            ),
            options=PromptMetadata(
                input=PromptInputConfig(
                    schema=to_json_schema(options.input_schema) if options.input_schema else None,
                )
            ),
        )
        return [Message.model_validate(e.model_dump()) for e in rendered.messages]

    elif isinstance(options.messages, list):
        return options.messages

    elif callable(options.messages):
        resolved = await ensure_async(options.messages)(input, context)
        return resolved

    raise TypeError(f'Unsupported type for messages: {type(options.messages)}')


async def render_user_prompt(
    registry: Registry,
    input: dict[str, Any],
    options: PromptConfig,
    prompt_cache: PromptCache,
    context: dict[str, Any] | None = None,
) -> Message:
    """
    Asynchronously renders a user prompt based on the given input, context, and options,
    utilizing a pre-compiled or dynamically compiled dotprompt template.

    Arguments:
        registry (Registry): The registry instance used to compile dotprompt templates.
        Input (dict[str, Any]): The input data used to populate the prompt.
        Options (PromptConfig): The configuration for rendering the prompt, including
            the template type and associated metadata.
        Prompt_cache (PromptCache): A cache that stores pre-compiled prompt templates to
            optimize rendering.
        Context (dict[str, Any] | None): Optional dynamic context data to override or
            supplement in the rendering process.

    Returns:
        Message: A Message instance containing the rendered user prompt.
    """
    if isinstance(options.prompt, str):
        if prompt_cache.user_prompt is None:
            prompt_cache.user_prompt = await registry.dotprompt.compile(options.prompt)

        if options.metadata:
            context = {**(context or {}), 'state': options.metadata.get('state')}

        return Message(
            role=Role.USER,
            content=await render_dotprompt_to_parts(
                context,
                prompt_cache.user_prompt,
                input,
                PromptMetadata(
                    input=PromptInputConfig(
                        schema=to_json_schema(options.input_schema) if options.input_schema else None,
                    )
                ),
            ),
        )

    if callable(options.prompt):
        resolved = await ensure_async(options.prompt)(input, context)
        return Message(role=Role.USER, content=_normalize_prompt_arg(resolved))

    return Message(role=Role.USER, content=_normalize_prompt_arg(options.prompt))


async def render_docs(
    input: dict[str, Any],
    options: PromptConfig,
    context: dict[str, Any] | None = None,
) -> list[DocumentData] | None:
    """Renders the docs for a prompt action.

    Args:
        input: Dictionary of input values.
        options: Configuration options for the prompt.
        context: Optional dictionary of context values.

    Returns:
        A list of DocumentData objects or None.
    """
    if options.docs is None:
        return None

    if callable(options.docs):
        return await ensure_async(options.docs)(input, context)

    return options.docs


def registry_definition_key(name: str, variant: str | None = None, ns: str | None = None) -> str:
    """Generate a registry definition key for a prompt.

    Format: "ns/name.variant" where ns and variant are optional.

    Args:
        name: The prompt name.
        variant: Optional variant name.
        ns: Optional namespace.

    Returns:
        Registry key string.
    """
    parts = []
    if ns:
        parts.append(ns)
    parts.append(name)
    if variant:
        parts[-1] = f'{parts[-1]}.{variant}'
    return '/'.join(parts)


def registry_lookup_key(name: str, variant: str | None = None, ns: str | None = None) -> str:
    """Generate a registry lookup key for a prompt.

    Args:
        name: The prompt name.
        variant: Optional variant name.
        ns: Optional namespace.

    Returns:
        Registry lookup key string.
    """
    return f'/prompt/{registry_definition_key(name, variant, ns)}'


def define_partial(registry: Registry, name: str, source: str) -> None:
    """Define a partial template in the registry.

    Partials are reusable template fragments that can be included in other prompts.
    Files starting with `_` are treated as partials.

    Args:
        registry: The registry to register the partial in.
        name: The name of the partial.
        source: The template source code.
    """
    registry.dotprompt.define_partial(name, source)
    logger.debug(f'Registered Dotprompt partial "{name}"')


def define_helper(registry: Registry, name: str, fn: Callable) -> None:
    """Define a Handlebars helper function in the registry.

    Args:
        registry: The registry to register the helper in.
        name: The name of the helper function.
        fn: The helper function to register.
    """
    registry.dotprompt.define_helper(name, fn)
    logger.debug(f'Registered Dotprompt helper "{name}"')


def load_prompt(registry: Registry, path: Path, filename: str, prefix: str = '', ns: str = '') -> None:
    """Load a single prompt file and register it in the registry.

    This function loads a .prompt file, parses it, and registers it as a lazy-loaded
    prompt that will only be fully loaded when first accessed.

    Args:
        registry: The registry to register the prompt in.
        path: Base path to the prompts directory.
        filename: Name of the prompt file (e.g., "myPrompt.prompt" or "myPrompt.variant.prompt").
        prefix: Subdirectory prefix (for namespacing).
        ns: Namespace for the prompt.
    """
    # Extract name and variant from filename
    # "myPrompt.prompt" -> name="myPrompt", variant=None
    # "myPrompt.variant.prompt" -> name="myPrompt", variant="variant"
    # "subdir/myPrompt.prompt" -> name="subdir/myPrompt", variant=None
    if not filename.endswith('.prompt'):
        raise ValueError(f"Invalid prompt filename: {filename}. Must end with '.prompt'")

    base_name = filename.removesuffix('.prompt')

    if prefix:
        name = f'{prefix}{base_name}'
    else:
        name = base_name
    variant: str | None = None

    # Extract variant (only takes parts[1], not all remaining parts)
    if '.' in name:
        parts = name.split('.')
        name = parts[0]
        variant = parts[1]  # Only first part after split

    # Build full file path
    # prefix may have trailing slash, so we need to handle it
    if prefix:
        # Strip trailing slash for path construction (pathlib handles it)
        prefix_clean = prefix.rstrip('/')
        file_path = path / prefix_clean / filename
    else:
        file_path = path / filename

    # Read the prompt file
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # Parse the prompt
    parsed_prompt = registry.dotprompt.parse(source)

    # Generate registry key
    registry_key = registry_definition_key(name, variant, ns)

    # Create a lazy-loaded prompt definition
    # The prompt will only be fully loaded when first accessed
    async def load_prompt_metadata():
        """Lazy loader for prompt metadata."""
        prompt_metadata = await registry.dotprompt.render_metadata(parsed_prompt)

        # Convert Pydantic model to dict if needed
        if hasattr(prompt_metadata, 'model_dump'):
            prompt_metadata_dict = prompt_metadata.model_dump()
        elif hasattr(prompt_metadata, 'dict'):
            prompt_metadata_dict = prompt_metadata.dict()
        else:
            # Already a dict
            prompt_metadata_dict = prompt_metadata

        if variant:
            prompt_metadata_dict['variant'] = variant

        # Clean up null descriptions
        output = prompt_metadata_dict.get('output')
        if output and isinstance(output, dict):
            schema = output.get('schema')
            if schema and isinstance(schema, dict) and schema.get('description') is None:
                schema.pop('description', None)

        input_schema = prompt_metadata_dict.get('input')
        if input_schema and isinstance(input_schema, dict):
            schema = input_schema.get('schema')
            if schema and isinstance(schema, dict) and schema.get('description') is None:
                schema.pop('description', None)

        # Build metadata structure
        metadata = {
            **prompt_metadata_dict.get('metadata', {}),
            'type': 'prompt',
            'prompt': {
                **prompt_metadata_dict,
                'template': parsed_prompt.template,
            },
        }

        raw = prompt_metadata_dict.get('raw')
        if raw and isinstance(raw, dict) and raw.get('metadata'):
            metadata['metadata'] = {**raw['metadata']}

        output = prompt_metadata_dict.get('output')
        input_schema = prompt_metadata_dict.get('input')
        raw = prompt_metadata_dict.get('raw')

        return {
            'name': registry_key,
            'model': prompt_metadata_dict.get('model'),
            'config': prompt_metadata_dict.get('config'),
            'tools': prompt_metadata_dict.get('tools'),
            'description': prompt_metadata_dict.get('description'),
            'output': {
                'jsonSchema': output.get('schema') if output and isinstance(output, dict) else None,
                'format': output.get('format') if output and isinstance(output, dict) else None,
            },
            'input': {
                'jsonSchema': input_schema.get('schema') if input_schema and isinstance(input_schema, dict) else None,
            },
            'metadata': metadata,
            'maxTurns': raw.get('maxTurns') if raw and isinstance(raw, dict) else None,
            'toolChoice': raw.get('toolChoice') if raw and isinstance(raw, dict) else None,
            'returnToolRequests': raw.get('returnToolRequests') if raw and isinstance(raw, dict) else None,
            'messages': parsed_prompt.template,
        }

    # Create a factory function that will create the ExecutablePrompt when accessed
    # Store metadata in a closure to avoid global state
    async def create_prompt_from_file():
        """Factory function to create ExecutablePrompt from file metadata."""
        metadata = await load_prompt_metadata()

        # Create ExecutablePrompt from metadata
        # Pass name/ns so as_tool() can look up the action
        executable_prompt = ExecutablePrompt(
            registry=registry,
            variant=metadata.get('variant'),
            model=metadata.get('model'),
            config=metadata.get('config'),
            description=metadata.get('description'),
            input_schema=metadata.get('input', {}).get('jsonSchema'),
            output_schema=metadata.get('output', {}).get('jsonSchema'),
            output_format=metadata.get('output', {}).get('format'),
            messages=metadata.get('messages'),
            max_turns=metadata.get('maxTurns'),
            tool_choice=metadata.get('toolChoice'),
            return_tool_requests=metadata.get('returnToolRequests'),
            metadata=metadata.get('metadata'),
            tools=metadata.get('tools'),
            _name=name,  # Store name for action lookup
            _ns=ns,  # Store namespace for action lookup
        )

        # Store reference to PROMPT action on the ExecutablePrompt
        # Actions are already registered at this point (lazy loading happens after registration)
        lookup_key = registry_lookup_key(name, variant, ns)
        prompt_action = registry.lookup_action_by_key(lookup_key)
        if prompt_action and prompt_action.kind == ActionKind.PROMPT:
            executable_prompt._prompt_action = prompt_action
            # Also store ExecutablePrompt reference on the action
            # prompt_action._executable_prompt = executable_prompt
            prompt_action._executable_prompt = weakref.ref(executable_prompt)

        return executable_prompt

    # Store the async factory in a way that can be accessed later
    # We'll store it in the action metadata
    action_metadata = {
        'type': 'prompt',
        'lazy': True,
        'source': 'file',
        'prompt': {
            'name': name,
            'variant': variant or '',
        },
    }

    # Create two separate action functions :
    # 1. PROMPT action - returns GenerateRequest (for rendering prompts)
    # 2. EXECUTABLE_PROMPT action - returns GenerateActionOptions (for executing prompts)

    async def prompt_action_fn(input: Any = None) -> GenerateRequest:
        """PROMPT action function - renders prompt and returns GenerateRequest."""
        # Load the prompt (lazy loading)
        prompt = await create_prompt_from_file()

        # Render the prompt with input to get GenerateActionOptions
        options = await prompt.render(input=input)

        # Convert GenerateActionOptions to GenerateRequest
        return await to_generate_request(registry, options)

    async def executable_prompt_action_fn(input: Any = None) -> GenerateActionOptions:
        """EXECUTABLE_PROMPT action function - renders prompt and returns GenerateActionOptions."""
        # Load the prompt (lazy loading)
        prompt = await create_prompt_from_file()

        # Render the prompt with input to get GenerateActionOptions
        return await prompt.render(input=input)

    # Register the PROMPT action
    # Use registry_definition_key for the action name (not registry_lookup_key)
    # The action name should be just the definition key (e.g., "dotprompt/testPrompt"),
    # not the full lookup key (e.g., "/prompt/dotprompt/testPrompt")
    action_name = registry_definition_key(name, variant, ns)
    prompt_action = registry.register_action(
        kind=ActionKind.PROMPT,
        name=action_name,
        fn=prompt_action_fn,
        metadata=action_metadata,
    )

    # Register the EXECUTABLE_PROMPT action
    executable_prompt_action = registry.register_action(
        kind=ActionKind.EXECUTABLE_PROMPT,
        name=action_name,
        fn=executable_prompt_action_fn,
        metadata=action_metadata,
    )

    # Store the factory function on both actions for easy access
    prompt_action._async_factory = create_prompt_from_file
    executable_prompt_action._async_factory = create_prompt_from_file

    # Store ExecutablePrompt reference on actions
    # This will be set when the prompt is first accessed (lazy loading)
    # We'll update it in create_prompt_from_file after the prompt is created

    logger.debug(f'Registered prompt "{registry_key}" from "{file_path}"')


def load_prompt_folder_recursively(registry: Registry, dir_path: Path, ns: str, sub_dir: str = '') -> None:
    """Recursively load all prompt files from a directory.

    Args:
        registry: The registry to register prompts in.
        dir_path: Base path to the prompts directory.
        ns: Namespace for prompts.
        sub_dir: Current subdirectory being processed (for recursion).
    """
    full_path = dir_path / sub_dir if sub_dir else dir_path

    if not full_path.exists() or not full_path.is_dir():
        return

    # Iterate through directory entries
    try:
        for entry in os.scandir(full_path):
            if entry.is_file() and entry.name.endswith('.prompt'):
                if entry.name.startswith('_'):
                    # This is a partial
                    partial_name = entry.name[1:-7]  # Remove "_" prefix and ".prompt" suffix
                    with open(entry.path, 'r', encoding='utf-8') as f:
                        source = f.read()

                    # Strip frontmatter if present
                    if source.startswith('---'):
                        end_frontmatter = source.find('---', 3)
                        if end_frontmatter != -1:
                            source = source[end_frontmatter + 3 :].strip()

                    define_partial(registry, partial_name, source)
                    logger.debug(f'Registered Dotprompt partial "{partial_name}" from "{entry.path}"')
                else:
                    # This is a regular prompt
                    prefix_with_slash = f'{sub_dir}/' if sub_dir else ''
                    load_prompt(registry, dir_path, entry.name, prefix_with_slash, ns)
            elif entry.is_dir():
                # Recursively process subdirectories
                new_sub_dir = os.path.join(sub_dir, entry.name) if sub_dir else entry.name
                load_prompt_folder_recursively(registry, dir_path, ns, new_sub_dir)
    except PermissionError:
        logger.warning(f'Permission denied accessing directory: {full_path}')
    except Exception as e:
        logger.error(f'Error loading prompts from {full_path}: {e}')


def load_prompt_folder(registry: Registry, dir_path: str | Path = './prompts', ns: str = '') -> None:
    """Load all prompt files from a directory.

    This is the main entry point for loading prompts from a directory.
    It recursively processes all `.prompt` files and registers them.

    Args:
        registry: The registry to register prompts in.
        dir_path: Path to the prompts directory. Defaults to './prompts'.
        ns: Namespace for prompts. Defaults to 'dotprompt'.
    """
    path = Path(dir_path).resolve()

    if not path.exists():
        logger.warning(f'Prompt directory does not exist: {path}')
        return

    if not path.is_dir():
        logger.warning(f'Prompt path is not a directory: {path}')
        return

    load_prompt_folder_recursively(registry, path, ns, '')
    logger.info(f'Loaded prompts from directory: {path}')


async def lookup_prompt(registry: Registry, name: str, variant: str | None = None) -> ExecutablePrompt:
    """Look up a prompt from the registry.

    Args:
        registry: The registry to look up the prompt from.
        name: The name of the prompt.
        variant: Optional variant name.

    Returns:
        An ExecutablePrompt instance.

    Raises:
        GenkitError: If the prompt is not found.
    """
    # Try without namespace first (for programmatic prompts)
    # Use create_action_key to build the full key: "/prompt/<definition_key>"
    definition_key = registry_definition_key(name, variant, None)
    lookup_key = create_action_key(ActionKind.PROMPT, definition_key)
    action = registry.lookup_action_by_key(lookup_key)

    # If not found and no namespace was specified, try with default 'dotprompt' namespace
    # (for file-based prompts)
    if not action:
        definition_key = registry_definition_key(name, variant, 'dotprompt')
        lookup_key = create_action_key(ActionKind.PROMPT, definition_key)
        action = registry.lookup_action_by_key(lookup_key)

    if action:
        # First check if we've stored the ExecutablePrompt directly
        if hasattr(action, '_executable_prompt') and action._executable_prompt is not None:
            return action._executable_prompt
        elif hasattr(action, '_async_factory'):
            # Otherwise, create it from the factory (lazy loading)
            # This will also set _executable_prompt on the action for future lookups
            executable_prompt = await action._async_factory()
            # Store it on the action for future lookups (if not already stored)
            if not hasattr(action, '_executable_prompt') or action._executable_prompt is None:
                action._executable_prompt = executable_prompt
            return executable_prompt
        else:
            # Fallback: try to get from metadata
            factory = action.metadata.get('_async_factory')
            if factory:
                executable_prompt = await factory()
                # Store it on the action for future lookups
                if not hasattr(action, '_executable_prompt') or action._executable_prompt is None:
                    action._executable_prompt = executable_prompt
                return executable_prompt
            # Last resort: this shouldn't happen if prompts are loaded correctly
            raise GenkitError(
                status='INTERNAL',
                message=f'Prompt action found but no ExecutablePrompt available for {name}',
            )

    variant_str = f' (variant {variant})' if variant else ''
    raise GenkitError(
        status='NOT_FOUND',
        message=f'Prompt {name}{variant_str} not found',
    )


async def prompt(
    registry: Registry,
    name: str,
    variant: str | None = None,
    dir: str | Path | None = None,  # Accepted but not used
) -> ExecutablePrompt:
    """Look up a prompt by name and optional variant.

    Can look up prompts that were:
    1. Defined programmatically using define_prompt()
    2. Loaded from .prompt files using load_prompt_folder()

    Args:
        registry: The registry to look up the prompt from.
        name: The name of the prompt.
        variant: Optional variant name.
        dir: Optional directory parameter (accepted for compatibility but not used).

    Returns:
        An ExecutablePrompt instance.

    Raises:
        GenkitError: If the prompt is not found.
    """

    return await lookup_prompt(registry, name, variant)
