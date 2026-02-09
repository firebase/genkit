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

"""AWS Bedrock format conversion utilities.

Pure-function helpers for converting between Genkit types and AWS Bedrock
Converse API formats. Extracted from the model module for independent
unit testing.

See:
    - Converse API: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
    - Boto3 Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html
"""

import base64
import json
from typing import Any

from genkit.plugins.amazon_bedrock.typing import BedrockConfig
from genkit.types import (
    FinishReason,
    GenerateRequest,
    GenerationCommonConfig,
    GenerationUsage,
    Media,
    Message,
    Part,
    Role,
    TextPart,
    ToolDefinition,
    ToolRequest,
    ToolRequestPart,
    ToolResponsePart,
)

__all__ = [
    'FINISH_REASON_MAP',
    'INFERENCE_PROFILE_PREFIXES',
    'INFERENCE_PROFILE_SUPPORTED_PROVIDERS',
    'build_json_instruction',
    'build_media_block',
    'build_usage',
    'convert_media_data_uri',
    'from_bedrock_content',
    'get_effective_model_id',
    'is_image_media',
    'map_finish_reason',
    'normalize_config',
    'parse_tool_call_args',
    'separate_system_messages',
    'to_bedrock_content',
    'to_bedrock_role',
    'to_bedrock_tool',
]

# Mapping from Bedrock stop reasons to Genkit finish reasons.
#
# See: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseOutput.html
FINISH_REASON_MAP: dict[str, FinishReason] = {
    'end_turn': FinishReason.STOP,
    'stop_sequence': FinishReason.STOP,
    'max_tokens': FinishReason.LENGTH,
    'tool_use': FinishReason.STOP,
    'content_filtered': FinishReason.BLOCKED,
    'guardrail_intervened': FinishReason.BLOCKED,
}

# Inference profile prefixes that indicate an ID already has a regional prefix.
INFERENCE_PROFILE_PREFIXES = ('us.', 'eu.', 'apac.')

# Model provider prefixes that support cross-region inference profiles.
# Only these providers can use inference profile IDs with regional prefixes.
INFERENCE_PROFILE_SUPPORTED_PROVIDERS = (
    'anthropic.',
    'amazon.',
    'meta.',
    'mistral.',
    'cohere.',
    'deepseek.',
)


def map_finish_reason(stop_reason: str) -> FinishReason:
    """Map a Bedrock stop reason string to a Genkit FinishReason.

    Args:
        stop_reason: The stop reason from the Bedrock API response.

    Returns:
        The corresponding Genkit FinishReason, or UNKNOWN if unmapped.
    """
    return FINISH_REASON_MAP.get(stop_reason, FinishReason.UNKNOWN)


def to_bedrock_role(role: Role | str) -> str:
    """Convert a Genkit role to a Bedrock role string.

    The Bedrock Converse API only supports 'user' and 'assistant' roles.
    Tool responses are sent as 'user' messages.

    Args:
        role: Genkit Role enum or string.

    Returns:
        Bedrock role string ('user' or 'assistant').
    """
    if isinstance(role, str):
        str_role_map = {
            'user': 'user',
            'model': 'assistant',
            'assistant': 'assistant',
            'tool': 'user',
        }
        return str_role_map.get(role.lower(), 'user')

    role_map = {
        Role.USER: 'user',
        Role.MODEL: 'assistant',
        Role.TOOL: 'user',
    }
    return role_map.get(role, 'user')


def separate_system_messages(
    messages: list[Message],
) -> tuple[list[str], list[Message]]:
    """Separate system messages from conversation messages.

    The Bedrock Converse API requires system messages to be passed
    separately from conversation messages.

    Args:
        messages: List of Genkit messages.

    Returns:
        Tuple of (system_texts, conversation_messages).
    """
    system_texts: list[str] = []
    conversation_messages: list[Message] = []

    for msg in messages:
        if msg.role == Role.SYSTEM or (isinstance(msg.role, str) and msg.role.lower() == 'system'):
            text_parts: list[str] = []
            for part in msg.content:
                root = part.root if isinstance(part, Part) else part
                if isinstance(root, TextPart):
                    text_parts.append(root.text)
            if text_parts:
                system_texts.append(''.join(text_parts))
        else:
            conversation_messages.append(msg)

    return system_texts, conversation_messages


def to_bedrock_tool(tool: ToolDefinition) -> dict[str, Any]:
    """Convert a Genkit tool definition to Bedrock format.

    Args:
        tool: Genkit ToolDefinition.

    Returns:
        Bedrock-compatible tool specification.
    """
    input_schema = tool.input_schema or {'type': 'object', 'properties': {}}

    return {
        'toolSpec': {
            'name': tool.name,
            'description': tool.description or '',
            'inputSchema': {
                'json': input_schema,
            },
        },
    }


