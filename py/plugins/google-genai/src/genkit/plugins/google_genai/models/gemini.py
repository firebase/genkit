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

"""Gemini models for use with Genkit.

# Naming convention
Gemini models follow the following naming conventions:

                             +------- Tier/Variant (e.g., pro, flash)
                             |      +---------- Modifier (Optional, e.g., exp)
                             |      |         +--- Date/Snapshot ID (Optional)
                             v      v         v
        gemini - <VER> - <TIER> [-MOD] [-DATE]
          ^        ^           ^
          |        |           |
(Family)--+        |           +-- Size Specifier (Optional, e.g., -8b,
          |        |               often follows TIER like 'flash')
          |        |
          +--------+---------- Version (Major generation, e.g., 1.0, 1.5, 2.0)


## Examples

gemini - 1.5 - flash - 8b
  ^      ^      ^      ^
  |      |      |      +-- Size Specifier
  |      |      +--------- Tier/Variant
  |      +----------------- Version
  +------------------------ Family

gemini - 2.0 - pro - exp - 02-05
  ^      ^      ^     ^      ^
  |      |      |     |      +-- Date/Snapshot ID
  |      |      |     +--------- Modifier
  |      |      +---------------- Tier/Variant
  |      +------------------------ Version
  +------------------------------- Family

## Terminology

Family (`gemini`)
: The base name identifying the overarching group or brand of related AI models
  developed by Google (e.g., Gemini).

Version Number (e.g., `1.0`, `1.5`, `2.0`, `2.5`)
: Indicates the major generation or release cycle of the model within the
  family. Higher numbers typically denote newer iterations, often incorporating
  significant improvements, architectural changes, or new capabilities compared
  to previous versions.

Tier / Variant (e.g., `pro`, `flash`)
: Distinguishes models within the same generation based on specific
  characteristics like performance profile, size, speed, efficiency, or intended
  primary use case.

  * **`pro`**: Generally indicates a high-capability, powerful, and versatile
    model within its generation, suitable for a wide range of complex tasks.

  * **`flash`**: Often signifies a model optimized for speed, latency, and
    cost-efficiency, potentially offering a different balance of performance
    characteristics compared to the `pro` variant.

Size Specifier (e.g., `8b`)
: An optional component, frequently appended to a Tier/Variant (like `flash`),
  providing more specific detail about the model's scale. This often relates to
  the approximate number of parameters (e.g., `8b` likely suggests 8 billion
  parameters), influencing its performance and resource requirements.

Modifier (e.g., `exp`)
: An optional flag indicating the model's release status, stability, or intended
  audience.

  * **`exp`**: Stands for "Experimental". Models marked with `exp` are typically
    previews or early releases. They are subject to change, updates, or removal
    without the standard notice periods applied to stable models, and they lack
    long-term stability guarantees, making them generally unsuitable for
    production systems requiring stability.

Date / Snapshot ID (e.g., `02-05`, `03-25`)
: An optional identifier, commonly seen with experimental (`exp`) models. It
  likely represents a specific build date (often in MM-DD format) or a unique
  snapshot identifier, helping to distinguish between different iterations or
  releases within the experimental track.

# Model support

The following models are currently supported by GoogleAI API:

| Model                       | Description                   | Status     |
|-----------------------------|-------------------------------|------------|
| `gemini-1.0-pro`            | Gemini 1.0 Pro                | Obsolete   |
| `gemini-1.5-pro`            | Gemini 1.5 Pro                | Deprecated |
| `gemini-1.5-flash`          | Gemini 1.5 Flash              | Deprecated |
| `gemini-1.5-flash-8b`       | Gemini 1.5 Flash 8B           | Deprecated |
| `gemini-2.0-flash`          | Gemini 2.0 Flash              | Supported  |
| `gemini-2.0-flash-lite`     | Gemini 2.0 Flash Lite         | Supported  |
| `gemini-2.0-pro-exp-02-05`  | Gemini 2.0 Pro Exp 02-05      | Supported  |
| `gemini-2.5-pro-exp-03-25`  | Gemini 2.5 Pro Exp 03-25      | Supported  |
| `gemini-2.0-flash-exp`      | Gemini 2.0 Flash Experimental | Supported  |


The following models are currently supported by VertexAI API:

| Model                       | Description                   | Status       |
|-----------------------------|-------------------------------|--------------|
| `gemini-1.0-pro`            | Gemini 1.0 Pro                | Obsolete     |
| `gemini-1.5-pro`            | Gemini 1.5 Pro                | Deprecated   |
| `gemini-1.5-flash`          | Gemini 1.5 Flash              | Deprecated   |
| `gemini-1.5-flash-8b`       | Gemini 1.5 Flash 8B           | Deprecated   |
| `gemini-2.0-flash`          | Gemini 2.0 Flash              | Supported    |
| `gemini-2.0-flash-lite`     | Gemini 2.0 Flash Lite         | Supported    |
| `gemini-2.0-pro-exp-02-05`  | Gemini 2.0 Pro Exp 02-05      | Supported    |
| `gemini-2.5-pro-exp-03-25`  | Gemini 2.5 Pro Exp 03-25      | Supported    |
| `gemini-2.0-flash-exp`      | Gemini 2.0 Flash Experimental | Unavailable  |
"""

