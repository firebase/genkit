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

"""Gemini models."""

import asyncio
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from functools import cached_property
from typing import Annotated, Any, Any as JsonAny, Literal, TypeAlias, cast, get_args

from genkit_google_genai._auth import GOOGLE_AUTH_ERRORS, raise_auth_error
from genkit_google_genai._constants import is_multi_regional_location, multi_regional_base_url
from genkit_google_genai._models._context_caching._constants import DEFAULT_TTL
from genkit_google_genai._models._context_caching._utils import generate_cache_key, validate_context_cache_request
from genkit_google_genai._models._sdk_config import (
    GEMINI_MANAGED_BODY_FIELDS,
    GEMINI_MANAGED_GENERATION_FIELDS,
    attach_config_extra,
    attach_leftovers,
    dump_family_config,
    keep_client_extra_body,
    sdk_config_error,
    split_sdk_fields,
)
from genkit_google_genai._models._secrets import context_api_key, reject_request_config_api_key
from genkit_google_genai._provider_errors import TRANSPORT_ERRORS, api_error, transport_error
from google import genai
from google.auth import default as google_auth_default
from google.auth.exceptions import DefaultCredentialsError
from google.genai import types as genai_types
from google.genai.errors import APIError
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    WithJsonSchema,
    field_validator,
    model_validator,
    with_config,
)
from pydantic.alias_generators import to_camel, to_snake
from typing_extensions import NotRequired, Self, TypedDict

from genkit import (
    ActionRunContext,
    FinishReason,
    GenkitError,
    Message,
    ModelResponse,
    ModelResponseChunk,
    Part,
    Role,
    RuntimeErrorReason,
)
from genkit.model import (
    Candidate,
    Constrained,
    ModelConfig,
    ModelInfo,
    ModelRequest,
    ModelUsage,
    Supports,
    ToolDefinition,
    get_basic_usage_stats,
)


def _to_dict(obj: JsonAny) -> JsonAny:  # noqa: ANN401
    """Convert object to dict if it's a Pydantic model, otherwise return as-is."""
    return obj.model_dump() if isinstance(obj, BaseModel) else obj


def _to_finish_reason(fr: Any) -> FinishReason:  # noqa: ANN401
    """Map a google-genai finish reason onto Genkit's FinishReason."""
    fr_name = getattr(fr, 'name', fr) if fr is not None else None
    if fr_name == 'STOP':
        return FinishReason.STOP
    if fr_name == 'MAX_TOKENS':
        return FinishReason.LENGTH
    if fr_name in (
        'SAFETY',
        'RECITATION',
        'BLOCKLIST',
        'PROHIBITED_CONTENT',
        'SPII',
        'LANGUAGE',
        'MALICIOUS',
        'IMAGE_SAFETY',
        'IMAGE_PROHIBITED_CONTENT',
        'IMAGE_RECITATION',
    ):
        return FinishReason.BLOCKED
    if fr_name in (
        'OTHER',
        'MALFORMED_FUNCTION_CALL',
        'MISSING_THOUGHT_SIGNATURE',
        'NO_IMAGE',
        'IMAGE_OTHER',
        'UNEXPECTED_TOOL_CALL',
    ):
        return FinishReason.OTHER
    return FinishReason.UNKNOWN


def _to_float(obj: Any, attr: str) -> float | None:  # noqa: ANN401
    """Extract an optional numeric attribute as a float."""
    val = getattr(obj, attr, None)
    return float(val) if val is not None else None


def _usage_from_metadata(usage_metadata: Any) -> ModelUsage:  # noqa: ANN401
    """Build ModelUsage from a google-genai usage_metadata block."""
    if usage_metadata is None:
        return ModelUsage()

    return ModelUsage(
        input_tokens=_to_float(usage_metadata, 'prompt_token_count'),
        output_tokens=_to_float(usage_metadata, 'candidates_token_count'),
        total_tokens=_to_float(usage_metadata, 'total_token_count'),
        thoughts_tokens=_to_float(usage_metadata, 'thoughts_token_count'),
        cached_content_tokens=_to_float(usage_metadata, 'cached_content_token_count'),
    )


from genkit_google_genai._models._utils import (  # noqa: E402
    TOOL_INPUT_FIELD,
    PartConverter,
    ToolTable,
    ToolWire,
)

# Input-only choice sets, exported for annotating caller code. Literals rather
# than enums so callers pass plain strings (thinking_level='HIGH') without
# importing anything, and type checkers still reject a value outside the set.
# The Dev UI schemas below read the same sets with get_args. Model names are
# never exported this way: model lists change.
#
# googlegenai_gemini_test.py pins each set that has a google-genai enum, so an
# SDK bump that adds a value fails until it is added here. The SDK's
# *_UNSPECIFIED placeholders are listed only where Genkit already offered
# them (HarmCategory, HarmBlockMethod, ProminentPeople, PhishBlockThreshold).
HarmCategory: TypeAlias = Literal[
    'HARM_CATEGORY_UNSPECIFIED',
    'HARM_CATEGORY_HATE_SPEECH',
    'HARM_CATEGORY_SEXUALLY_EXPLICIT',
    'HARM_CATEGORY_HARASSMENT',
    'HARM_CATEGORY_DANGEROUS_CONTENT',
    'HARM_CATEGORY_CIVIC_INTEGRITY',
    'HARM_CATEGORY_JAILBREAK',
    'HARM_CATEGORY_IMAGE_HATE',
    'HARM_CATEGORY_IMAGE_DANGEROUS_CONTENT',
    'HARM_CATEGORY_IMAGE_HARASSMENT',
    'HARM_CATEGORY_IMAGE_SEXUALLY_EXPLICIT',
]
HarmBlockThreshold: TypeAlias = Literal[
    'BLOCK_LOW_AND_ABOVE', 'BLOCK_MEDIUM_AND_ABOVE', 'BLOCK_ONLY_HIGH', 'BLOCK_NONE', 'OFF'
]
HarmBlockMethod: TypeAlias = Literal['HARM_BLOCK_METHOD_UNSPECIFIED', 'SEVERITY', 'PROBABILITY']
ThinkingLevel: TypeAlias = Literal['MINIMAL', 'LOW', 'MEDIUM', 'HIGH']
# genai_types.ImageConfig types aspect_ratio and image_size as str. These
# follow the Gemini image generation docs, union across image models:
# https://ai.google.dev/gemini-api/docs/image-generation#aspect_ratios_and_image_size
ImageAspectRatio: TypeAlias = Literal[
    '1:1', '1:4', '1:8', '2:3', '3:2', '3:4', '4:1', '4:3', '4:5', '5:4', '8:1', '9:16', '16:9', '21:9'
]
ImageSize: TypeAlias = Literal['1K', '2K', '4K']
ProminentPeople: TypeAlias = Literal['PROMINENT_PEOPLE_UNSPECIFIED', 'ALLOW_PROMINENT_PEOPLE', 'BLOCK_PROMINENT_PEOPLE']
PhishBlockThreshold: TypeAlias = Literal[
    'PHISH_BLOCK_THRESHOLD_UNSPECIFIED',
    'BLOCK_LOW_AND_ABOVE',
    'BLOCK_MEDIUM_AND_ABOVE',
    'BLOCK_HIGH_AND_ABOVE',
    'BLOCK_HIGHER_AND_ABOVE',
    'BLOCK_VERY_HIGH_AND_ABOVE',
    'BLOCK_ONLY_EXTREMELY_HIGH',
]
# No google-genai enum: ImageConfig.person_generation is a str documented with these values.
PersonGeneration: TypeAlias = Literal['ALLOW_ALL', 'ALLOW_ADULT', 'ALLOW_NONE']
ResponseModality: TypeAlias = Literal['TEXT', 'IMAGE', 'AUDIO']
SearchType: TypeAlias = Literal['web', 'image']


@with_config(ConfigDict(extra='forbid'))
class SafetySetting(TypedDict):
    """One ``safety_settings`` entry. Sent as ``genai_types.SafetySetting``.

    A TypedDict so a dict literal type-checks without importing it.
    """

    category: HarmCategory
    threshold: HarmBlockThreshold
    method: NotRequired[HarmBlockMethod]


def _literal_list_schema(choices: tuple[str, ...], description: str) -> WithJsonSchema:
    """Top-level ``{type: array, items: {enum}}`` so the Dev UI renders a multi-select.

    The Dev UI reads array item enums only off the outer object, so the
    ``anyOf[array, null]`` pydantic emits for ``list[Literal] | None``
    renders as free text.
    """
    return WithJsonSchema({
        'type': 'array',
        'items': {'type': 'string', 'enum': list(choices)},
        'description': description,
    })


# Flat fields grouped by the nested request object the plugin builds from them.
_THINKING_FIELDS = ('include_thoughts', 'thinking_budget', 'thinking_level')
_IMAGE_FIELDS = (
    'aspect_ratio',
    'image_size',
    'output_mime_type',
    'output_compression_quality',
    'person_generation',
    'prominent_people',
)
_GOOGLE_SEARCH_OPTIONS = (
    'google_search_types',
    'google_search_exclude_domains',
    'google_search_blocking_confidence',
    'google_search_start_time',
    'google_search_end_time',
)

