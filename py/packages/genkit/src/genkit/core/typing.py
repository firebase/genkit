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

"""Schema types module defining the core data models for Genkit.

This module contains Pydantic models that define the structure and validation
for various data types used throughout the Genkit framework, including messages,
actions, tools, and configuration options.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel


class Model(RootModel[Any]):
    """Model data type class."""

    root: Any


class CustomPart(BaseModel):
    """Model for custompart data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    text: Any | None = None
    media: Any | None = None
    tool_request: Any | None = Field(None, alias='toolRequest')
    tool_response: Any | None = Field(None, alias='toolResponse')
    data: Any | None = None
    metadata: dict[str, Any] | None = None
    custom: dict[str, Any]


class Media(BaseModel):
    """Model for media data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    content_type: str | None = Field(None, alias='contentType')
    url: str


class ToolRequest(BaseModel):
    """Model for toolrequest data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    ref: str | None = None
    name: str
    input: Any | None = None


class ToolResponse(BaseModel):
    """Model for toolresponse data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    ref: str | None = None
    name: str
    output: Any | None = None


class Embedding(BaseModel):
    """Model for embedding data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    embedding: list[float]
    metadata: dict[str, Any] | None = None


class BaseDataPoint(BaseModel):
    """Model for basedatapoint data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    input: Any | None = None
    output: Any | None = None
    context: list | None = None
    reference: Any | None = None
    test_case_id: str | None = Field(None, alias='testCaseId')
    trace_ids: list[str] | None = Field(None, alias='traceIds')


class EvalRequest(BaseModel):
    """Model for evalrequest data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    dataset: list[BaseDataPoint]
    eval_run_id: str = Field(..., alias='evalRunId')
    options: Any | None = None


class Details(BaseModel):
    """Model for details data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    reasoning: str | None = None


class Score(BaseModel):
    """Model for score data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    id: str | None = Field(
        None, description='Optional ID to differentiate different scores'
    )
    score: float | str | bool | None = None
    error: str | None = None
    details: Details | None = None


class Code(StrEnum):
    """Enumeration of code values."""

    BLOCKED = 'blocked'
    OTHER = 'other'
    UNKNOWN = 'unknown'


class CandidateError(BaseModel):
    """Model for candidateerror data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    index: float
    code: Code
    message: str | None = None


class FinishReason(StrEnum):
    """Enumeration of finishreason values."""

    STOP = 'stop'
    LENGTH = 'length'
    BLOCKED = 'blocked'
    INTERRUPTED = 'interrupted'
    OTHER = 'other'
    UNKNOWN = 'unknown'


class ToolChoice(StrEnum):
    """Enumeration of toolchoice values."""

    AUTO = 'auto'
    REQUIRED = 'required'
    NONE = 'none'


class GenerateActionOutputConfig(BaseModel):
    """Model for generateactionoutputconfig data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    format: str | None = None
    content_type: str | None = Field(None, alias='contentType')
    instructions: bool | str | None = None
    json_schema: Any | None = Field(None, alias='jsonSchema')
    constrained: bool | None = None


class GenerationCommonConfig(BaseModel):
    """Model for generationcommonconfig data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    version: str | None = None
    temperature: float | None = None
    max_output_tokens: float | None = Field(None, alias='maxOutputTokens')
    top_k: float | None = Field(None, alias='topK')
    top_p: float | None = Field(None, alias='topP')
    stop_sequences: list[str] | None = Field(None, alias='stopSequences')


class GenerationUsage(BaseModel):
    """Model for generationusage data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    input_tokens: float | None = Field(None, alias='inputTokens')
    output_tokens: float | None = Field(None, alias='outputTokens')
    total_tokens: float | None = Field(None, alias='totalTokens')
    input_characters: float | None = Field(None, alias='inputCharacters')
    output_characters: float | None = Field(None, alias='outputCharacters')
    input_images: float | None = Field(None, alias='inputImages')
    output_images: float | None = Field(None, alias='outputImages')
    input_videos: float | None = Field(None, alias='inputVideos')
    output_videos: float | None = Field(None, alias='outputVideos')
    input_audio_files: float | None = Field(None, alias='inputAudioFiles')
    output_audio_files: float | None = Field(None, alias='outputAudioFiles')
    custom: dict[str, float] | None = None


