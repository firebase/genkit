# Copyright 2026 Google LLC
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

"""Google AI Interactions Deep Research background model action."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal, cast

from pydantic import BaseModel, ConfigDict, WithJsonSchema, field_validator, model_validator, with_config
from pydantic.alias_generators import to_camel, to_snake
from typing_extensions import NotRequired, TypedDict

from genkit import ActionRunContext, GenkitError, Operation, RuntimeErrorReason
from genkit.model import BackgroundAction, ModelRef, ModelRequest, model_ref
from genkit.plugin_api import Action, ActionKind, to_json_schema
from genkit_google_genai._interactions._client import (
    cancel_interaction,
    create_interaction,
    get_interaction,
)
from genkit_google_genai._interactions._converters import (
    clean_schema,
    from_interaction,
    to_interaction_tool,
)
from genkit_google_genai._interactions._options import ClientOptions
from genkit_google_genai._models._interactions_registry import deep_research_model_info
from genkit_google_genai._models._interactions_utils import (
    api_key_for_context,
    client_overrides_from_config,
    extract_version,
    lowercase_choice,
    lowercase_choice_list,
    partition_keys,
    remove_client_option_overrides,
    steps_with_folded_system_instruction,
)
from genkit_google_genai._models._secrets import reject_request_config_api_key

AGENT_CONFIG_KEYS = (
    'thinking_summaries',
    'visualization',
    'collaborative_planning',
)
TOOL_CONFIG_KEYS = (
    'google_search',
    'url_context',
    'code_execution',
    'file_search_store_names',
    'file_search_metadata_filter',
    'file_search_top_k',
    'mcp_servers',
)
CREATE_OPTION_KEYS = (
    'previous_interaction_id',
    'store',
    'response_modalities',
)


@with_config(ConfigDict(extra='allow'))
class McpServerConfig(TypedDict):
    """One ``mcp_servers`` entry for Deep Research.

    A TypedDict so a dict literal type-checks without importing it. Keys
    the Interactions API adds later pass through.
    """

    name: NotRequired[str]
    url: NotRequired[str]
    headers: NotRequired[dict[str, str]]
    allowed_tools: NotRequired[list[str]]


_MCP_SERVERS_SCHEMA = WithJsonSchema({
    'type': 'array',
    'items': {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'url': {'type': 'string'},
            'headers': {'type': 'object', 'additionalProperties': {'type': 'string'}},
            'allowedTools': {'type': 'array', 'items': {'type': 'string'}},
        },
    },
    'description': 'MCP servers Deep Research may call.',
})


class DeepResearchConfig(BaseModel):
    """Deep Research model configuration."""

    model_config = ConfigDict(extra='allow', validate_by_name=True, validate_by_alias=True, alias_generator=to_camel)
    base_url: str | None = None
    api_version: str | None = None
    # Milliseconds — applied to the HTTP call, not the create body.
    timeout: float | None = None
    custom_headers: dict[str, str] | None = None
    thinking_summaries: Literal['auto', 'none'] | None = None
    previous_interaction_id: str | None = None
    store: bool | None = None
    response_modalities: list[Literal['text', 'image', 'audio']] | None = None
    visualization: Literal['auto', 'off'] | None = None
    collaborative_planning: bool | None = None
    google_search: bool | None = None
    url_context: bool | None = None
    code_execution: bool | None = None
    file_search_store_names: list[str] | None = None
    file_search_metadata_filter: str | None = None
    file_search_top_k: int | None = None
    mcp_servers: Annotated[list[McpServerConfig] | None, _MCP_SERVERS_SCHEMA] = None

    @model_validator(mode='before')
    @classmethod
    def reject_nested_file_search(cls, data: object) -> object:
        """Unknown keys pass through to the API, so name the flat fields for the old nested one."""
        if isinstance(data, Mapping):
            for key in ('file_search', 'fileSearch'):
                if key in data:
                    names = ('file_search_store_names', 'file_search_metadata_filter', 'file_search_top_k')
                    if key == 'fileSearch':
                        names = tuple(to_camel(n) for n in names)
                    raise GenkitError(
                        status='INVALID_ARGUMENT',
                        message=f'{key} was flattened; use {" / ".join(names)}',
                        reason=RuntimeErrorReason.INVALID_INPUT,
                    )
        return data

    @field_validator('mcp_servers', mode='before')
    @classmethod
    def snake_case_mcp_keys(cls, value: object) -> object:
        """Accept ``allowedTools`` from .prompt files; the create body is snake_case."""
        if not isinstance(value, list):
            return value
        return [
            {to_snake(k): v for k, v in cast(Mapping[str, Any], entry).items()} if isinstance(entry, Mapping) else entry
            for entry in cast(list[object], value)
        ]

    @field_validator('thinking_summaries', 'visualization', mode='before')
    @classmethod
    def fold_choice_case(cls, value: object) -> object:
        """Accept AUTO/NONE the same as auto/none."""
        return lowercase_choice(value)

    @field_validator('response_modalities', mode='before')
    @classmethod
    def fold_modalities_case(cls, value: object) -> object:
        """Accept TEXT/IMAGE/AUDIO the same as lowercase wire values."""
        return lowercase_choice_list(value)


def deep_research_model(version: str) -> ModelRef:
    """Return a ModelRef for a Deep Research version (namespaced or bare)."""
    clean = extract_version(version)
    return model_ref(
        name=clean,
        namespace='googleai',
        info=deep_research_model_info(clean),
        config_schema=DeepResearchConfig,
    )


def build_tools(request: ModelRequest[DeepResearchConfig], config: DeepResearchConfig) -> list[dict[str, Any]]:
    """Build Interactions API tool configurations for Deep Research."""
    tools: list[dict[str, Any]] = []
    if request.tools:
        tools.extend(dict(to_interaction_tool(tool_def)) for tool_def in request.tools)

    for tool_type in ('google_search', 'url_context', 'code_execution'):
        if getattr(config, tool_type, None):
            tools.append({'type': tool_type})
    # The create body is snake_case, the same names the Gemini FileSearch tool takes.
    file_search = {
        key: value
        for key, value in (
            ('file_search_store_names', config.file_search_store_names),
            ('metadata_filter', config.file_search_metadata_filter),
            ('top_k', config.file_search_top_k),
        )
        if value is not None
    }
    if file_search:
        tools.append({'type': 'file_search', **file_search})
    for mcp_server in config.mcp_servers or []:
        tools.append({'type': 'mcp_server', **{k: v for k, v in mcp_server.items() if v is not None}})

    return tools


def response_format_from_request(
    request: ModelRequest[DeepResearchConfig],
) -> dict[str, Any] | None:
    """Build response_format when the caller asked for JSON output."""
    if request.output_format != 'json' and request.output_content_type != 'application/json':
        return None
    response_format: dict[str, Any] = {'type': 'text', 'mime_type': 'application/json'}
    if request.output_schema:
        # output_schema is already a JSON Schema dict. Dumping a model
        # by alias here would rename properties the constraint expects.
        response_format['schema'] = clean_schema(request.output_schema)
    return response_format


def create_deep_research_background_action(
    target: str | ModelRef,
    *,
    plugin_api_key: str | None,
    client_options: ClientOptions,
) -> BackgroundAction:
    """Wire Deep Research start/check/cancel as Actions that re-read secrets."""
    name = target.name if isinstance(target, ModelRef) else target
    version = extract_version(name)
    info = deep_research_model_info(version)
    full_name = name if '/' in name else f'googleai/{name}'
    action_key = f'/background-model/{full_name}'

    def persist(operation: Operation) -> Operation:
        operation.action = action_key
        return operation

    async def start(request: ModelRequest[DeepResearchConfig], ctx: ActionRunContext) -> Operation:
        reject_request_config_api_key(request.config)
        config = request.config or DeepResearchConfig()
        api_key = api_key_for_context(ctx.context, plugin_api_key)
        options = client_options.merge(client_overrides_from_config(config))

        dumped = remove_client_option_overrides(config.model_dump(exclude_none=True))
        agent_fields, _tool_fields, create_options, passthrough = partition_keys(
            dumped,
            AGENT_CONFIG_KEYS,
            TOOL_CONFIG_KEYS,
            CREATE_OPTION_KEYS,
        )
        agent_config: dict[str, Any] = {'type': 'deep-research', **agent_fields}

        tools = build_tools(request, config)
        response_format = response_format_from_request(request)
        create_kwargs: dict[str, Any] = {
            'agent': version,
            'input': steps_with_folded_system_instruction(request.messages),
            'background': True,
            'agent_config': agent_config,
            **create_options,
            **passthrough,
        }
        if tools:
            create_kwargs['tools'] = tools
        if response_format is not None:
            create_kwargs['response_format'] = response_format

        interaction = await create_interaction(api_key, create_kwargs, options)
        return persist(from_interaction(interaction))

    def _op_key_and_options(ctx: ActionRunContext) -> tuple[str, ClientOptions]:
        call_config = ctx.context.get('config')
        options = client_options.merge(call_config if isinstance(call_config, dict) else None)
        return api_key_for_context(ctx.context, plugin_api_key), options

    async def check(operation: Operation, ctx: ActionRunContext) -> Operation:
        api_key, options = _op_key_and_options(ctx)
        interaction = await get_interaction(api_key, operation.id, options)
        return persist(from_interaction(interaction))

    async def cancel(operation: Operation, ctx: ActionRunContext) -> Operation:
        api_key, options = _op_key_and_options(ctx)
        interaction = await cancel_interaction(api_key, operation.id, options)
        return persist(from_interaction(interaction))

    start_action = Action(
        kind=ActionKind.BACKGROUND_MODEL,
        name=full_name,
        fn=start,
        metadata={
            'model': {**info.model_dump(by_alias=True), 'customOptions': to_json_schema(DeepResearchConfig)},
            'type': 'background-model',
        },
    )
    check_action = Action(
        kind=ActionKind.CHECK_OPERATION,
        name=f'{full_name}/check',
        fn=check,
        metadata={'type': 'check-operation'},
    )
    cancel_action = Action(
        kind=ActionKind.CANCEL_OPERATION,
        name=f'{full_name}/cancel',
        fn=cancel,
        metadata={'type': 'cancel-operation'},
    )
    return BackgroundAction(
        start_action=start_action,
        check_action=check_action,
        cancel_action=cancel_action,
    )