# Nested keys the flat fields replaced, and what to pass instead. The error
# repeats the caller's casing, so a .prompt file gets camelCase names.
_FLATTENED_KEYS: dict[str, tuple[str, ...]] = {
    'thinking_config': _THINKING_FIELDS,
    'image_config': _IMAGE_FIELDS,
    'speech_config': ('voice', 'speakers', 'language_code'),
    'file_search': ('file_search_store_names', 'file_search_metadata_filter', 'file_search_top_k'),
    'google_search_retrieval': ('google_search',),
}
_TOOL_CHOICE_KEYS = frozenset({'function_calling_config', 'tool_config'})

# Settings the Gemini API rejects (google-genai raises before sending). The
# plugin raises first so the error names the flat field.
_VERTEX_ONLY_FIELDS = (
    'output_mime_type',
    'output_compression_quality',
    'person_generation',
    'prominent_people',
    'google_search_exclude_domains',
    'google_search_blocking_confidence',
)


# Genkit's generate(tool_choice=) and the Gemini function calling mode it sends.
_FUNCTION_CALLING_MODES: dict[str, genai_types.FunctionCallingConfigMode] = {
    'auto': genai_types.FunctionCallingConfigMode.AUTO,
    'required': genai_types.FunctionCallingConfigMode.ANY,
    'none': genai_types.FunctionCallingConfigMode.NONE,
}


def _tool_config(tool_choice: str, function_tools: list[genai_types.Tool]) -> genai_types.ToolConfig:
    """The toolConfig for a request's tool_choice. Function calling has no config fields.

    'required' also names the request's tools as the allowed functions, as Go
    does; Gemini only reads allowed_function_names in ANY mode.
    """
    calling = genai_types.FunctionCallingConfig(mode=_FUNCTION_CALLING_MODES[tool_choice])
    if tool_choice == 'required':
        calling.allowed_function_names = [
            declaration.name
            for tool in function_tools
            for declaration in tool.function_declarations or []
            if declaration.name
        ]
    return genai_types.ToolConfig(function_calling_config=calling)


def _pop_prefixed(config: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Pop every ``<prefix>name`` key from *config*, returned as ``{name: value}``."""
    return {key[len(prefix) :]: config.pop(key) for key in [k for k in config if k.startswith(prefix)]}


def _flattened_key_error(key: str, value: object) -> GenkitError | None:
    """The error for a nested key the flat fields replaced, or None if *key* isn't one."""
    snake = to_snake(key)
    camel = snake != key

    def names(fields: tuple[str, ...]) -> str:
        return ' / '.join(to_camel(f) if camel else f for f in fields)

    if snake in _TOOL_CHOICE_KEYS:
        message = f"{key} is not a config field; pass ai.generate(tool_choice='auto' | 'required' | 'none')"
    elif snake in _FLATTENED_KEYS:
        message = f'{key} was flattened; use {names(_FLATTENED_KEYS[snake])}'
    elif snake == 'google_search' and isinstance(value, Mapping):
        message = f'{key} takes True or False; set options with {names(_GOOGLE_SEARCH_OPTIONS)}'
    elif snake in ('code_execution', 'url_context') and isinstance(value, Mapping):
        message = f'{key} takes True or False'
    else:
        return None
    return GenkitError(status='INVALID_ARGUMENT', message=message, reason=RuntimeErrorReason.INVALID_INPUT)


def _both_set_error(first: str, second: str) -> ValueError:
    return ValueError(f'{first} and {second} are both set; pass {first}=None or {second}=None to clear a default')


class GeminiConfig(ModelConfig):
    """Gemini Config.

    Every setting is a flat field; the plugin builds the nested
    ``GenerateContentConfig`` from them at request time. Unknown keys raise.
    A request field this class doesn't declare goes in ``extra`` under its
    wire name and is merged into the request body.
    """

    # GenkitConfig's flags (to_camel, both spellings, extra='forbid') are
    # inherited; don't pass alias= on fields or type checkers stop accepting
    # the snake_case kwarg.

    base_url: str | None = Field(
        default=None, description='Overrides the plugin-configured or default baseUrl, if specified.'
    )
    api_version: str | None = Field(
        default=None, description='Overrides the plugin-configured or default apiVersion, if specified.'
    )
    location: str | None = Field(
        default=None,
        description=(
            'Overrides the plugin-configured location/region for this request '
            "(Vertex AI only). Accepts regions (e.g. 'us-central1'), "
            "multi-regions ('us', 'eu'), or 'global'."
        ),
    )

    safety_settings: Annotated[
        list[SafetySetting] | None,
        WithJsonSchema({
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'category': {'type': 'string', 'enum': list(get_args(HarmCategory))},
                    'threshold': {'type': 'string', 'enum': list(get_args(HarmBlockThreshold))},
                    'method': {'type': 'string', 'enum': list(get_args(HarmBlockMethod))},
                },
                'required': ['category', 'threshold'],
                'additionalProperties': False,
            },
            'description': (
                'Adjust how likely you are to see responses that could be harmful. '
                'Content is blocked based on the probability that it is harmful.'
            ),
        }),
    ] = Field(
        default=None,
    )

    code_execution: bool | None = Field(
        default=None,
        description='Enables the model to generate and run code.',
    )

    context_cache: bool | None = Field(
        default=None,
        description=(
            'Context caching allows you to save and reuse precomputed input tokens that you wish to use repeatedly.'
        ),
    )

    response_modalities: Annotated[
        list[ResponseModality] | None,
        _literal_list_schema(get_args(ResponseModality), 'The modalities to be used in the response.'),
    ] = Field(default=None)

    google_search: bool | None = Field(
        default=None,
        description=(
            'Ground the response in public web data with the Google Search tool. '
            'Left unset, any google_search_* option turns it on. False with options set raises.'
        ),
    )
    google_search_types: Annotated[
        list[SearchType] | None,
        _literal_list_schema(get_args(SearchType), 'Search types to enable. Web search when unset.'),
    ] = Field(default=None)
    google_search_exclude_domains: list[str] | None = Field(
        default=None, description='Domains to exclude from results, e.g. ["amazon.com"]. Vertex AI only.'
    )
    google_search_blocking_confidence: PhishBlockThreshold | None = Field(
        default=None, description='Block results at or above this phishing confidence. Vertex AI only.'
    )
    google_search_start_time: datetime | None = Field(
        default=None,
        description='Only return results from this time on (inclusive). Set with google_search_end_time.',
    )
    google_search_end_time: datetime | None = Field(
        default=None,
        description='Only return results before this time (exclusive). Set with google_search_start_time.',
    )

    file_search_store_names: list[str] | None = Field(
        default=None,
        description=(
            'The fileSearchStores to retrieve from; setting it attaches the File Search tool. '
            'Example: fileSearchStores/my-file-search-store-123'
        ),
    )
    file_search_metadata_filter: str | None = Field(
        default=None, description='Metadata filter to apply to the semantic retrieval documents and chunks.'
    )
    file_search_top_k: int | None = Field(
        default=None, description='The number of semantic retrieval chunks to retrieve.'
    )

    url_context: bool | None = Field(
        default=None, description='Return grounding metadata from links included in the query'
    )

    @field_validator('response_modalities', mode='before')
    @classmethod
    def _upper_case_modalities(cls, value: object) -> object:
        """Accept 'Text' / 'image' the same as 'TEXT' / 'IMAGE'; the API is case-insensitive here."""
        if isinstance(value, list):
            return [v.upper() if isinstance(v, str) else v for v in cast(list[object], value)]
        return value

    @model_validator(mode='before')
    @classmethod
    def _reject_nested_keys(cls, data: Any) -> Any:  # noqa: ANN401
        """Name the flat fields when a caller passes a nested key they replaced."""
        if isinstance(data, Mapping):
            for key, value in cast(Mapping[str, Any], data).items():
                if isinstance(key, str) and (error := _flattened_key_error(key, value)) is not None:
                    raise error
        return data

    @model_validator(mode='after')
    def _reject_contradictions(self) -> Self:
        """Settings that can't both be set. Checked per layer and again on the merged config."""
        if self.thinking_level is not None and self.thinking_budget is not None:
            raise _both_set_error('thinking_level', 'thinking_budget')
        if self.google_search is False:
            options = [name for name in _GOOGLE_SEARCH_OPTIONS if getattr(self, name) is not None]
            if options:
                raise ValueError(
                    f'google_search=False with {", ".join(options)} set; drop the options, '
                    'or pass None for each to clear a default'
                )
        return self

    # inherited from ModelConfig:
    # version, temperature, max_output_tokens, top_k, top_p, stop_sequences

    temperature: Annotated[
        float | None,
        WithJsonSchema({
            'type': 'number',
            'minimum': 0.0,
            'maximum': 2.0,
            'description': (
                'Controls the randomness of the output. Values can range over [0.0, 2.0]. The default value is 1.0.'
            ),
        }),
    ] = Field(
        default=None,
        ge=0.0,
        le=2.0,
    )

    top_p: Annotated[
        float | None,
        WithJsonSchema({
            'type': 'number',
            'minimum': 0.0,
            'maximum': 1.0,
            'description': (
                'The maximum cumulative probability of tokens to consider when sampling. '
                'Values can range over [0.0, 1.0]. The default value is 0.95.'
            ),
        }),
    ] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    top_k: int | None = Field(  # pyrefly: ignore[bad-override]
        default=None,
        description=('The maximum number of tokens to consider when sampling.'),
    )

    thinking_level: ThinkingLevel | None = Field(
        default=None,
        description=(
            'For Gemini 3 and later - the thinking level. A higher level is associated with more '
            'detailed thinking, which is needed for solving more complex tasks. Not with thinking_budget.'
        ),
    )
    thinking_budget: int | None = Field(
        default=None,
        description=(
            'For Gemini 2.5 - the thinking budget in tokens. 0 is DISABLED. -1 is AUTOMATIC. '
            'The default values and allowed ranges are model dependent. Not with thinking_level.'
        ),
    )
    include_thoughts: bool | None = Field(
        default=None,
        description=(
            'Include thoughts in the response. Thoughts are returned only if the model supports '
            'thought and thoughts are available.'
        ),
    )

    max_output_tokens: int | None = Field(  # pyrefly: ignore[bad-override]
        default=None, description='Maximum number of tokens to generate.'
    )
    stop_sequences: list[str] | None = Field(default=None, description='Stop sequences.')

    # Sampling knobs GenerateContentConfig types. Declared so they stay flat
    # and SDK-validated now that unknown keys raise.
    seed: int | None = Field(default=None, description='Seed for decoding; repeats the same output for the same input.')
    presence_penalty: float | None = Field(
        default=None, description='Penalizes tokens that already appear in the output.'
    )
    frequency_penalty: float | None = Field(
        default=None, description='Penalizes tokens by how often they appear in the output.'
    )
    candidate_count: int | None = Field(default=None, description='Number of response candidates to generate.')
    response_logprobs: bool | None = Field(default=None, description='Return log probabilities of the output tokens.')
    logprobs: int | None = Field(
        default=None, description='Number of top candidate tokens to return log probabilities for.'
    )