class Constrained(StrEnum):
    """Enumeration of constrained values."""

    NONE = 'none'
    ALL = 'all'
    NO_TOOLS = 'no-tools'


class Supports(BaseModel):
    """Model for supports data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    multiturn: bool | None = None
    media: bool | None = None
    tools: bool | None = None
    system_role: bool | None = Field(None, alias='systemRole')
    output: list[str] | None = None
    content_type: list[str] | None = Field(None, alias='contentType')
    context: bool | None = None
    constrained: Constrained | None = None
    tool_choice: bool | None = Field(None, alias='toolChoice')


class Stage(StrEnum):
    """Enumeration of stage values."""

    FEATURED = 'featured'
    STABLE = 'stable'
    UNSTABLE = 'unstable'
    LEGACY = 'legacy'
    DEPRECATED = 'deprecated'


class ModelInfo(BaseModel):
    """Model for modelinfo data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    versions: list[str] | None = None
    label: str | None = None
    supports: Supports | None = None
    stage: Stage | None = None


class OutputConfig(BaseModel):
    """Model for outputconfig data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    format: str | None = None
    schema_: dict[str, Any] | None = Field(None, alias='schema')
    constrained: bool | None = None
    instructions: str | None = None
    content_type: str | None = Field(None, alias='contentType')


class Role(StrEnum):
    """Enumeration of role values."""

    SYSTEM = 'system'
    USER = 'user'
    MODEL = 'model'
    TOOL = 'tool'


class ToolDefinition(BaseModel):
    """Model for tooldefinition data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    name: str
    description: str
    input_schema: dict[str, Any] | None = Field(
        None,
        alias='inputSchema',
        description='Valid JSON Schema representing the input of the tool.',
    )
    output_schema: dict[str, Any] | None = Field(
        None,
        alias='outputSchema',
        description='Valid JSON Schema describing the output of the tool.',
    )
    metadata: dict[str, Any] | None = Field(
        None, description='additional metadata for this tool definition'
    )


class CommonRerankerOptions(BaseModel):
    """Model for commonrerankeroptions data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    k: float | None = Field(None, description='Number of documents to rerank')


class RankedDocumentMetadata(BaseModel):
    """Model for rankeddocumentmetadata data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    score: float


class CommonRetrieverOptions(BaseModel):
    """Model for commonretrieveroptions data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    k: float | None = Field(None, description='Number of documents to retrieve')


class InstrumentationLibrary(BaseModel):
    """Model for instrumentationlibrary data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    name: str
    version: str | None = None
    schema_url: str | None = Field(None, alias='schemaUrl')


class PathMetadata(BaseModel):
    """Model for pathmetadata data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    path: str
    status: str
    error: str | None = None
    latency: float


class SpanContext(BaseModel):
    """Model for spancontext data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    trace_id: str = Field(..., alias='traceId')
    span_id: str = Field(..., alias='spanId')
    is_remote: bool | None = Field(None, alias='isRemote')
    trace_flags: float = Field(..., alias='traceFlags')


class SameProcessAsParentSpan(BaseModel):
    """Model for sameprocessasparentspan data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    value: bool


class State(StrEnum):
    """Enumeration of state values."""

    SUCCESS = 'success'
    ERROR = 'error'


class SpanMetadata(BaseModel):
    """Model for spanmetadata data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    name: str
    state: State | None = None
    input: Any | None = None
    output: Any | None = None
    is_root: bool | None = Field(None, alias='isRoot')
    metadata: dict[str, str] | None = None
    path: str | None = None


