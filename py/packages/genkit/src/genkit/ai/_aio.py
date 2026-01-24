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

"""User-facing asyncio API for Genkit.

To use Genkit in your application, construct an instance of the `Genkit`
class while customizing it with any plugins.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

from genkit.aio import Channel
from genkit.blocks.document import Document
from genkit.blocks.embedding import EmbedderRef
from genkit.blocks.evaluator import EvaluatorRef
from genkit.blocks.generate import (
    StreamingCallback as ModelStreamingCallback,
    generate_action,
)
from genkit.blocks.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
    ModelMiddleware,
)
from genkit.blocks.prompt import PromptConfig, load_prompt_folder, to_generate_action_options
from genkit.blocks.retriever import IndexerRef, IndexerRequest, RetrieverRef
from genkit.core.action import ActionRunContext
from genkit.core.action.types import ActionKind
from genkit.core.plugin import Plugin
from genkit.core.typing import (
    BaseDataPoint,
    EmbedRequest,
    EmbedResponse,
    EvalRequest,
    EvalResponse,
)
from genkit.types import (
    DocumentData,
    GenerationCommonConfig,
    Message,
    OutputConfig,
    Part,
    RetrieverRequest,
    RetrieverResponse,
    ToolChoice,
)

from ._base_async import GenkitBase
from ._server import ServerSpec


class Genkit(GenkitBase):
    """Genkit asyncio user-facing API."""

    def __init__(
        self,
        plugins: list[Plugin] | None = None,
        model: str | None = None,
        prompt_dir: str | Path | None = None,
        reflection_server_spec: ServerSpec | None = None,
    ) -> None:
        """Initialize a new Genkit instance.

        Args:
            plugins: List of plugins to initialize.
            model: Model name to use.
            prompt_dir: Directory to automatically load prompts from.
                If not provided, defaults to loading from './prompts' if it exists.
            reflection_server_spec: Server spec for the reflection
                server.
        """
        super().__init__(plugins=plugins, model=model, reflection_server_spec=reflection_server_spec)

        load_path = prompt_dir
        if load_path is None:
            default_prompts_path = Path('./prompts')
            if default_prompts_path.is_dir():
                load_path = default_prompts_path

        if load_path:
            load_prompt_folder(self.registry, dir_path=load_path)

    async def generate(
        self,
        model: str | None = None,
        prompt: str | Part | list[Part] | None = None,
        system: str | Part | list[Part] | None = None,
        messages: list[Message] | None = None,
        tools: list[str] | None = None,
        return_tool_requests: bool | None = None,
        tool_choice: ToolChoice | None = None,
        tool_responses: list[Part] | None = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        max_turns: int | None = None,
        on_chunk: ModelStreamingCallback | None = None,
        context: dict[str, Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: type | dict[str, Any] | None = None,
        output_constrained: bool | None = None,
        output: OutputConfig | dict[str, Any] | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | None = None,
    ) -> GenerateResponseWrapper:
        """Generates text or structured data using a language model.

        This function provides a flexible interface for interacting with various
        language models, supporting both simple text generation and more complex
        interactions involving tools and structured conversations.

        Args:
            model: Optional. The name of the model to use for generation. If not
                provided, a default model may be used.
            prompt: Optional. A single prompt string, a `Part` object, or a list
                of `Part` objects to provide as input to the model. This is used
                for simple text generation.
            system: Optional. A system message string, a `Part` object, or a
                list of `Part` objects to provide context or instructions to
                the model, especially for chat-based models.
            messages: Optional. A list of `Message` objects representing a
                conversation history.  This is used for chat-based models to
                maintain context.
            tools: Optional. A list of tool names (strings) that the model can
                use.
            return_tool_requests: Optional. If `True`, the model will return
                tool requests instead of executing them directly.
            tool_choice: Optional. A `ToolChoice` object specifying how the
                model should choose which tool to use.
            tool_responses: Optional. tool_responses should contain a list of
                tool response parts corresponding to interrupt tool request
                parts from the most recent model message. Each entry must have
                a matching `name` and `ref` (if supplied) for its tool request
                counterpart.
            config: Optional. A `GenerationCommonConfig` object or a dictionary
                containing configuration parameters for the generation process.
                This allows fine-tuning the model's behavior.
            max_turns: Optional. The maximum number of turns in a conversation.
            on_chunk: Optional. A callback function of type
                `ModelStreamingCallback` that is called for each chunk of
                generated text during streaming.
            context: Optional. A dictionary containing additional context
                information that can be used during generation.
            output_format: Optional. The format to use for the output (e.g.,
                'json').
            output_content_type: Optional. The content type of the output.
            output_instructions: Optional. Instructions for formatting the
                output.
            output_schema: Optional. Schema defining the structure of the
                output.
            output_constrained: Optional. Whether to constrain the output to the
                schema.
            output: Optional. An `OutputConfig` object or dictionary containing
                output configuration. This groups output-related parameters.
            use: Optional. A list of `ModelMiddleware` functions to apply to the
                generation process. Middleware can be used to intercept and
                modify requests and responses.
            docs: Optional. A list of documents to be used for grounding.


        Returns:
            A `GenerateResponseWrapper` object containing the model's response,
            which may include generated text, tool requests, or other relevant
            information.

        Note:
            - The `tools`, `return_tool_requests`, and `tool_choice` arguments
              are used for models that support tool usage.
            - The `on_chunk` argument enables streaming responses, allowing you
              to process the generated content as it becomes available.
        """
        # Unpack output config if provided
        if output:
            if isinstance(output, dict):
                # Handle dict input - extract values directly
                if output_format is None:
                    output_format = output.get('format')
                if output_content_type is None:
                    output_content_type = output.get('content_type')
                if output_instructions is None:
                    output_instructions = output.get('instructions')
                if output_schema is None:
                    output_schema = output.get('schema')
                if output_constrained is None:
                    output_constrained = output.get('constrained')
            else:
                # Handle OutputConfig object - use getattr for safety since
                # OutputConfig is auto-generated and may not have all fields.
                # Note: schema_ is the Python attribute name in OutputConfig because
                # 'schema' is a reserved attribute in Pydantic BaseModel. The field
                # uses Field(alias='schema') for JSON serialization.
                if output_format is None:
                    output_format = getattr(output, 'format', None)
                if output_content_type is None:
                    output_content_type = getattr(output, 'content_type', None)
                if output_instructions is None:
                    output_instructions = getattr(output, 'instructions', None)
                if output_schema is None:
                    output_schema = getattr(output, 'schema_', None)
                if output_constrained is None:
                    output_constrained = getattr(output, 'constrained', None)

        return await generate_action(
            self.registry,
            await to_generate_action_options(
                self.registry,
                PromptConfig(
                    model=model,
                    prompt=prompt,
                    system=system,
                    messages=messages,
                    tools=tools,
                    return_tool_requests=return_tool_requests,
                    tool_choice=tool_choice,
                    tool_responses=tool_responses,
                    config=config,
                    max_turns=max_turns,
                    output_format=output_format,
                    output_content_type=output_content_type,
                    output_instructions=output_instructions,
                    output_schema=output_schema,
                    output_constrained=output_constrained,
                    docs=docs,
                ),
            ),
            on_chunk=on_chunk,
            middleware=use,
            context=context if context else ActionRunContext._current_context(),
        )

    def generate_stream(
        self,
        model: str | None = None,
        prompt: str | Part | list[Part] | None = None,
        system: str | Part | list[Part] | None = None,
        messages: list[Message] | None = None,
        tools: list[str] | None = None,
        return_tool_requests: bool | None = None,
        tool_choice: ToolChoice | None = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        max_turns: int | None = None,
        context: dict[str, Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: type | dict[str, Any] | None = None,
        output_constrained: bool | None = None,
        output: OutputConfig | dict[str, Any] | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | None = None,
        timeout: float | None = None,
    ) -> tuple[
        AsyncIterator[GenerateResponseChunkWrapper],
        asyncio.Future[GenerateResponseWrapper],
    ]:
        """Streams generated text or structured data using a language model.

        This function provides a flexible interface for interacting with various
        language models, supporting both simple text generation and more complex
        interactions involving tools and structured conversations.

        Args:
            model: Optional. The name of the model to use for generation. If not
                provided, a default model may be used.
            prompt: Optional. A single prompt string, a `Part` object, or a list
                of `Part` objects to provide as input to the model. This is used
                for simple text generation.
            system: Optional. A system message string, a `Part` object, or a
                list of `Part` objects to provide context or instructions to the
                model, especially for chat-based models.
            messages: Optional. A list of `Message` objects representing a
                conversation history.  This is used for chat-based models to
                maintain context.
            tools: Optional. A list of tool names (strings) that the model can
                use.
            return_tool_requests: Optional. If `True`, the model will return
                tool requests instead of executing them directly.
            tool_choice: Optional. A `ToolChoice` object specifying how the
                model should choose which tool to use.
            config: Optional. A `GenerationCommonConfig` object or a dictionary
                containing configuration parameters for the generation process.
                This allows fine-tuning the model's behavior.
            max_turns: Optional. The maximum number of turns in a conversation.
            context: Optional. A dictionary containing additional context
                information that can be used during generation.
            output_format: Optional. The format to use for the output (e.g.,
                'json').
            output_content_type: Optional. The content type of the output.
            output_instructions: Optional. Instructions for formatting the
                output.
            output_schema: Optional. Schema defining the structure of the
                output.
            output_constrained: Optional. Whether to constrain the output to the
                schema.
            output: Optional. An `OutputConfig` object or dictionary containing
                output configuration. This groups output-related parameters.
            use: Optional. A list of `ModelMiddleware` functions to apply to the
                generation process. Middleware can be used to intercept and
                modify requests and responses.
            docs: Optional. A list of documents to be used for grounding.
            timeout: Optional. The timeout for the streaming action.

        Returns:
            A `GenerateResponseWrapper` object containing the model's response,
            which may include generated text, tool requests, or other relevant
            information.

        Note:
            - The `tools`, `return_tool_requests`, and `tool_choice` arguments
              are used for models that support tool usage.
            - The `on_chunk` argument enables streaming responses, allowing you
              to process the generated content as it becomes available.
        """
        stream = Channel(timeout=timeout)

        resp = self.generate(
            model=model,
            prompt=prompt,
            system=system,
            messages=messages,
            tools=tools,
            return_tool_requests=return_tool_requests,
            tool_choice=tool_choice,
            config=config,
            max_turns=max_turns,
            context=context,
            output_format=output_format,
            output_content_type=output_content_type,
            output_instructions=output_instructions,
            output_schema=output_schema,
            output_constrained=output_constrained,
            output=output,
            docs=docs,
            use=use,
            on_chunk=lambda c: stream.send(c),
        )
        stream.set_close_future(asyncio.create_task(resp))

        return stream, stream.closed

    async def retrieve(
        self,
        retriever: str | RetrieverRef | None = None,
        query: str | DocumentData | None = None,
        options: dict[str, Any] | None = None,
    ) -> RetrieverResponse:
        """Retrieves documents based on query.

        Args:
            retriever: Optional retriever name or reference to use.
            query: Text query or a DocumentData containing query text.
            options: Optional retriever-specific options.

        Returns:
            The generated response with documents.
        """
        retriever_name: str
        retriever_config: dict[str, Any] = {}

        if isinstance(retriever, RetrieverRef):
            retriever_name = retriever.name
            retriever_config = retriever.config or {}
            if retriever.version:
                retriever_config['version'] = retriever.version
        elif isinstance(retriever, str):
            retriever_name = retriever
        else:
            raise ValueError('Retriever must be specified as a string name or a RetrieverRef.')

        if isinstance(query, str):
            query = Document.from_text(query)

        request_options = {**(retriever_config or {}), **(options or {})}

        retrieve_action = await self.registry.resolve_action(cast(ActionKind, ActionKind.RETRIEVER), retriever_name)
        if retrieve_action is None:
            raise ValueError(f'Retriever "{retriever_name}" not found')

        if query is None:
            raise ValueError('Query must be specified for retrieval.')

        return (
            await retrieve_action.arun(
                RetrieverRequest(
                    query=query,
                    options=request_options if request_options else None,
                )
            )
        ).response

    async def index(
        self,
        indexer: str | IndexerRef | None = None,
        documents: list[Document] | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        """Indexes documents.

        Args:
            indexer: Optional indexer name or reference to use.
            documents: Documents to index.
            options: Optional indexer-specific options.
        """
        indexer_name: str
        indexer_config: dict[str, Any] = {}

        if isinstance(indexer, IndexerRef):
            indexer_name = indexer.name
            indexer_config = indexer.config or {}
            if indexer.version:
                indexer_config['version'] = indexer.version
        elif isinstance(indexer, str):
            indexer_name = indexer
        else:
            raise ValueError('Indexer must be specified as a string name or an IndexerRef.')

        req_options = {**(indexer_config or {}), **(options or {})}

        index_action = await self.registry.resolve_action(cast(ActionKind, ActionKind.INDEXER), indexer_name)
        if index_action is None:
            raise ValueError(f'Indexer "{indexer_name}" not found')

        if documents is None:
            raise ValueError('Documents must be specified for indexing.')

        await index_action.arun(
            IndexerRequest(
                # Document subclasses DocumentData, so this is type-safe at runtime.
                # The type checker doesn't recognize the subclass relationship here.
                documents=documents,  # type: ignore[arg-type]
                options=req_options if req_options else None,
            )
        )

    async def embed(
        self,
        embedder: str | EmbedderRef | None = None,
        documents: list[Document] | None = None,
        options: dict[str, Any] | None = None,
    ) -> EmbedResponse:
        embedder_name: str
        embedder_config: dict[str, Any] = {}

        if isinstance(embedder, EmbedderRef):
            embedder_name = embedder.name
            embedder_config = embedder.config or {}
            if embedder.version:
                embedder_config['version'] = embedder.version  # Handle version from ref
        elif isinstance(embedder, str):
            embedder_name = embedder
        else:
            # Handle case where embedder is None
            raise ValueError('Embedder must be specified as a string name or an EmbedderRef.')

        # Merge options passed to embed() with config from EmbedderRef
        final_options = {**(embedder_config or {}), **(options or {})}

        embed_action = await self.registry.resolve_action(cast(ActionKind, ActionKind.EMBEDDER), embedder_name)
        if embed_action is None:
            raise ValueError(f'Embedder "{embedder_name}" not found')

        if documents is None:
            raise ValueError('Documents must be specified for embedding.')

        # Document subclasses DocumentData, so this is type-safe at runtime.
        # The type checker doesn't recognize the subclass relationship here.
        return (await embed_action.arun(EmbedRequest(input=documents, options=final_options))).response  # type: ignore[arg-type]

    async def evaluate(
        self,
        evaluator: str | EvaluatorRef | None = None,
        dataset: list[BaseDataPoint] | None = None,
        options: Any | None = None,
        eval_run_id: str | None = None,
    ) -> EvalResponse:
        """Evaluates a dataset using an evaluator.

        Args:
            evaluator: Name or reference of the evaluator to use.
            dataset: Dataset to evaluate.
            options: Evaluation options.
            eval_run_id: Optional ID for the evaluation run.

        Returns:
            The evaluation results.
        """
        evaluator_name: str = ''
        evaluator_config: dict[str, Any] = {}

        if isinstance(evaluator, EvaluatorRef):
            evaluator_name = evaluator.name
            evaluator_config = evaluator.config_schema or {}
        elif isinstance(evaluator, str):
            evaluator_name = evaluator
        else:
            raise ValueError('Evaluator must be specified as a string name or an EvaluatorRef.')

        final_options = {**(evaluator_config or {}), **(options or {})}

        eval_action = await self.registry.resolve_action(cast(ActionKind, ActionKind.EVALUATOR), evaluator_name)
        if eval_action is None:
            raise ValueError(f'Evaluator "{evaluator_name}" not found')

        if not eval_run_id:
            eval_run_id = str(uuid.uuid4())

        if dataset is None:
            raise ValueError('Dataset must be specified for evaluation.')

        return (
            await eval_action.arun(
                EvalRequest(
                    dataset=dataset,
                    options=final_options,
                    eval_run_id=eval_run_id,
                )
            )
        ).response