DEFAULT_TTS_VOICE_NAME = 'Kore'
"""Prebuilt voice sent when a TTS model that needs one gets a request naming no voice."""

_GEMINI_API_TTS_MODELS_NEEDING_VOICE = frozenset({'gemini-3.1-flash-tts-preview'})
"""Gemini API TTS models that reject a request naming no voice. On Vertex AI every TTS model gets the default."""


def _body_names_voice(body: object) -> bool:
    """Whether a wire-shaped body names a voice under ``generationConfig.speechConfig``.

    A replicated (cloned) voice has no flat field and goes through
    ``config.extra``. Keys are compared the way google-genai's extra_body
    merge aligns them: underscores dropped, lowercased.
    """

    def child(node: object, name: str) -> object:
        if not isinstance(node, Mapping):
            return None
        for key, value in cast(Mapping[str, Any], node).items():
            if isinstance(key, str) and key.replace('_', '').lower() == name:
                return value
        return None

    speech = child(child(body, 'generationconfig'), 'speechconfig')
    return child(speech, 'voiceconfig') is not None or child(speech, 'multispeakervoiceconfig') is not None


def _extra_sets_voice(cfg: genai_types.GenerateContentConfig) -> bool:
    """Whether the extra body already on *cfg* names a voice, so the default voice stays out."""
    return _body_names_voice(cfg.http_options.extra_body if cfg.http_options else None)


class GeminiTtsConfig(GeminiConfig):
    """Gemini TTS Config."""

    voice: str | None = Field(
        default=None,
        description=(
            'Prebuilt voice name, e.g. "Kore". Not with speakers. Without voice or speakers, '
            f'models that reject a request without a voice get {DEFAULT_TTS_VOICE_NAME}.'
        ),
    )
    speakers: dict[str, str] | None = Field(
        default=None,
        description='Multi-speaker voices as {speaker name in the prompt: prebuilt voice name}. Not with voice.',
    )
    language_code: str | None = Field(
        default=None, description='Language code (ISO 639-1) for the speech, e.g. "en-US".'
    )

    @model_validator(mode='after')
    def _one_voice_kind(self) -> Self:
        if self.voice is not None and self.speakers is not None:
            raise _both_set_error('voice', 'speakers')
        return self


class GeminiImageConfig(GeminiConfig):
    """Gemini Image Config."""

    aspect_ratio: ImageAspectRatio | None = Field(default=None, description='Aspect ratio of the generated images.')
    image_size: ImageSize | None = Field(default=None, description='Size of the generated images.')
    output_mime_type: str | None = Field(
        default=None, description='MIME type of the generated image, e.g. "image/jpeg". Vertex AI only.'
    )
    output_compression_quality: int | None = Field(
        default=None, description='Compression quality of the generated image (image/jpeg only). Vertex AI only.'
    )
    person_generation: PersonGeneration | None = Field(default=None, description='Controls the generation of people.')
    prominent_people: ProminentPeople | None = Field(
        default=None, description='Whether generating prominent people (celebrities) is allowed.'
    )


class GemmaConfig(GeminiConfig):
    """Gemma Config."""

    # Inherits temperature from GeminiConfig
    temperature: float | None = None


GEMINI_TEXT_SUPPORTS = Supports(
    multiturn=True,
    media=True,
    tools=True,
    tool_choice=True,
    system_role=True,
    constrained=Constrained.ALL,
    output=['text', 'json'],
)