class SpanStatus(BaseModel):
    """Model for spanstatus data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    code: float
    message: str | None = None


class Annotation(BaseModel):
    """Model for annotation data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    attributes: dict[str, Any]
    description: str


class TimeEvent(BaseModel):
    """Model for timeevent data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    time: float
    annotation: Annotation


class TraceMetadata(BaseModel):
    """Model for tracemetadata data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    feature_name: str | None = Field(None, alias='featureName')
    paths: set[PathMetadata] | None = None
    timestamp: float


class Context(RootModel[list]):
    """Context data type class."""

    root: list


class Input(RootModel[Any]):
    """Input data type class."""

    root: Any


class Output(RootModel[Any]):
    """Output data type class."""

    root: Any


class Reference(RootModel[Any]):
    """Reference data type class."""

    root: Any


class TraceIds(RootModel[list[str]]):
    """TraceIds data type class."""

    root: list[str]


class Data(RootModel[Any]):
    """Data data type class."""

    root: Any


class MediaModel(RootModel[Any]):
    """MediaModel data type class."""

    root: Any


class Metadata(RootModel[dict[str, Any] | None]):
    """Metadata data type class."""

    root: dict[str, Any] | None = None


class Text(RootModel[Any]):
    """Text data type class."""

    root: Any


class ToolRequestModel(RootModel[Any]):
    """ToolRequestModel data type class."""

    root: Any


class ToolResponseModel(RootModel[Any]):
    """ToolResponseModel data type class."""

    root: Any


class Custom(RootModel[dict[str, Any] | None]):
    """Custom data type class."""

    root: dict[str, Any] | None = None


class Config(RootModel[Any]):
    """Config data type class."""

    root: Any


class OutputModel(RootModel[OutputConfig]):
    """OutputModel data type class."""

    root: OutputConfig


class Tools(RootModel[list[ToolDefinition]]):
    """Tools data type class."""

    root: list[ToolDefinition]


class CustomModel(RootModel[Any]):
    """CustomModel data type class."""

    root: Any


class FinishMessage(RootModel[str]):
    """FinishMessage data type class."""

    root: str


class LatencyMs(RootModel[float]):
    """LatencyMs data type class."""

    root: float


class Raw(RootModel[Any]):
    """Raw data type class."""

    root: Any


class Usage(RootModel[GenerationUsage]):
    """Usage data type class."""

    root: GenerationUsage


class Aggregated(RootModel[bool]):
    """Aggregated data type class."""

    root: bool


class Index(RootModel[float]):
    """Index data type class."""

    root: float


class DataPart(BaseModel):
    """Model for datapart data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    text: Text | None = None
    media: MediaModel | None = None
    tool_request: ToolRequestModel | None = Field(None, alias='toolRequest')
    tool_response: ToolResponseModel | None = Field(None, alias='toolResponse')
    data: Any | None = None
    metadata: Metadata | None = None
    custom: dict[str, Any] | None = None


class MediaPart(BaseModel):
    """Model for mediapart data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    text: Text | None = None
    media: Media
    tool_request: ToolRequestModel | None = Field(None, alias='toolRequest')
    tool_response: ToolResponseModel | None = Field(None, alias='toolResponse')
    data: Data | None = None
    metadata: Metadata | None = None
    custom: Custom | None = None


class TextPart(BaseModel):
    """Model for textpart data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    text: str
    media: MediaModel | None = None
    tool_request: ToolRequestModel | None = Field(None, alias='toolRequest')
    tool_response: ToolResponseModel | None = Field(None, alias='toolResponse')
    data: Data | None = None
    metadata: Metadata | None = None
    custom: Custom | None = None


class ToolRequestPart(BaseModel):
    """Model for toolrequestpart data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    text: Text | None = None
    media: MediaModel | None = None
    tool_request: ToolRequest = Field(..., alias='toolRequest')
    tool_response: ToolResponseModel | None = Field(None, alias='toolResponse')
    data: Data | None = None
    metadata: Metadata | None = None
    custom: Custom | None = None