def to_bedrock_content(part: Part) -> dict[str, Any] | None:
    """Convert a single Genkit Part to a Bedrock content block.

    Handles TextPart, ToolRequestPart, and ToolResponsePart.
    MediaPart requires async URL fetching so is handled separately
    in the model class.

    Args:
        part: A Genkit Part.

    Returns:
        Bedrock content block dict, or None if the part type needs
        special handling (e.g. MediaPart).
    """
    root = part.root if isinstance(part, Part) else part

    if isinstance(root, TextPart):
        return {'text': root.text}

    if isinstance(root, ToolRequestPart):
        tool_req = root.tool_request
        return {
            'toolUse': {
                'toolUseId': tool_req.ref or '',
                'name': tool_req.name,
                'input': tool_req.input if isinstance(tool_req.input, dict) else {},
            },
        }

    if isinstance(root, ToolResponsePart):
        tool_resp = root.tool_response
        output = tool_resp.output
        result_content = [{'text': output}] if isinstance(output, str) else [{'json': output}]
        return {
            'toolResult': {
                'toolUseId': tool_resp.ref or '',
                'content': result_content,
            },
        }

    return None


def from_bedrock_content(content_blocks: list[dict[str, Any]]) -> list[Part]:
    """Convert Bedrock response content blocks to Genkit parts.

    Handles text, toolUse, and reasoningContent blocks.

    Args:
        content_blocks: List of Bedrock content blocks from the API response.

    Returns:
        List of Genkit Part objects.
    """
    parts: list[Part] = []

    for block in content_blocks:
        if 'text' in block:
            parts.append(Part(root=TextPart(text=block['text'])))

        if 'toolUse' in block:
            tool_use = block['toolUse']
            parts.append(
                Part(
                    root=ToolRequestPart(
                        tool_request=ToolRequest(
                            ref=tool_use.get('toolUseId', ''),
                            name=tool_use.get('name', ''),
                            input=tool_use.get('input', {}),
                        )
                    )
                )
            )

        if 'reasoningContent' in block:
            reasoning = block['reasoningContent']
            if 'reasoningText' in reasoning:
                reasoning_text = reasoning['reasoningText']
                if isinstance(reasoning_text, dict) and 'text' in reasoning_text:
                    parts.append(Part(root=TextPart(text=f'[Reasoning]\n{reasoning_text["text"]}\n[/Reasoning]\n')))
                elif isinstance(reasoning_text, str):
                    parts.append(Part(root=TextPart(text=f'[Reasoning]\n{reasoning_text}\n[/Reasoning]\n')))

    return parts


def parse_tool_call_args(args_str: str) -> dict[str, Any] | str:
    """Parse tool call arguments from a JSON string.

    Gracefully handles invalid JSON by returning the raw string.

    Args:
        args_str: JSON string of tool call arguments.

    Returns:
        Parsed dict if valid JSON, otherwise the raw string.
    """
    if not args_str:
        return {}
    try:
        return json.loads(args_str)
    except (json.JSONDecodeError, TypeError):
        return args_str


def build_usage(usage_data: dict[str, Any]) -> GenerationUsage:
    """Build GenerationUsage from Bedrock usage data.

    Args:
        usage_data: Usage dict from the Bedrock API response.

    Returns:
        GenerationUsage with token counts.
    """
    return GenerationUsage(
        input_tokens=usage_data.get('inputTokens', 0),
        output_tokens=usage_data.get('outputTokens', 0),
        total_tokens=usage_data.get('totalTokens', 0),
    )


def normalize_config(config: object) -> BedrockConfig:
    """Normalize config to BedrockConfig.

    Handles dicts with camelCase keys, GenerationCommonConfig, and
    BedrockConfig passthrough.

    Args:
        config: Request configuration (dict, BedrockConfig, or GenerationCommonConfig).

    Returns:
        Normalized BedrockConfig instance.
    """
    if config is None:
        return BedrockConfig()

    if isinstance(config, BedrockConfig):
        return config

    if isinstance(config, GenerationCommonConfig):
        max_tokens = int(config.max_output_tokens) if config.max_output_tokens is not None else None
        return BedrockConfig(
            temperature=config.temperature,
            max_tokens=max_tokens,
            top_p=config.top_p,
            stop_sequences=config.stop_sequences,
        )

    if isinstance(config, dict):
        mapped: dict[str, Any] = {}
        key_map: dict[str, str] = {
            'maxOutputTokens': 'max_tokens',
            'maxTokens': 'max_tokens',
            'topP': 'top_p',
            'topK': 'top_k',
            'stopSequences': 'stop_sequences',
        }
        for key, value in config.items():
            str_key = str(key)
            mapped_key = key_map.get(str_key, str_key)
            mapped[mapped_key] = value
        return BedrockConfig(**mapped)

    return BedrockConfig()