GEMINI_2_5_PRO_EXP_03_25 = ModelInfo(
    label='Google AI - Gemini 2.5 Pro Exp 03-25',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_2_5_PRO_PREVIEW_03_25 = ModelInfo(
    label='Google AI - Gemini 2.5 Pro Preview 03-25',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_2_5_PRO_PREVIEW_05_06 = ModelInfo(
    label='Google AI - Gemini 2.5 Pro Preview 05-06',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_2_5_FLASH_PREVIEW_04_17 = ModelInfo(
    label='Google AI - Gemini 2.5 Flash Preview 04-17',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_2_5_PRO = ModelInfo(
    label='Google AI - Gemini 2.5 Pro',
    supports=GEMINI_TEXT_SUPPORTS,
)

GEMINI_2_5_FLASH = ModelInfo(
    label='Google AI - Gemini 2.5 Flash',
    supports=GEMINI_TEXT_SUPPORTS,
)

GEMINI_2_5_FLASH_LITE = ModelInfo(
    label='Google AI - Gemini 2.5 Flash Lite',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.NO_TOOLS,
        output=['text', 'json'],
    ),
)

GEMINI_3_FLASH_PREVIEW = ModelInfo(
    label='Google AI - Gemini 3 Flash Preview',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_3_PRO_PREVIEW = ModelInfo(
    label='Google AI - Gemini 3 Pro Preview',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_3_5_FLASH = ModelInfo(
    label='Google AI - Gemini 3.5 Flash',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_3_6_FLASH = ModelInfo(
    label='Google AI - Gemini 3.6 Flash',
    supports=GEMINI_TEXT_SUPPORTS,
)

GEMINI_3_7_FLASH = ModelInfo(
    label='Google AI - Gemini 3.7 Flash',
    supports=GEMINI_TEXT_SUPPORTS,
)

GEMINI_3_1_PRO_PREVIEW = ModelInfo(
    label='Google AI - Gemini 3.1 Pro Preview',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

# customtools is registered identically to pro-preview (no distinct config in JS).
GEMINI_3_1_PRO_PREVIEW_CUSTOMTOOLS = ModelInfo(
    label='Google AI - Gemini 3.1 Pro Preview (Custom Tools)',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_3_1_FLASH_LITE_PREVIEW = ModelInfo(
    label='Google AI - Gemini 3.1 Flash Lite Preview',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_3_1_FLASH_LITE = ModelInfo(
    label='Google AI - Gemini 3.1 Flash Lite',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GEMINI_FLASH_LITE_LATEST = ModelInfo(
    label='Google AI - Gemini Flash Lite Latest',
    supports=GEMINI_TEXT_SUPPORTS,
)

GEMINI_IMAGE_SUPPORTS = Supports(
    multiturn=True,
    media=True,
    tools=True,
    tool_choice=True,
    system_role=True,
    constrained=Constrained.ALL,
)

GEMINI_3_PRO_IMAGE = ModelInfo(
    label='Google AI - Gemini 3 Pro Image',
    supports=GEMINI_IMAGE_SUPPORTS,
)

GEMINI_3_1_FLASH_IMAGE = ModelInfo(
    label='Google AI - Gemini 3.1 Flash Image',
    supports=GEMINI_IMAGE_SUPPORTS,
)

GEMINI_3_1_FLASH_IMAGE_PREVIEW = ModelInfo(
    label='Google AI - Gemini 3.1 Flash Image Preview',
    supports=GEMINI_IMAGE_SUPPORTS,
)

GEMINI_3_PRO_IMAGE_PREVIEW = ModelInfo(
    label='Google AI - Gemini 3 Pro Image Preview',
    supports=GEMINI_IMAGE_SUPPORTS,
)

GEMINI_2_5_FLASH_IMAGE = ModelInfo(
    label='Google AI - Gemini 2.5 Flash Image',
    supports=GEMINI_IMAGE_SUPPORTS,
)

GEMINI_2_5_FLASH_IMAGE_PREVIEW = ModelInfo(
    label='Google AI - Gemini 2.5 Flash Image Preview',
    supports=GEMINI_IMAGE_SUPPORTS,
)

GEMINI_TTS_SUPPORTS = Supports(
    multiturn=False,
    media=False,
    tools=False,
    tool_choice=False,
    system_role=False,
    constrained=Constrained.NONE,
    output=['media'],
)

GEMINI_2_5_FLASH_PREVIEW_TTS = ModelInfo(
    label='Google AI - Gemini 2.5 Flash Preview TTS',
    supports=GEMINI_TTS_SUPPORTS,
)

GEMINI_2_5_PRO_PREVIEW_TTS = ModelInfo(
    label='Google AI - Gemini 2.5 Pro Preview TTS',
    supports=GEMINI_TTS_SUPPORTS,
)

GEMINI_3_1_FLASH_TTS_PREVIEW = ModelInfo(
    label='Google AI - Gemini 3.1 Flash TTS Preview',
    supports=GEMINI_TTS_SUPPORTS,
)

GEMMA_SUPPORTS = Supports(
    multiturn=True,
    media=True,
    tools=True,
    tool_choice=True,
    system_role=True,
    constrained=Constrained.ALL,
    output=['text', 'json'],
)

GEMMA_4_26B_A4B_IT = ModelInfo(
    label='Google AI - Gemma 4 26B A4B IT',
    supports=GEMMA_SUPPORTS,
)

GEMMA_4_31B_IT = ModelInfo(
    label='Google AI - Gemma 4 31B IT',
    supports=GEMMA_SUPPORTS,
)

GENERIC_GEMINI_MODEL = ModelInfo(
    label='Google AI - Gemini',
    supports=Supports(
        multiturn=True,
        media=True,
        tools=True,
        tool_choice=True,
        system_role=True,
        constrained=Constrained.ALL,
        output=['text', 'json'],
    ),
)

GENERIC_TTS_MODEL = ModelInfo(
    label='Google AI - Gemini TTS',
    supports=GEMINI_TTS_SUPPORTS,
)

GENERIC_IMAGE_MODEL = ModelInfo(
    label='Google AI - Gemini Image',
    supports=Supports(
        multiturn=False,
        media=True,
        tools=False,
        tool_choice=False,
        system_role=True,
        constrained=Constrained.ALL,
        output=['media'],
    ),
)

GENERIC_GEMMA_MODEL = ModelInfo(
    label='Google AI - Gemma',
    supports=GEMMA_SUPPORTS,
)


# Quote autocomplete needs a Literal, so these aliases are the model-id
# catalog. Constructors take ``Known* | str``: listed ids autocomplete,
# and an id Google ships after this release still type-checks and routes.
KnownGemini: TypeAlias = Literal[
    'gemini-2.5-flash',
    'gemini-2.5-pro',
    'gemini-2.5-flash-lite',
    'gemini-flash-latest',
    'gemini-flash-lite-latest',
    'gemini-pro-latest',
    'gemini-3-flash-preview',
    'gemini-3-pro-preview',
    'gemini-3.1-flash-lite',
    'gemini-3.1-flash-lite-preview',
    'gemini-3.1-pro-preview',
    'gemini-3.1-pro-preview-customtools',
    'gemini-3.5-flash',
    'gemini-3.6-flash',
    'gemini-3.7-flash',
    'gemini-2.5-flash-preview-04-17',
    'gemini-2.5-pro-exp-03-25',
    'gemini-2.5-pro-preview-03-25',
    'gemini-2.5-pro-preview-05-06',
]
KnownGeminiTts: TypeAlias = Literal[
    'gemini-2.5-flash-preview-tts',
    'gemini-2.5-pro-preview-tts',
    'gemini-3.1-flash-tts-preview',
]
KnownGeminiImage: TypeAlias = Literal[
    'gemini-2.5-flash-image',
    'gemini-2.5-flash-image-preview',
    'gemini-3-pro-image',
    'gemini-3-pro-image-preview',
    'gemini-3.1-flash-image',
    'gemini-3.1-flash-image-preview',
]
KnownGemma: TypeAlias = Literal[
    'gemma-3-1b-it',
    'gemma-3-4b-it',
    'gemma-3-12b-it',
    'gemma-3-27b-it',
    'gemma-3n-e4b-it',
    'gemma-4-26b-a4b-it',
    'gemma-4-31b-it',
]


SUPPORTED_MODELS = {}


def _add_model(model_info: ModelInfo, names: list[str]) -> None:
    for name in names:
        SUPPORTED_MODELS[name] = model_info
    if model_info.versions:
        for version in model_info.versions:
            SUPPORTED_MODELS[version] = model_info


_add_model(GEMINI_2_5_PRO_EXP_03_25, ['gemini-2.5-pro-exp-03-25'])
_add_model(GEMINI_2_5_PRO_PREVIEW_03_25, ['gemini-2.5-pro-preview-03-25'])
_add_model(GEMINI_2_5_PRO_PREVIEW_05_06, ['gemini-2.5-pro-preview-05-06'])
_add_model(GEMINI_2_5_FLASH_PREVIEW_04_17, ['gemini-2.5-flash-preview-04-17'])
_add_model(GEMINI_2_5_PRO, ['gemini-2.5-pro'])
_add_model(GEMINI_2_5_FLASH, ['gemini-2.5-flash'])
_add_model(GEMINI_2_5_FLASH_LITE, ['gemini-2.5-flash-lite'])
_add_model(GEMINI_FLASH_LITE_LATEST, ['gemini-flash-lite-latest'])
_add_model(GEMINI_3_FLASH_PREVIEW, ['gemini-3-flash-preview'])
_add_model(GEMINI_3_PRO_PREVIEW, ['gemini-3-pro-preview', 'gemini-pro-latest'])
_add_model(GEMINI_3_5_FLASH, ['gemini-3.5-flash', 'gemini-flash-latest'])
_add_model(GEMINI_3_6_FLASH, ['gemini-3.6-flash'])
_add_model(GEMINI_3_7_FLASH, ['gemini-3.7-flash'])
_add_model(GEMINI_3_1_PRO_PREVIEW, ['gemini-3.1-pro-preview'])
_add_model(GEMINI_3_1_PRO_PREVIEW_CUSTOMTOOLS, ['gemini-3.1-pro-preview-customtools'])
_add_model(GEMINI_3_1_FLASH_LITE_PREVIEW, ['gemini-3.1-flash-lite-preview'])
_add_model(GEMINI_3_1_FLASH_LITE, ['gemini-3.1-flash-lite'])
_add_model(GEMINI_3_PRO_IMAGE, ['gemini-3-pro-image'])
_add_model(GEMINI_3_1_FLASH_IMAGE, ['gemini-3.1-flash-image'])
_add_model(GEMINI_3_1_FLASH_IMAGE_PREVIEW, ['gemini-3.1-flash-image-preview'])
_add_model(GEMINI_3_PRO_IMAGE_PREVIEW, ['gemini-3-pro-image-preview'])
_add_model(GEMINI_2_5_FLASH_IMAGE_PREVIEW, ['gemini-2.5-flash-image-preview'])
_add_model(GEMINI_2_5_FLASH_IMAGE, ['gemini-2.5-flash-image'])
_add_model(GEMINI_2_5_FLASH_PREVIEW_TTS, ['gemini-2.5-flash-preview-tts'])
_add_model(GEMINI_2_5_PRO_PREVIEW_TTS, ['gemini-2.5-pro-preview-tts'])
_add_model(GEMINI_3_1_FLASH_TTS_PREVIEW, ['gemini-3.1-flash-tts-preview'])
_add_model(GEMMA_4_26B_A4B_IT, ['gemma-4-26b-a4b-it'])
_add_model(GEMMA_4_31B_IT, ['gemma-4-31b-it'])

# Frozen at import so quote-autocomplete tests do not see ids that
# resolve() writes into SUPPORTED_MODELS later.
GEMINI_CATALOG_IDS = frozenset(SUPPORTED_MODELS)


DEFAULT_SUPPORTS_MODEL = Supports(
    multiturn=True,
    media=True,
    tools=True,
    tool_choice=True,
    system_role=True,
    constrained=Constrained.ALL,
)


def is_gemini_model(name: str) -> bool:
    """Check if the model is a standard Gemini text generation model.

    Excludes TTS and image variants which have different capabilities.

    Args:
        name: The model name to check.

    Returns:
        True if this is a standard Gemini model (not TTS or image).

    Example:
        >>> is_gemini_model('gemini-2.0-flash-001')
        True
        >>> is_gemini_model('gemini-2.5-flash-preview-tts')
        False
    """
    local = name.split('/')[-1].lower()
    return local.startswith('gemini-') and not is_tts_model(local) and not is_image_model(local)


def is_tts_model(name: str) -> bool:
    """Check if the model is a Gemini text-to-speech (TTS) model.

    TTS is a ``gemini-`` name that contains ``-tts``. Strip the plugin /
    ``models/`` prefix first so ``googleai/gemini-…-tts`` still routes here.

    Args:
        name: The model name to check.

    Returns:
        True if this is a TTS model.

    Example:
        >>> is_tts_model('gemini-2.5-flash-preview-tts')
        True
    """
    local = name.split('/')[-1].lower()
    return local.startswith('gemini-') and '-tts' in local


def is_image_model(name: str) -> bool:
    """Check if the model is a Gemini native image generation model.

    Native image is a ``gemini-`` name that contains ``-image``. The
    ``gemini-`` prefix is required: a bare ``image`` substring would also
    match ``imagen-`` ids, which have no generate path here.

    Args:
        name: The model name to check.

    Returns:
        True if this is a Gemini image model.

    Example:
        >>> is_image_model('gemini-2.0-flash-preview-image-generation')
        True
    """
    local = name.split('/')[-1].lower()
    return local.startswith('gemini-') and '-image' in local


def is_gemma_model(name: str) -> bool:
    """Check if the model is a Gemma open model.

    Gemma is the ``gemma-`` prefix on the local name after stripping the
    plugin / ``models/`` prefix.

    Args:
        name: The model name to check.

    Returns:
        True if this is a Gemma model.

    Example:
        >>> is_gemma_model('gemma-2-27b-it')
        True
    """
    return name.split('/')[-1].lower().startswith('gemma-')


def is_tuned_gemini_name(name: str) -> bool:
    """Check whether a model name refers to a Vertex AI tuned Gemini endpoint.

    Accepts both the short form (``endpoints/ID``) and the fully qualified
    resource path (``projects/PROJECT/locations/LOCATION/endpoints/ID``).
    Mirrors ``isTunedGeminiName`` in the Go plugin.

    Args:
        name: The model name to check.

    Returns:
        True if this is a tuned endpoint name.

    Example:
        >>> is_tuned_gemini_name('endpoints/1234567890')
        True
        >>> is_tuned_gemini_name('projects/p/locations/us-central1/endpoints/9')
        True
        >>> is_tuned_gemini_name('gemini-2.5-flash')
        False
    """
    if name.startswith('endpoints/'):
        return True
    return name.startswith('projects/') and '/locations/' in name and '/endpoints/' in name


def resolve_vertex_model_name(client: genai.Client, name: str) -> str:
    """Prepare a model name for the google-genai SDK.

    The SDK's internal model-name transformer prefixes unqualified names with
    ``publishers/google/models/``, which is wrong for tuned endpoints. For a
    short-form ``endpoints/ID`` this expands to the fully qualified
    ``projects/PROJECT/locations/LOCATION/endpoints/ID`` using the client's
    configured project and location so the SDK passes it through unchanged.
    Non-tuned names are returned as-is. Mirrors
    ``gemini.go:resolveVertexModelName`` in the Go plugin.

    Args:
        client: The genai.Client whose project/location to use.
        name: The incoming model name.

    Returns:
        A name safe to hand to ``client.aio.models.generate_content``.
    """
    if not is_tuned_gemini_name(name):
        return name
    if name.startswith('projects/'):
        return name
    api_client = getattr(client, '_api_client', None)
    if api_client is None or not getattr(api_client, 'vertexai', False):
        return name
    project = getattr(api_client, 'project', None) or ''
    location = getattr(api_client, 'location', None) or ''
    if not project or not location:
        return name
    return f'projects/{project}/locations/{location}/{name}'


def get_model_config_schema(name: str) -> type[GeminiConfig]:
    """Get the appropriate config schema for a dynamically discovered model.

    Different model types (TTS, image, Gemma, standard) have different
    configuration options. This function returns the correct schema based
    on the model name.

    Args:
        name: The model name to determine schema for.

    Returns:
        The appropriate config schema class:
        - GeminiTtsConfig for TTS models
        - GeminiImageConfig for image models
        - GemmaConfig for Gemma models
        - GeminiConfig for standard Gemini models
    """
    if is_tts_model(name):
        return GeminiTtsConfig
    if is_image_model(name):
        return GeminiImageConfig
    if is_gemma_model(name):
        return GemmaConfig
    return GeminiConfig


def google_model_info(
    version: str,
) -> ModelInfo:
    """Generates a ModelInfo object.

    This function returns the best ModelInfo Supports based on model type.
    Detects TTS, Image, Gemma, and standard Gemini models.

    Args:
        version: Version of the model.

    Returns:
        ModelInfo object with appropriate capabilities.
    """
    if version in SUPPORTED_MODELS:
        return SUPPORTED_MODELS[version]

    if is_tts_model(version):
        return GENERIC_TTS_MODEL
    if is_image_model(version):
        return GENERIC_IMAGE_MODEL
    if is_gemma_model(version):
        return GENERIC_GEMMA_MODEL

    return ModelInfo(
        label=f'Google AI - {version}',
        supports=DEFAULT_SUPPORTS_MODEL,
    )


_adc_project_cache: str | None = None
_adc_project_probed: bool = False


async def _adc_project() -> str | None:
    """Resolve the project from application default credentials, cached.

    ADC resolution can do file and metadata-server IO, so it runs in a thread
    and is attempted only once per process. A failed or empty resolution is
    cached too: without ADC configured (express mode, say) every overridden
    request would otherwise pay for a probe that can stall on the metadata
    server. Concurrent first calls may duplicate the probe, which is benign.
    """
    global _adc_project_cache, _adc_project_probed
    if not _adc_project_probed:
        try:
            _, project = await asyncio.to_thread(google_auth_default)
            _adc_project_cache = project
        except DefaultCredentialsError:
            _adc_project_cache = None
        _adc_project_probed = True
    return _adc_project_cache


class GeminiModel:
    """Gemini model."""

    def __init__(
        self,
        version: str,
        client: genai.Client,
        client_kwargs: dict[str, Any] | None = None,
        base_url_pinned: bool = False,
    ) -> None:
        """Initialize Gemini model.

        Args:
            version: Gemini version
            client: Google AI client
            client_kwargs: The plugin-level kwargs the client was constructed
                from. Required for a per-request tenant key or client knobs
                (api_version, base_url, location).
            base_url_pinned: Whether the plugin caller explicitly pinned a
                base URL (as opposed to one derived from the location).
        """
        self._version = version
        self._client = client
        self._client_kwargs = client_kwargs
        self._base_url_pinned = base_url_pinned

    def _get_tools(self, request: ModelRequest) -> list[genai_types.Tool]:
        """Generates VertexAI Gemini compatible tool definitions.

        Args:
            request: The generation request.

        Returns:
             list of Gemini tools
        """
        tools, _table = self._declare_tools(request)
        return tools

    def _declare_tools(self, request: ModelRequest) -> tuple[list[genai_types.Tool], ToolTable]:
        """Declare this turn's tools and the table that unwraps their calls."""
        tools: list[genai_types.Tool] = []
        entries: list[ToolWire] = []
        for tool in request.tools or []:
            genai_tool, wire = self._create_tool(tool)
            tools.append(genai_tool)
            entries.append(wire)
        return tools, ToolTable(entries)

    def _create_tool(self, tool: ToolDefinition) -> tuple[genai_types.Tool, ToolWire]:
        """Create a tool that is compatible with Google Genai API.

        Args:
            tool: Genkit Tool Definition

        Returns:
            Genai tool compatible with Gemini API, plus how it was declared.
        """
        params = self._convert_schema_property(tool.input_schema)
        wrapped = False
        # Empty params: Gemini requires type=OBJECT even for no-arg tools.
        if not params:
            params = genai_types.Schema(type=genai_types.Type.OBJECT, properties={})
        elif params.type != genai_types.Type.OBJECT:
            # wrap after convert so OBJECT / Type.OBJECT / $ref enums / ['null']
            # all see the same type Gemini will
            wrapped = True
            params = genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties={TOOL_INPUT_FIELD: params},
                required=[TOOL_INPUT_FIELD],
            )

        wire_name = tool.name.replace('/', '__')
        function = genai_types.FunctionDeclaration(
            name=wire_name,
            description=tool.description,
            parameters=params,
            response=self._convert_schema_property(tool.output_schema) if tool.output_schema else None,
        )
        return genai_types.Tool(function_declarations=[function]), ToolWire(
            original_name=tool.name,
            wire_name=wire_name,
            wrapped=wrapped,
        )

    def _convert_schema_property(
        self, input_schema: dict[str, object] | None, defs: dict[str, object] | None = None
    ) -> genai_types.Schema | None:
        """Sanitizes a schema to be compatible with Gemini API.

        Args:
            input_schema: A dictionary with input parameters
            defs: Dictionary with definitions. Optional.

        Returns:
            Schema or None
        """
        if input_schema is None:
            return None

        if defs is None:
            defs_value = input_schema.get('$defs')
            defs = cast(dict[str, object], defs_value) if isinstance(defs_value, dict) else {}

        if '$ref' in input_schema:
            ref_path = input_schema['$ref']
            if isinstance(ref_path, str):
                ref_tokens = ref_path.split('/')
                ref_name = ref_tokens[-1]

                if defs is None or ref_name not in defs:
                    raise ValueError(f'Failed to resolve schema for {ref_name}')

                ref_schema = defs[ref_name]
                if isinstance(ref_schema, dict):
                    schema = self._convert_schema_property(cast(dict[str, object], ref_schema), defs)
                else:
                    schema = None

                if schema and input_schema.get('description'):
                    schema.description = cast(str, input_schema['description'])

                return schema

        if 'type' not in input_schema:
            return None

        schema = genai_types.Schema()
        if input_schema.get('description'):
            schema.description = cast(str, input_schema['description'])

        if 'required' in input_schema:
            schema.required = cast(list[str], input_schema['required'])

        if 'type' in input_schema:
            raw_type = input_schema['type']
            if isinstance(raw_type, list):
                non_null = [t for t in raw_type if t != 'null']
                schema.nullable = True
                raw_type = non_null[0] if non_null else 'string'
            schema_type = genai_types.Type(cast(str, raw_type))
            schema.type = schema_type

            if 'enum' in input_schema:
                schema.enum = cast(list[str], input_schema['enum'])

            if schema_type == genai_types.Type.ARRAY:
                items_value = input_schema.get('items')
                if isinstance(items_value, dict):
                    schema.items = self._convert_schema_property(cast(dict[str, object], items_value), defs)

            if schema_type == genai_types.Type.OBJECT:
                schema.properties = {}
                properties_value = input_schema.get('properties', {})
                if isinstance(properties_value, dict):
                    properties = cast(dict[str, dict[str, object]], properties_value)
                    for key in properties:
                        nested_schema = self._convert_schema_property(properties[key], defs)
                        if nested_schema:
                            schema.properties[key] = nested_schema

        return schema

    async def _retrieve_cached_content(
        self,
        request: ModelRequest,
        model_name: str,
        cache_config: dict,
        contents: list[genai_types.Content],
        client: genai.Client | None = None,
    ) -> genai_types.CachedContent:
        """Retrieves cached content from the Google API if exists.

        If content is present - increases storage ttl based on the configured `ttl_seconds`
        If content is not present - creates it and returns creates instance.

        Args:
            request: incoming generation instance
            model_name: name of the generation model to use
            cache_config: user-defined cache configuration (e.g. ttl_seconds)
            contents: content to submit for cached context creation
            client: client to use for cache operations. Defaults to the
                plugin-configured client.

        Returns:
            Cached Content instance based on provided params
        """
        validate_context_cache_request(request=request, model_name=model_name)
        cache_client = client if client is not None else self._client

        ttl_value = cache_config.get('ttl_seconds', DEFAULT_TTL)
        ttl: float = float(ttl_value) if ttl_value is not None else DEFAULT_TTL
        cache_key = generate_cache_key(contents=contents, model_name=model_name)

        iterator_config = genai_types.ListCachedContentsConfig()
        cache = None
        # These calls run before generate, so a provider or credential failure
        # here is classified the same way a generate failure is.
        try:
            pages = await cache_client.aio.caches.list(config=iterator_config)

            async for item in pages:
                if item.display_name == cache_key:
                    cache = item
                    break
            if cache and cache.name:
                updated_expiration_time = datetime.now(timezone.utc) + timedelta(seconds=ttl)
                cache = await cache_client.aio.caches.update(
                    name=cache.name, config=genai_types.UpdateCachedContentConfig(expire_time=updated_expiration_time)
                )
            else:
                cache = await cache_client.aio.caches.create(
                    model=model_name,
                    config=genai_types.CreateCachedContentConfig(
                        contents=cast(genai_types.ContentListUnion, contents),
                        display_name=cache_key,
                        ttl=f'{ttl}s',
                    ),
                )
        except APIError as e:
            raise api_error(e) from e
        except GOOGLE_AUTH_ERRORS as e:
            raise_auth_error(e)
        except TRANSPORT_ERRORS as e:
            raise transport_error(e) from e
        return cache

    async def generate(self, request: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
        """Handle a generation request.

        Args:
            request: The generation request containing messages and parameters.
            ctx: action context

        Returns:
            The model's response to the generation request.
        """
        model_name = self._version
        if request.config:
            version = getattr(request.config, 'version', None)
            if version:
                model_name = version

        declared_tools, tool_table = self._declare_tools(request)

        # TODO(#4361): Do not move - this method mutates `request` by extracting system
        # prompts into configuration object
        request_cfg = await self._genkit_to_googleai_cfg(request=request, declared_tools=declared_tools)

        # TTS models require response_modalities: ["AUDIO"]; some reject a request that names no voice
        if is_tts_model(model_name):
            if not request_cfg:
                request_cfg = genai_types.GenerateContentConfig()
            if not request_cfg.response_modalities:
                request_cfg.response_modalities = ['AUDIO']
            if self._tts_needs_default_voice(model_name) and not _extra_sets_voice(request_cfg):
                speech = request_cfg.speech_config
                if speech is None:
                    speech = genai_types.SpeechConfig()
                    request_cfg.speech_config = speech
                if (
                    not isinstance(speech, str)
                    and speech.voice_config is None
                    and speech.multi_speaker_voice_config is None
                ):
                    speech.voice_config = genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=DEFAULT_TTS_VOICE_NAME)
                    )

        # Image models require response_modalities: ["TEXT", "IMAGE"]
        if is_image_model(model_name):
            if not request_cfg:
                request_cfg = genai_types.GenerateContentConfig()
            if not request_cfg.response_modalities:
                request_cfg.response_modalities = ['TEXT', 'IMAGE']

        # Resolve the client before building messages so context-cache
        # operations run against the same (possibly overridden) region as the
        # generate call.
        client = await self._resolve_request_client(request, context=ctx.context)

        request_contents, cached_content = await self._build_messages(
            request=request, model_name=model_name, client=client, tools=tool_table
        )

        if cached_content and cached_content.name:
            if not request_cfg:
                request_cfg = genai_types.GenerateContentConfig()
            request_cfg.cached_content = cached_content.name

        if ctx.is_streaming:
            response = await self._streaming_generate(
                request_contents=request_contents,
                request_cfg=request_cfg,
                ctx=ctx,
                model_name=model_name,
                client=client,
                tools=tool_table,
            )
        else:
            response = await self._generate(
                request_contents=request_contents,
                request_cfg=request_cfg,
                model_name=model_name,
                client=client,
                tools=tool_table,
            )

        response.usage = self._create_usage_stats(request=request, response=response)

        return response

    def _tts_needs_default_voice(self, model_name: str) -> bool:
        """Whether a TTS request that names no voice is sent the default voice.

        Args:
            model_name: The TTS model the request goes to.

        Returns:
            True on Vertex AI, and for the Gemini API models in ``_GEMINI_API_TTS_MODELS_NEEDING_VOICE``.
        """
        if self._client.vertexai:
            return True
        return model_name.split('/')[-1].lower() in _GEMINI_API_TTS_MODELS_NEEDING_VOICE

    async def _resolve_request_client(
        self, request: ModelRequest, context: dict[str, Any] | None = None
    ) -> genai.Client:
        """Resolve the client to use for a request.

        A tenant key lives in ``context.secrets``. ``request.config`` is
        client knobs (``base_url``, ``api_version``, ``location``), not
        the key. Any of those rebuilds a request-scoped client; otherwise
        the plugin client is reused.
        """
        reject_request_config_api_key(request.config)
        api_version = None
        base_url_override = None
        location_override = None
        bag = context if isinstance(context, dict) else {}
        secret_key = context_api_key(bag)

        if request.config:
            if isinstance(request.config, dict):
                api_version = request.config.get('api_version')
                base_url_override = request.config.get('base_url')
                location_override = request.config.get('location')
            else:
                api_version = getattr(request.config, 'api_version', None)
                base_url_override = getattr(request.config, 'base_url', None)
                location_override = getattr(request.config, 'location', None)

        if location_override and not self._client.vertexai:
            # Location is a Vertex AI concept; ignore it for the Gemini API backend.
            location_override = None

        if not (api_version or secret_key or base_url_override or location_override):
            return self._client

        if self._client_kwargs is None:
            raise GenkitError(
                status='FAILED_PRECONDITION',
                message='Per-request api_key/api_version/base_url/location overrides require '
                'a model constructed with client_kwargs.',
            )

        # Clone the plugin-level client kwargs so the temporary client keeps the
        # plugin's credentials, endpoint, headers, and timeouts.
        kwargs = dict(self._client_kwargs)
        plugin_opts = kwargs.get('http_options')
        opts = plugin_opts.model_copy(deep=True) if plugin_opts is not None else genai_types.HttpOptions()

        if api_version:
            opts.api_version = api_version
        if location_override:
            kwargs['location'] = location_override
            if not self._base_url_pinned and not base_url_override:
                if is_multi_regional_location(location_override):
                    # Multi-regions are served from dedicated endpoints the SDK
                    # does not derive itself.
                    opts.base_url = multi_regional_base_url(location_override)
                else:
                    opts.base_url = None
        if base_url_override:
            opts.base_url = base_url_override
        if secret_key:
            # Express / tenant keys are not a regional Vertex host. Drop
            # project, location, and the plugin base_url unless this call
            # set one.
            kwargs['api_key'] = secret_key
            kwargs['credentials'] = None
            kwargs.pop('project', None)
            kwargs.pop('location', None)
            if not base_url_override:
                opts.base_url = None
        kwargs['http_options'] = opts

        # The plugin's kwargs may carry project=None when the project comes
        # from ADC. Resolve it here, off the event loop: the SDK's own
        # resolution would block the loop, and it skips resolution entirely
        # when a base_url is set. Express mode (api_key) takes no project --
        # the SDK rejects the two together -- so the probe is skipped there.
        if self._client.vertexai and not kwargs.get('project') and not kwargs.get('api_key'):
            kwargs['project'] = getattr(kwargs.get('credentials'), 'project_id', None) or await _adc_project()
        if self._client.vertexai and not kwargs.get('project') and is_multi_regional_location(kwargs.get('location')):
            if kwargs.get('api_key'):
                raise GenkitError(
                    status='FAILED_PRECONDITION',
                    message='Multi-region locations are not available in Vertex AI express '
                    'mode (api_key). Configure the plugin with a project and credentials '
                    'to use multi-region locations.',
                )
            raise GenkitError(
                status='FAILED_PRECONDITION',
                message='A project is required when overriding the location with a '
                'multi-region. Set the project parameter or GOOGLE_CLOUD_PROJECT '
                'environment variable.',
            )

        try:
            return genai.Client(**kwargs)
        except GOOGLE_AUTH_ERRORS as e:
            # A Vertex override with no key or explicit credentials makes the SDK look up ADC.
            raise_auth_error(e)
        except (ValueError, TypeError) as e:
            # The SDK rejects bad override combinations (api_key with project, say).
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message='Failed to create google-genai client',
                cause=e,
            ) from e

    async def _generate(
        self,
        request_contents: list[genai_types.Content],
        request_cfg: genai_types.GenerateContentConfig | None,
        model_name: str,
        client: genai.Client | None = None,
        tools: ToolTable | None = None,
    ) -> ModelResponse:
        """Call google-genai generate.

        Args:
            request_contents: request contents
            request_cfg: request configuration
            model_name: name of generation model to use
            client: optional client to use for the request
            tools: tools declared this turn

        Returns:
            genai response.
        """
        client = client or self._client
        try:
            response = await client.aio.models.generate_content(
                model=resolve_vertex_model_name(client, model_name),
                contents=cast(genai_types.ContentListUnion, request_contents),
                config=request_cfg,
            )
        except APIError as e:
            raise api_error(e) from e
        except GOOGLE_AUTH_ERRORS as e:
            # The SDK resolves and refreshes credentials on the request, not at construction.
            raise_auth_error(e)
        except TRANSPORT_ERRORS as e:
            raise transport_error(e) from e

        content = await self._contents_from_response(response, tools=tools)

        # Ensure we always have at least one content item to avoid UI errors
        if not content:
            content = [Part.from_text('')]

        finish_reason = FinishReason.OTHER
        candidates = []
        if response.candidates:
            for i, c in enumerate(response.candidates):
                c_content = []
                if c.content and c.content.parts:
                    for part in c.content.parts:
                        converted = PartConverter.from_gemini(part=part, tools=tools)
                        if converted:
                            c_content.append(converted)

                if not c_content:
                    c_content = [Part.from_text('')]

                c_finish_reason = _to_finish_reason(c.finish_reason)

                if i == 0:
                    finish_reason = c_finish_reason

                candidates.append(
                    Candidate(
                        index=float(i),
                        message=Message(role=Role.MODEL, content=c_content),
                        finish_reason=c_finish_reason,
                    )
                )

        return ModelResponse(
            message=Message(
                content=content,
                role=Role.MODEL,
            ),
            finish_reason=finish_reason,
            candidates=candidates,
            usage=_usage_from_metadata(response.usage_metadata),
        )

    async def _streaming_generate(
        self,
        request_contents: list[genai_types.Content],
        request_cfg: genai_types.GenerateContentConfig | None,
        ctx: ActionRunContext,
        model_name: str,
        client: genai.Client | None = None,
        tools: ToolTable | None = None,
    ) -> ModelResponse:
        """Call google-genai generate for streaming.

        Args:
            request_contents: request contents
            request_cfg: request configuration
            ctx: action context
            model_name: name of generation model to use
            client: optional client to use for the request
            tools: tools declared this turn

        Returns:
            empty genai response
        """
        client = client or self._client
        try:
            generator = await client.aio.models.generate_content_stream(
                model=resolve_vertex_model_name(client, model_name),
                contents=cast(genai_types.ContentListUnion, request_contents),
                config=request_cfg,
            )
            # The HTTP call happens on the first iteration, not on the
            # await that created the generator, so classify has to cover
            # the async for as well.
            accumulated_content: list[Part] = []
            finish_reason = FinishReason.UNKNOWN
            usage_metadata: Any = None
            async for response_chunk in generator:
                content = await self._contents_from_response(response_chunk, tools=tools)
                if content:  # Only process if we have content
                    accumulated_content.extend(content)
                    ctx.send_chunk(
                        chunk=ModelResponseChunk(
                            content=content,
                            role=Role.MODEL,
                        )
                    )
                # The terminating reason and cumulative token usage ride on the trailing
                # chunks, so hold onto the latest values we see as the stream drains —
                # otherwise a streamed turn reports no finish reason and no usage at all.
                if response_chunk.candidates and response_chunk.candidates[0] is not None:
                    fr = response_chunk.candidates[0].finish_reason
                    if fr:
                        finish_reason = _to_finish_reason(fr)
                if response_chunk.usage_metadata is not None:
                    usage_metadata = response_chunk.usage_metadata

            return ModelResponse(
                message=Message(
                    role=Role.MODEL,
                    content=accumulated_content,
                ),
                finish_reason=finish_reason,
                usage=_usage_from_metadata(usage_metadata),
            )
        except APIError as e:
            raise api_error(e) from e
        except GOOGLE_AUTH_ERRORS as e:
            raise_auth_error(e)
        except TRANSPORT_ERRORS as e:
            raise transport_error(e) from e

    @cached_property
    def metadata(self) -> dict:
        """Model metadata.

        Returns:
            model metadata.
        """
        if self._version in SUPPORTED_MODELS:
            supports = SUPPORTED_MODELS[self._version].supports.model_dump(by_alias=True, exclude_none=True)
        else:
            # Fallback to default supports for models not explicitly listed
            supports = DEFAULT_SUPPORTS_MODEL.model_dump(by_alias=True, exclude_none=True)
        return {
            'model': {
                'label': f'Google AI - {self._version}',
                'supports': supports,
            }
        }

    async def _build_messages(
        self,
        request: ModelRequest,
        model_name: str,
        client: genai.Client | None = None,
        tools: ToolTable | None = None,
    ) -> tuple[list[genai_types.Content], genai_types.CachedContent | None]:
        """Build google-genai request contents from Genkit request.

        Args:
            request: Genkit request.
            model_name: name of generation model to use
            client: client to use for context-cache operations. Defaults to
                the plugin-configured client.
            tools: tools declared this turn

        Returns:
            list of google-genai contents.
        """
        request_contents: list[genai_types.Content] = []
        cache = None

        for msg in request.messages:
            if msg.role == Role.SYSTEM:
                continue
            content_parts: list[genai_types.Part] = []
            for p in msg.content:
                converted = await PartConverter.to_gemini(p, tools=tools)
                if isinstance(converted, list):
                    content_parts.extend(converted)
                else:
                    content_parts.append(converted)
            role = 'model' if msg.role in (Role.MODEL, 'model') else 'user'
            request_contents.append(genai_types.Content(parts=content_parts, role=role))

            if msg.metadata and msg.metadata.get('cache'):
                cache = await self._retrieve_cached_content(
                    request=request,
                    model_name=model_name,
                    cache_config=msg.metadata['cache'],
                    contents=request_contents,
                    client=client,
                )
                # The prefix up to this message is now stored in the cache.
                # Only post-cache messages should be sent in the generate call.
                request_contents = []

        if not request_contents:
            request_contents.append(genai_types.Content(parts=[genai_types.Part(text=' ')], role='user'))

        return request_contents, cache

    async def _contents_from_response(
        self, response: genai_types.GenerateContentResponse, *, tools: ToolTable | None = None
    ) -> list:
        """Retrieve contents from google-genai response.

        Args:
            response: google-genai response.
            tools: tools declared this turn.

        Returns:
            list of generated contents.
        """
        content = []
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        converted = PartConverter.from_gemini(part=part, tools=tools)
                        if converted:  # Only append if conversion succeeded
                            content.append(converted)

        # Ensure we always return a list, even if empty
        return content if content else []

    async def _genkit_to_googleai_cfg(
        self,
        request: ModelRequest,
        *,
        declared_tools: list[genai_types.Tool] | None = None,
    ) -> genai_types.GenerateContentConfig | None:
        """Converts a Genkit ModelRequest to a Gemini GenerateContentConfig.

        The conversion follows a linear pipeline:
        1. Extract system instructions from messages
        2. Dump the typed request.config instance into a snake_case dict
        3. Extract tool-related fields from the dict
        4. Clean Genkit-specific / unsupported keys from the dict
        5. Build GenerateContentConfig from known fields; leftovers ride on extra_body,
           and ``config.extra`` is merged over the top of the request body
        """
        system_instruction: list[genai.types.Part] = []

        # 1. System messages
        system_messages = list(filter(lambda m: m.role == Role.SYSTEM, request.messages))
        for m in system_messages:
            if m.content:
                for p in m.content:
                    converted = await PartConverter.to_gemini(p)
                    if isinstance(converted, list):
                        system_instruction.extend(converted)
                    else:
                        system_instruction.append(converted)

        cfg = None
        tools: list[genai_types.Tool] = []

        leftovers: dict[str, Any] = {}
        extra: dict[str, Any] | None = None
        if request.config:
            # 2. Normalize config into a dict
            dumped_config = self._normalize_config_to_dict(request.config)

            if dumped_config is not None:
                # config.extra is wire-shaped; it goes on the body as-is in step 5.
                extra = dumped_config.pop('extra', None)

                # 3. Extract tool-related fields
                self._check_backend_fields(dumped_config)
                self._extract_tools_from_config(dumped_config, tools)
                self._nest_generation_fields(dumped_config, extra)

                # 4. Clean Genkit-specific and unsupported keys
                self._clean_unsupported_keys(dumped_config)

                # 5. Build GenerateContentConfig from known fields. Leftovers are
                # declared fields the installed SDK doesn't type yet; they ride
                # on extra_body under generationConfig.
                known, leftovers = split_sdk_fields(dumped_config, genai_types.GenerateContentConfig)
                if known:
                    try:
                        cfg = genai_types.GenerateContentConfig(**known)
                    except ValidationError as e:
                        raise sdk_config_error(action_name=self._version, error=e) from e

        # Tools from top-level field and config-level fields
        function_tools = declared_tools if declared_tools is not None else self._get_tools(request)
        tools.extend(function_tools)

        has_output = bool(request.output_format or request.output_schema)

        if cfg is not None or tools or system_instruction or request.output_format or leftovers or extra:
            if cfg is None:
                cfg = genai_types.GenerateContentConfig()

            if has_output:
                model_name = self._version
                if request.config:
                    version = getattr(request.config, 'version', None)
                    if version:
                        model_name = version

                # Check if the model supports constrained generation with this configuration
                model_info = google_model_info(model_name)
                model_supports_constrained = (
                    model_info.supports.constrained if model_info and model_info.supports else Constrained.NO_TOOLS
                )
                supports_constrained = model_supports_constrained == Constrained.ALL or (
                    model_supports_constrained == Constrained.NO_TOOLS and not request.tools
                )

                response_mime_type = (
                    'application/json' if request.output_format == 'json' and supports_constrained else None
                )
                cfg.response_mime_type = response_mime_type

                if request.output_schema and request.output_constrained and supports_constrained:
                    cfg.response_schema = self._convert_schema_property(request.output_schema)

            if tools:
                cfg.tools = cast(genai_types.ToolListUnion, tools)

            if request.tool_choice and function_tools:
                cfg.tool_config = _tool_config(request.tool_choice, function_tools)

            cfg.system_instruction = genai_types.Content(parts=system_instruction) if system_instruction else None
            cfg = attach_leftovers(cfg, leftovers, nest='generationConfig')
            cfg = attach_config_extra(
                cfg,
                extra,
                action_name=self._version,
                managed_body_fields=GEMINI_MANAGED_BODY_FIELDS,
                managed_generation_fields=GEMINI_MANAGED_GENERATION_FIELDS,
            )
            return keep_client_extra_body(cfg, (self._client_kwargs or {}).get('http_options'))

        return None

    # -- Config conversion helpers (called by _genkit_to_googleai_cfg) --

    # Keys that are Genkit-specific and must not be forwarded to the API.
    # 'version' overrides the model name, others are client-level settings.
    _GENKIT_ONLY_KEYS = frozenset(['version', 'api_version', 'api_key', 'base_url', 'location', 'context_cache'])

    # Keys that may not be supported by older google-genai SDK versions.
    _SDK_GATED_KEYS = frozenset(['image_config', 'thinking_config', 'response_modalities'])

    def _normalize_config_to_dict(
        self,
        config: GeminiConfig | None,
    ) -> dict[str, Any] | None:
        """Dump a typed family config to a snake_case dict for the SDK."""
        return dump_family_config(
            config=config,
            expected_type=GeminiConfig,
            action_name=self._version,
        )

    def _invalid_config(self, message: str) -> GenkitError:
        return GenkitError(
            status='INVALID_ARGUMENT', message=f'{self._version}: {message}', reason=RuntimeErrorReason.INVALID_INPUT
        )

    def _check_backend_fields(self, config: Mapping[str, Any]) -> None:
        """Raise for settings the Gemini API rejects, naming the flat field.

        google-genai raises its own ValueError for these, with the nested
        SDK path; the plugin knows the backend, so it raises first.
        """
        if self._client.vertexai:
            return
        fields = [name for name in _VERTEX_ONLY_FIELDS if config.get(name) is not None]
        if any('method' in s for s in config.get('safety_settings') or []):
            fields.append('safety_settings[].method')
        if fields:
            raise self._invalid_config(f'{", ".join(fields)}: Vertex AI only, not supported on the Gemini API')

    def _extract_tools_from_config(
        self,
        config: dict[str, Any],
        tools: list[genai_types.Tool],
    ) -> None:
        """Turn the flat tool fields into ``tools`` entries.

        Mutates *config* by popping consumed keys and appends to *tools*.
        Rules that span two fields which can come from different layers
        (ModelRef, prompt, call) are checked here, on the merged config.
        """
        if config.pop('code_execution', None):
            tools.append(genai_types.Tool(code_execution=genai_types.ToolCodeExecution()))

        # Safety settings — filter out unspecified categories
        if 'safety_settings' in config:
            config['safety_settings'] = [
                s for s in config['safety_settings'] if s['category'] != 'HARM_CATEGORY_UNSPECIFIED'
            ]

        # Google Search: True, or any option with google_search unset. The
        # config class already rejected False alongside options.
        search = _pop_prefixed(config, 'google_search_')
        if config.pop('google_search', None) or search:
            options: dict[str, Any] = {}
            if 'types' in search:
                options['search_types'] = {f'{t}_search': {} for t in search.pop('types')}
            start, end = search.pop('start_time', None), search.pop('end_time', None)
            if (start is None) != (end is None):
                raise self._invalid_config('set google_search_start_time and google_search_end_time together')
            if start is not None:
                # The API rejects sub-second precision ("Granularity of nano is
                # not supported"), so datetime.now() would fail as sent.
                options['time_range_filter'] = {
                    'start_time': start.replace(microsecond=0),
                    'end_time': end.replace(microsecond=0),
                }
            options.update(search)  # exclude_domains, blocking_confidence
            tools.append(genai_types.Tool(google_search=genai_types.GoogleSearch(**options)))

        # File Search. Empty store names (an untouched Dev UI list) mean off.
        file_search = _pop_prefixed(config, 'file_search_')
        stores = [s for s in file_search.pop('store_names', None) or [] if s]
        if stores:
            tools.append(
                genai_types.Tool(file_search=genai_types.FileSearch(file_search_store_names=stores, **file_search))
            )
        elif file_search:
            names = ', '.join(f'file_search_{k}' for k in file_search)
            raise self._invalid_config(f'{names} needs file_search_store_names')

        if config.pop('url_context', None):
            tools.append(genai_types.Tool(url_context=genai_types.UrlContext()))

    def _nest_generation_fields(self, config: dict[str, Any], extra: Mapping[str, Any] | None) -> None:
        """Group the flat thinking, image and speech fields into their nested request objects.

        Mutates *config*. The dicts match what the nested Genkit classes used
        to dump, so the request body is unchanged.
        """
        thinking = {key: config.pop(key) for key in _THINKING_FIELDS if key in config}
        if thinking:
            config['thinking_config'] = thinking

        image = {key: config.pop(key) for key in _IMAGE_FIELDS if key in config}
        if image:
            config['image_config'] = image

        voice, speakers = config.pop('voice', None), config.pop('speakers', None)
        language_code = config.pop('language_code', None)
        speech: dict[str, Any] = {}
        if voice is not None:
            speech['voice_config'] = {'prebuilt_voice_config': {'voice_name': voice}}
        if speakers is not None:
            speech['multi_speaker_voice_config'] = {
                'speaker_voice_configs': [
                    {'speaker': speaker, 'voice_config': {'prebuilt_voice_config': {'voice_name': name}}}
                    for speaker, name in speakers.items()
                ]
            }
        if speech and _body_names_voice(extra):
            # extra is deep-merged into the body, so both voices would be sent.
            raise self._invalid_config(
                f'{"voice" if voice is not None else "speakers"} and extra generationConfig.speechConfig '
                'both name a voice; pass one'
            )
        if language_code is not None:
            speech['language_code'] = language_code
        if speech:
            config['speech_config'] = speech

    def _clean_unsupported_keys(self, config: dict[str, Any]) -> None:
        """Remove Genkit-specific and SDK-gated keys from the config dict.

        Mutates *config* in place.
        """
        for key in self._GENKIT_ONLY_KEYS:
            config.pop(key, None)

        for key in self._SDK_GATED_KEYS:
            if key in config and key not in genai_types.GenerateContentConfig.model_fields:
                del config[key]

    def _create_usage_stats(self, request: ModelRequest, response: ModelResponse) -> ModelUsage:
        """Create usage statistics.

        Args:
            request: Genkit request
            response: Genkit response

        Returns:
            usage statistics
        """
        if not response.message:
            usage = ModelUsage()
            usage.input_tokens = 0
            usage.output_tokens = 0
            usage.total_tokens = 0
            return usage

        usage = get_basic_usage_stats(input_=request.messages, response=response.message)
        if response.usage:
            for field in ('input_tokens', 'output_tokens', 'total_tokens', 'thoughts_tokens', 'cached_content_tokens'):
                val = getattr(response.usage, field, None)
                if val is not None:
                    setattr(usage, field, val)

        return usage