class ToolResponsePart(BaseModel):
    """Model for toolresponsepart data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    text: Text | None = None
    media: MediaModel | None = None
    tool_request: ToolRequestModel | None = Field(None, alias='toolRequest')
    tool_response: ToolResponse = Field(..., alias='toolResponse')
    data: Data | None = None
    metadata: Metadata | None = None
    custom: Custom | None = None


class EmbedResponse(BaseModel):
    """Model for embedresponse data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    embeddings: list[Embedding]


class BaseEvalDataPoint(BaseModel):
    """Model for baseevaldatapoint data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    input: Input | None = None
    output: Output | None = None
    context: Context | None = None
    reference: Reference | None = None
    test_case_id: str = Field(..., alias='testCaseId')
    trace_ids: TraceIds | None = Field(None, alias='traceIds')


class EvalFnResponse(BaseModel):
    """Model for evalfnresponse data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    sample_index: float | None = Field(None, alias='sampleIndex')
    test_case_id: str = Field(..., alias='testCaseId')
    trace_id: str | None = Field(None, alias='traceId')
    span_id: str | None = Field(None, alias='spanId')
    evaluation: Score | list[Score]


class EvalResponse(RootModel[list[EvalFnResponse]]):
    """EvalResponse data type class."""

    root: list[EvalFnResponse]


class Resume(BaseModel):
    """Model for resume data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    respond: list[ToolResponsePart] | None = None
    restart: list[ToolRequestPart] | None = None
    metadata: dict[str, Any] | None = None


class Part(
    RootModel[
        TextPart
        | MediaPart
        | ToolRequestPart
        | ToolResponsePart
        | DataPart
        | CustomPart
    ]
):
    """Part data type class."""

    root: (
        TextPart
        | MediaPart
        | ToolRequestPart
        | ToolResponsePart
        | DataPart
        | CustomPart
    )


class Link(BaseModel):
    """Model for link data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    context: SpanContext | None = None
    attributes: dict[str, Any] | None = None
    dropped_attributes_count: float | None = Field(
        None, alias='droppedAttributesCount'
    )


class TimeEvents(BaseModel):
    """Model for timeevents data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    time_event: list[TimeEvent] | None = Field(None, alias='timeEvent')


class SpanData(BaseModel):
    """Model for spandata data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    span_id: str = Field(..., alias='spanId')
    trace_id: str = Field(..., alias='traceId')
    parent_span_id: str | None = Field(None, alias='parentSpanId')
    start_time: float = Field(..., alias='startTime')
    end_time: float = Field(..., alias='endTime')
    attributes: dict[str, Any]
    display_name: str = Field(..., alias='displayName')
    links: list[Link] | None = None
    instrumentation_library: InstrumentationLibrary = Field(
        ..., alias='instrumentationLibrary'
    )
    span_kind: str = Field(..., alias='spanKind')
    same_process_as_parent_span: SameProcessAsParentSpan | None = Field(
        None, alias='sameProcessAsParentSpan'
    )
    status: SpanStatus | None = None
    time_events: TimeEvents | None = Field(None, alias='timeEvents')
    truncated: bool | None = None


class TraceData(BaseModel):
    """Model for tracedata data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    trace_id: str = Field(..., alias='traceId')
    display_name: str | None = Field(None, alias='displayName')
    start_time: float | None = Field(
        None,
        alias='startTime',
        description='trace start time in milliseconds since the epoch',
    )
    end_time: float | None = Field(
        None,
        alias='endTime',
        description='end time in milliseconds since the epoch',
    )
    spans: dict[str, SpanData]


class Content(RootModel[list[Part]]):
    """Content data type class."""

    root: list[Part]


class DocumentPart(RootModel[TextPart | MediaPart]):
    """DocumentPart data type class."""

    root: TextPart | MediaPart


class GenerateResponseChunk(BaseModel):
    """Model for generateresponsechunk data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    role: Role | None = None
    index: float | None = None
    content: list[Part]
    custom: Any | None = None
    aggregated: bool | None = None