import sys  # noqa

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

from functools import cached_property
from typing import Any

from google import genai
from google.genai import types as genai_types

from genkit.ai import (
    ActionKind,
    ActionRunContext,
    GenkitRegistry,
)
from genkit.blocks.model import get_basic_usage_stats
from genkit.codec import dump_dict, dump_json
from genkit.core.tracing import tracer
from genkit.lang.deprecations import (
    DeprecationInfo,
    DeprecationStatus,
    deprecated_enum_metafactory,
)
from genkit.plugins.google_genai.models.utils import PartConverter
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    GenerationUsage,
    Message,
    ModelInfo,
    Role,
    Stage,
    Supports,
    ToolDefinition,
)


class GeminiConfigSchema(genai_types.GenerateContentConfig):
    pass


GEMINI_1_0_PRO = ModelInfo(
    label='Google AI - Gemini Pro',
    stage=Stage.LEGACY,
    versions=['gemini-pro', 'gemini-1.0-pro-latest', 'gemini-1.0-pro-001'],
    supports=Supports(
        multiturn=True,
        media=False,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


GEMINI_1_5_PRO = ModelInfo(
    label='Google AI - Gemini 1.5 Pro',
    stage=Stage.DEPRECATED,
    versions=[
        'gemini-1.5-pro-latest',
        'gemini-1.5-pro-001',
        'gemini-1.5-pro-002',
    ],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


GEMINI_1_5_FLASH = ModelInfo(
    label='Google AI - Gemini 1.5 Flash',
    stage=Stage.DEPRECATED,
    versions=[
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash-001',
        'gemini-1.5-flash-002',
    ],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


GEMINI_1_5_FLASH_8B = ModelInfo(
    label='Google AI - Gemini 1.5 Flash',
    stage=Stage.DEPRECATED,
    versions=['gemini-1.5-flash-8b-latest', 'gemini-1.5-flash-8b-001'],
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


GEMINI_2_0_FLASH = ModelInfo(
    label='Google AI - Gemini 2.0 Flash',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


GEMINI_2_0_FLASH_LITE = ModelInfo(
    label='Google AI - Gemini 2.0 Flash Lite',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


GEMINI_2_0_PRO_EXP_02_05 = ModelInfo(
    label='Google AI - Gemini 2.0 Pro Exp 02-05',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_0_FLASH_EXP_IMAGEN = ModelInfo(
    label='Google AI - Gemini 2.0 Flash Experimental',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)

GEMINI_2_5_PRO_EXP_03_25 = ModelInfo(
    label='Google AI - Gemini 2.5 Pro Exp 03-25',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained='no-tools',
    ),
)


Deprecations = deprecated_enum_metafactory({
    'GEMINI_1_0_PRO': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
    'GEMINI_1_5_PRO': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
    'GEMINI_1_5_FLASH': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
    'GEMINI_1_5_FLASH_8B': DeprecationInfo(recommendation='GEMINI_2_0_FLASH', status=DeprecationStatus.DEPRECATED),
})


class VertexAIGeminiVersion(StrEnum, metaclass=Deprecations):
    """VertexAIGemini models.

    Model Support:

    | Model                       | Description               | Status     |
    |-----------------------------|---------------------------|------------|
    | `gemini-1.5-pro`            | Gemini 1.5 Pro            | Deprecated |
    | `gemini-1.5-flash`          | Gemini 1.5 Flash          | Deprecated |
    | `gemini-1.5-flash-8b`       | Gemini 1.5 Flash 8B       | Deprecated |
    | `gemini-2.0-flash`          | Gemini 2.0 Flash          | Supported  |
    | `gemini-2.0-flash-lite`     | Gemini 2.0 Flash Lite     | Supported  |
    | `gemini-2.0-pro-exp-02-05`  | Gemini 2.0 Pro Exp 02-05  | Supported  |
    | `gemini-2.5-pro-exp-03-25`  | Gemini 2.5 Pro Exp 03-25  | Supported  |
    """

    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
    GEMINI_2_0_FLASH = 'gemini-2.0-flash'
    GEMINI_2_0_FLASH_LITE = 'gemini-2.0-flash-lite'
    GEMINI_2_0_PRO_EXP_02_05 = 'gemini-2.0-pro-exp-02-05'
    GEMINI_2_5_PRO_EXP_03_25 = 'gemini-2.5-pro-exp-03-25'


class GoogleAIGeminiVersion(StrEnum):
    """VertexAIGemini models.

    Model Support:

    | Model                       | Description               | Status     |
    |-----------------------------|---------------------------|------------|
    | `gemini-1.5-pro`            | Gemini 1.5 Pro            | Deprecated |
    | `gemini-1.5-flash`          | Gemini 1.5 Flash          | Deprecated |
    | `gemini-1.5-flash-8b`       | Gemini 1.5 Flash 8B       | Deprecated |
    | `gemini-2.0-flash`          | Gemini 2.0 Flash          | Supported  |
    | `gemini-2.0-flash-lite`     | Gemini 2.0 Flash Lite     | Supported  |
    | `gemini-2.0-pro-exp-02-05`  | Gemini 2.0 Pro Exp 02-05  | Supported  |
    | `gemini-2.5-pro-exp-03-25`  | Gemini 2.5 Pro Exp 03-25  | Supported  |
    | `gemini-2.0-flash-exp`      | Gemini 2.0 Flash Exp      | Supported  |
    """

    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_1_5_FLASH_8B = 'gemini-1.5-flash-8b'
    GEMINI_2_0_FLASH = 'gemini-2.0-flash'
    GEMINI_2_0_FLASH_LITE = 'gemini-2.0-flash-lite'
    GEMINI_2_0_PRO_EXP_02_05 = 'gemini-2.0-pro-exp-02-05'
    GEMINI_2_5_PRO_EXP_03_25 = 'gemini-2.5-pro-exp-03-25'
    GEMINI_2_0_FLASH_EXP = 'gemini-2.0-flash-exp'


SUPPORTED_MODELS = {
    VertexAIGeminiVersion.GEMINI_1_5_PRO: GEMINI_1_5_PRO,
    VertexAIGeminiVersion.GEMINI_1_5_FLASH: GEMINI_1_5_FLASH,
    VertexAIGeminiVersion.GEMINI_1_5_FLASH_8B: GEMINI_1_5_FLASH_8B,
    VertexAIGeminiVersion.GEMINI_2_0_FLASH: GEMINI_2_0_FLASH,
    VertexAIGeminiVersion.GEMINI_2_0_FLASH_LITE: GEMINI_2_0_FLASH_LITE,
    VertexAIGeminiVersion.GEMINI_2_0_PRO_EXP_02_05: GEMINI_2_0_PRO_EXP_02_05,
    VertexAIGeminiVersion.GEMINI_2_5_PRO_EXP_03_25: GEMINI_2_5_PRO_EXP_03_25,
    GoogleAIGeminiVersion.GEMINI_1_5_PRO: GEMINI_1_5_PRO,
    GoogleAIGeminiVersion.GEMINI_1_5_FLASH: GEMINI_1_5_FLASH,
    GoogleAIGeminiVersion.GEMINI_1_5_FLASH_8B: GEMINI_1_5_FLASH_8B,
    GoogleAIGeminiVersion.GEMINI_2_0_FLASH: GEMINI_2_0_FLASH,
    GoogleAIGeminiVersion.GEMINI_2_0_FLASH_LITE: GEMINI_2_0_FLASH_LITE,
    GoogleAIGeminiVersion.GEMINI_2_0_PRO_EXP_02_05: GEMINI_2_0_PRO_EXP_02_05,
    GoogleAIGeminiVersion.GEMINI_2_5_PRO_EXP_03_25: GEMINI_2_5_PRO_EXP_03_25,
    GoogleAIGeminiVersion.GEMINI_2_0_FLASH_EXP: GEMINI_2_0_FLASH_EXP_IMAGEN,
}


class GeminiModel:
    """Gemini model."""

    def __init__(
        self,
        version: str | GoogleAIGeminiVersion | VertexAIGeminiVersion,
        client: genai.Client,
        registry: GenkitRegistry,
    ):
        """Initialize Gemini model.

        Args:
            version: Gemini version
            client: Google AI client
            registry: Genkit registry
        """
        self._version = version
        self._client = client
        self._registry = registry

    def _create_vertexai_tool(self, tool: ToolDefinition) -> genai_types.Tool:
        """Create a tool that is compatible with VertexAI API.

        Args:
            tool: Genkit Tool Definition

        Returns:
            Genai tool compatible with VertexAI API.
        """
        function = genai_types.FunctionDeclaration(
            name=tool.name,
            description=tool.description,
            parameters=tool.input_schema,
            response=tool.output_schema,
        )
        return genai_types.Tool(function_declarations=[function])

    def _create_gemini_tool(self, tool: ToolDefinition) -> genai_types.Tool:
        """Create a tool that is compatible with Gemini API.

        Args:
            tool: Genkit Tool Definition

        Returns:
            Genai tool compatible with Gemini API.
        """
        params = self._convert_schema_property(tool.input_schema)
        function = genai_types.FunctionDeclaration(name=tool.name, description=tool.description, parameters=params)
        return genai_types.Tool(function_declarations=[function])

    def _get_tools(self, request: GenerateRequest) -> list[genai_types.Tool]:
        """Generates VertexAI Gemini compatible tool definitions.

        Args:
            request: The generation request.

        Returns:
             list of Gemini tools
        """
        tools = []
        for tool in request.tools:
            genai_tool = self._create_vertexai_tool(tool) if self._client.vertexai else self._create_gemini_tool(tool)
            tools.append(genai_tool)

        return tools

    def _convert_schema_property(
        self, input_schema: dict[str, Any], defs: dict[str, Any] | None = None
    ) -> genai_types.Schema | None:
        """Sanitizes a schema to be compatible with Gemini API.

        Args:
            input_schema: a dictionary with input parameters

        Returns:
            Schema or None
        """
        if not defs:
            defs = input_schema.get('$defs') if '$defs' in input_schema else {}

        if not input_schema or 'type' not in input_schema:
            return None

        schema = genai_types.Schema()
        if input_schema.get('description'):
            schema.description = input_schema['description']

        if 'required' in input_schema:
            schema.required = input_schema['required']

        if 'type' in input_schema:
            schema_type = genai_types.Type(input_schema['type'])
            schema.type = schema_type

            if 'enum' in input_schema:
                schema.enum = input_schema['enum']

            if schema_type == genai_types.Type.ARRAY:
                schema.items = self._convert_schema_property(input_schema['items'], defs)

            if schema_type == genai_types.Type.OBJECT:
                schema.properties = {}
                properties = input_schema['properties']
                for key in properties:
                    if isinstance(properties[key], dict) and '$ref' in properties[key]:
                        ref_tokens = properties[key]['$ref'].split('/')
                        if ref_tokens[2] not in defs:
                            raise Exception(f'Failed to resolve schema for {ref_tokens[2]}')
                        resolved_schema = self._convert_schema_property(defs[ref_tokens[2]], defs)
                        schema.properties[key] = resolved_schema

                        if 'description' in properties[key]:
                            schema.properties[key].description = properties[key]['description']
                    else:
                        nested_schema = self._convert_schema_property(properties[key], defs)
                        schema.properties[key] = nested_schema

        return schema

    def _call_tool(self, call: genai_types.FunctionCall) -> genai_types.Content:
        """Calls tool's function from the registry.

        Args:
            call: FunctionCall from Gemini response

        Returns:
            Gemini message content to add to the message
        """
        tool_function = self._registry.registry.lookup_action(ActionKind.TOOL, call.name)
        args = tool_function.input_type.validate_python(call.args)
        tool_answer = tool_function.run(args)
        return genai_types.Content(
            parts=[
                genai_types.Part.from_function_response(
                    name=call.name,
                    response={
                        'content': tool_answer.response,
                    },
                )
            ]
        )

    async def generate(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Handle a generation request.

        Args:
            request: The generation request containing messages and parameters.
            ctx: action context

        Returns:
            The model's response to the generation request.
        """
        request_cfg = self._genkit_to_googleai_cfg(request)
        request_contents = self._build_messages(request)

        if ctx.is_streaming:
            response = await self._streaming_generate(request_contents, request_cfg, ctx)
        else:
            response = await self._generate(request_contents, request_cfg)

        response.usage = self._create_usage_stats(request=request, response=response)

        return response

    async def _generate(
        self,
        request_contents: list[genai_types.Content],
        request_cfg: genai_types.GenerateContentConfig,
    ) -> GenerateResponse:
        """Call google-genai generate.

        Args:
            request_contents: request contents
            request_cfg: request configuration

        Returns:
            genai response.
        """
        with tracer.start_as_current_span('generate_content') as span:
            span.set_attribute(
                'genkit:input',
                dump_json(
                    {
                        'config': dump_dict(request_cfg),
                        'contents': [dump_dict(c) for c in request_contents],
                        'model': self._version,
                    },
                    fallback=lambda _: '[!! failed to serialize !!]',
                ),
            )
            response = await self._client.aio.models.generate_content(
                model=self._version, contents=request_contents, config=request_cfg
            )
            span.set_attribute('genkit:output', dump_json(response))

        content = self._contents_from_response(response)

        return GenerateResponse(
            message=Message(
                content=content,
                role=Role.MODEL,
            )
        )

    async def _streaming_generate(
        self,
        request_contents: list[genai_types.Content],
        request_cfg: genai_types.GenerateContentConfig | None,
        ctx: ActionRunContext,
    ) -> GenerateResponse:
        """Call google-genai generate for streaming.

        Args:
            request_contents: request contents
            request_cfg: request configuration
            ctx: action context

        Returns:
            empty genai response
        """
        with tracer.start_as_current_span('generate_content_stream') as span:
            span.set_attribute(
                'genkit:input',
                dump_json({
                    'config': dump_dict(request_cfg),
                    'contents': [dump_dict(c) for c in request_contents],
                    'model': self._version,
                }),
            )
            generator = self._client.aio.models.generate_content_stream(
                model=self._version, contents=request_contents, config=request_cfg
            )
        accumulated_content = []
        async for response_chunk in await generator:
            content = self._contents_from_response(response_chunk)
            accumulated_content.append(*content)
            ctx.send_chunk(
                chunk=GenerateResponseChunk(
                    content=content,
                    role=Role.MODEL,
                )
            )

        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=accumulated_content,
            )
        )

    @cached_property
    def metadata(self) -> dict:
        """Get model metadata.

        Returns:
            model metadata.
        """
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }

    def is_multimode(self):
        """Check if the model supports media.

        Returns:
            True if the model supports media, False otherwise.
        """
        return SUPPORTED_MODELS[self._version].supports.media

    def _build_messages(self, request: GenerateRequest) -> list[genai_types.Content]:
        """Build google-genai request contents from Genkit request.

        Args:
            request: Genkit request.

        Returns:
            list of google-genai contents.
        """
        request_contents: list[genai_types.Content] = []

        for msg in request.messages:
            content_parts: list[genai_types.Part] = []
            for p in msg.content:
                content_parts.append(PartConverter.to_gemini(p))
            request_contents.append(genai_types.Content(parts=content_parts, role=msg.role))

        return request_contents

    def _contents_from_response(self, response: genai_types.GenerateContentResponse) -> list:
        """Retrieve contents from google-genai response.

        Args:
            response: google-genai response.

        Returns:
            list of generated contents.
        """
        content = []
        if response.candidates:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    content.append(PartConverter.from_gemini(part=part))

        return content

    def _genkit_to_googleai_cfg(self, request: GenerateRequest) -> genai_types.GenerateContentConfig | None:
        """Translate GenerationCommonConfig to Google Ai GenerateContentConfig.

        Args:
            request: Genkit request.

        Returns:
            Google Ai request config or None.
        """
        cfg = None

        if request.config:
            request_config = request.config
            if isinstance(request_config, GenerationCommonConfig):
                cfg = genai_types.GenerateContentConfig(
                    max_output_tokens=request_config.max_output_tokens,
                    top_k=request_config.top_k,
                    top_p=request_config.top_p,
                    temperature=request_config.temperature,
                    stop_sequences=request_config.stop_sequences,
                )
            elif isinstance(request_config, GeminiConfigSchema):
                cfg = request_config
            elif isinstance(request_config, dict):
                cfg = genai_types.GenerateContentConfig(**request_config)

        if request.output:
            if not cfg:
                cfg = genai_types.GenerateContentConfig()

            response_mime_type = 'application/json' if request.output.format == 'json' and not request.tools else None
            cfg.response_mime_type = response_mime_type

            if request.output.schema_ and request.output.constrained:
                cfg.response_schema = self._convert_schema_property(request.output.schema_)

        if request.tools:
            if not cfg:
                cfg = genai_types.GenerateContentConfig()

            tools = self._get_tools(request)
            cfg.tools = tools

        system_messages = list(filter(lambda m: m.role == Role.SYSTEM, request.messages))
        if system_messages:
            system_parts = []
            if not cfg:
                cfg = genai.types.GenerateContentConfig()

            for msg in system_messages:
                for p in msg.content:
                    system_parts.append(PartConverter.to_gemini(p))
                request.messages.remove(msg)
            cfg.system_instruction = genai.types.Content(parts=system_parts)

        return cfg

    def _create_usage_stats(self, request: GenerateRequest, response: GenerateResponse) -> GenerationUsage:
        """Create usage statistics.

        Args:
            request: Genkit request
            response: Genkit response

        Returns:
            usage statistics
        """
        usage = get_basic_usage_stats(input_=request.messages, response=response.message)
        if response.usage:
            usage.input_tokens = response.usage.input_tokens
            usage.output_tokens = response.usage.output_tokens
            usage.total_tokens = response.usage.total_tokens

        return usage