def build_json_instruction(request: GenerateRequest) -> str | None:
    """Build a JSON output instruction for the system prompt.

    The Bedrock Converse API doesn't have native JSON mode. Instead,
    we inject instructions into the system prompt to guide the model.

    Args:
        request: The generation request.

    Returns:
        JSON instruction string if JSON output is requested, None otherwise.
    """
    if not request.output:
        return None

    if request.output.format != 'json':
        return None

    instruction_parts = [
        'IMPORTANT: You MUST respond with valid JSON only.',
        'Do not include any text before or after the JSON.',
        'Do not wrap the JSON in markdown code blocks.',
    ]

    if request.output.schema:
        schema_str = json.dumps(request.output.schema, indent=2)
        instruction_parts.append(f'Your response MUST conform to this JSON schema:\n{schema_str}')

    return '\n'.join(instruction_parts)


def convert_media_data_uri(media: Media) -> tuple[bytes, str, bool]:
    """Convert a data URI media to raw bytes and format.

    Only handles data: URIs. For HTTP URLs, returns empty values
    and is_data_uri=False, signaling that async fetching is needed.

    Args:
        media: Genkit Media object.

    Returns:
        Tuple of (media_bytes, format_str, is_data_uri).
    """
    url = media.url
    content_type = media.content_type or ''

    if not url.startswith('data:'):
        return b'', '', False

    format_str = _format_from_content_type(content_type, url)

    parts = url.split(',', 1)
    if len(parts) == 2:
        media_bytes = base64.b64decode(parts[1])
        return media_bytes, format_str, True

    return b'', format_str, False


def is_image_media(content_type: str, url: str) -> bool:
    """Determine if media is an image (vs video).

    Args:
        content_type: MIME type.
        url: Media URL.

    Returns:
        True if the media is an image.
    """
    if content_type.startswith('image/'):
        return True
    if content_type.startswith('video/'):
        return False
    return any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])


def build_media_block(media_bytes: bytes, format_str: str, is_image: bool) -> dict[str, Any]:
    """Build a Bedrock media content block from raw bytes.

    Args:
        media_bytes: The raw media bytes.
        format_str: Format string (e.g., 'jpeg', 'png', 'mp4').
        is_image: True for image, False for video.

    Returns:
        Bedrock-compatible media content block.
    """
    media_type = 'image' if is_image else 'video'
    return {
        media_type: {
            'format': format_str,
            'source': {'bytes': media_bytes},
        },
    }


def get_effective_model_id(
    model_id: str,
    *,
    bearer_token: str | None = None,
    aws_region: str | None = None,
) -> str:
    """Get the effective model ID, adding inference profile prefix if needed.

    When using API key authentication (bearer token), AWS Bedrock requires
    inference profile IDs with regional prefixes (us., eu., apac.) instead
    of direct model IDs for supported providers.

    Args:
        model_id: The base model ID.
        bearer_token: AWS bearer token for API key auth (from env).
        aws_region: AWS region string (from env).

    Returns:
        The model ID to use for the API call.
    """
    if model_id.startswith(INFERENCE_PROFILE_PREFIXES):
        return model_id

    if not bearer_token:
        return model_id

    if not model_id.startswith(INFERENCE_PROFILE_SUPPORTED_PROVIDERS):
        return model_id

    if not aws_region:
        return model_id

    region_lower = aws_region.lower()
    if region_lower.startswith(('us-', 'us_')):
        prefix = 'us'
    elif region_lower.startswith(('eu-', 'eu_')):
        prefix = 'eu'
    elif region_lower.startswith(('ap-', 'ap_', 'cn-', 'cn_', 'me-', 'me_', 'af-', 'af_', 'sa-', 'sa_')):
        prefix = 'apac'
    else:
        prefix = 'us'

    return f'{prefix}.{model_id}'


def _format_from_content_type(content_type: str, url: str) -> str:
    """Extract media format string from content type or URL.

    Args:
        content_type: MIME type (e.g., 'image/png').
        url: Media URL as fallback for format detection.

    Returns:
        Format string (e.g., 'jpeg', 'png', 'mp4').
    """
    if content_type:
        return content_type.split('/')[-1]

    for ext in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'mp4', 'webm', 'mov']:
        if f'.{ext}' in url.lower():
            return ext if ext != 'jpg' else 'jpeg'

    return 'jpeg'