class Message(BaseModel):
    """Model for message data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    role: Role
    content: list[Part]
    metadata: dict[str, Any] | None = None


class ModelResponseChunk(BaseModel):
    """Model for modelresponsechunk data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    role: Role | None = None
    index: Index | None = None
    content: Content
    custom: CustomModel | None = None
    aggregated: Aggregated | None = None


class RankedDocumentData(BaseModel):
    """Model for rankeddocumentdata data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    content: list[DocumentPart]
    metadata: RankedDocumentMetadata


class RerankerResponse(BaseModel):
    """Model for rerankerresponse data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    documents: list[RankedDocumentData]


class Messages(RootModel[list[Message]]):
    """Messages data type class."""

    root: list[Message]


class DocumentData(BaseModel):
    """Model for documentdata data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    content: list[DocumentPart]
    metadata: dict[str, Any] | None = None


class EmbedRequest(BaseModel):
    """Model for embedrequest data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    input: list[DocumentData]
    options: Any | None = None


class Candidate(BaseModel):
    """Model for candidate data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    index: float
    message: Message
    usage: GenerationUsage | None = None
    finish_reason: FinishReason = Field(..., alias='finishReason')
    finish_message: str | None = Field(None, alias='finishMessage')
    custom: Any | None = None


class GenerateActionOptions(BaseModel):
    """Model for generateactionoptions data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    model: str
    docs: list[DocumentData] | None = None
    messages: list[Message]
    tools: list[str] | None = None
    tool_choice: ToolChoice | None = Field(None, alias='toolChoice')
    config: Any | None = None
    output: GenerateActionOutputConfig | None = None
    resume: Resume | None = None
    return_tool_requests: bool | None = Field(None, alias='returnToolRequests')
    max_turns: float | None = Field(None, alias='maxTurns')


class GenerateRequest(BaseModel):
    """Model for generaterequest data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    messages: list[Message]
    config: Any | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: ToolChoice | None = Field(None, alias='toolChoice')
    output: OutputConfig | None = None
    docs: list[DocumentData] | None = None
    candidates: float | None = None


class GenerateResponse(BaseModel):
    """Model for generateresponse data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    message: Message | None = None
    finish_reason: FinishReason | None = Field(None, alias='finishReason')
    finish_message: str | None = Field(None, alias='finishMessage')
    latency_ms: float | None = Field(None, alias='latencyMs')
    usage: GenerationUsage | None = None
    custom: Any | None = None
    raw: Any | None = None
    request: GenerateRequest | None = None
    candidates: list[Candidate] | None = None


class RerankerRequest(BaseModel):
    """Model for rerankerrequest data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    query: DocumentData
    documents: list[DocumentData]
    options: Any | None = None


class RetrieverRequest(BaseModel):
    """Model for retrieverrequest data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    query: DocumentData
    options: Any | None = None


class RetrieverResponse(BaseModel):
    """Model for retrieverresponse data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    documents: list[DocumentData]


class Docs(RootModel[list[DocumentData]]):
    """Docs data type class."""

    root: list[DocumentData]


class Request(RootModel[GenerateRequest]):
    """Request data type class."""

    root: GenerateRequest


class ModelRequest(BaseModel):
    """Model for modelrequest data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    messages: Messages
    config: Config | None = None
    tools: Tools | None = None
    tool_choice: ToolChoice | None = Field(None, alias='toolChoice')
    output: OutputModel | None = None
    docs: Docs | None = None


class ModelResponse(BaseModel):
    """Model for modelresponse data."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)
    message: Message | None = None
    finish_reason: FinishReason = Field(..., alias='finishReason')
    finish_message: FinishMessage | None = Field(None, alias='finishMessage')
    latency_ms: LatencyMs | None = Field(None, alias='latencyMs')
    usage: Usage | None = None
    custom: CustomModel | None = None
    raw: Raw | None = None
    request: Request | None = None
