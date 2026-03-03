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

This module provides the primary entry point for using Genkit in an asynchronous
environment. The `Genkit` class coordinates plugins, registry, and execution
of AI actions like generation, embedding, and retrieval.

Key features provided by the `Genkit` class:
- **Generation**: Interface for unified model interaction via `generate` and `generate_stream`.
- **Flow Control**: Execution of granular steps with tracing via `run`.
- **Dynamic Extensibility**: On-the-fly creation of tools via `dynamic_tool`.
- **Observability**: Specialized methods for managing trace context and flushing telemetry.
"""

from __future__ import annotations

import asyncio
import signal
import socket
import threading
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from pathlib import Path
from typing import Any, ParamSpec, TypeVar, cast, overload

import anyio
import uvicorn
from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from pydantic import BaseModel
from typing_extensions import Never

from genkit.core._internal import Channel, ensure_async, run_loop
from genkit.core._internal._background import (
    BackgroundAction,
    CancelModelOpFn,
    CheckModelOpFn,
    StartModelOpFn,
    check_operation as check_operation_impl,
    define_background_model as define_background_model_block,
    lookup_background_action,
)
from genkit.core._internal._dap import (
    DapConfig,
    DapFn,
    DynamicActionProvider,
    define_dynamic_action_provider as define_dap_block,
)
from genkit.core._internal._environment import is_dev_environment
from genkit.core._internal._flow import FlowWrapper, define_flow
from genkit.core._internal._logging import get_logger
from genkit.core._internal._registry import Registry
from genkit.core._internal._typing import (
    BaseDataPoint,
    DocumentData,
    Embedding,
    EmbedRequest,
    EvalRequest,
    EvalResponse,
    Message,
    ModelInfo,
    Operation,
    Part,
    RetrieverRequest,
    RetrieverResponse,
    SpanMetadata,
    ToolChoice,
)
from genkit.ai.document import Document
from genkit.ai.embedding import EmbedderFn, EmbedderOptions, EmbedderRef, define_embedder
from genkit.ai.evaluator import (
    BatchEvaluatorFn,
    EvaluatorFn,
    EvaluatorRef,
    define_batch_evaluator,
    define_evaluator,
)
from genkit.ai.formats import built_in_formats
from genkit.ai.formats.types import FormatDef
from genkit.ai.generate import define_generate_action, generate_action
from genkit.ai.model import (
    ModelFn,
    ModelMiddleware,
    ModelResponse,
    ModelResponseChunk,
    define_model,
)
from genkit.ai.model import ModelConfig
from genkit.ai.prompt import (
    ExecutablePrompt,
    PromptConfig,
    define_helper,
    define_partial,
    define_prompt,
    define_schema,
    load_prompt_folder,
    to_generate_action_options,
)
from genkit.ai.reranker import (
    RankedDocument,
    RerankerFn,
    RerankerOptions,
    RerankerRef,
    define_reranker as define_reranker_block,
    rerank as rerank_block,
)
from genkit.ai.resource import (
    ResourceFn,
    ResourceOptions,
    define_resource as define_resource_block,
)
from genkit.ai.retriever import (
    IndexerFn,
    IndexerRef,
    IndexerRequest,
    RetrieverFn,
    RetrieverRef,
    SimpleRetrieverOptions,
    define_indexer_action,
    define_retriever_action,
    define_simple_retriever,
)
from genkit.ai.tools import define_tool
from genkit.core.action import Action, ActionRunContext
from genkit.core.action import ActionKind
from genkit.core.error import GenkitError
from genkit.core.plugin import Plugin
from genkit.core.tracing import run_in_new_span
from genkit._web._reflection import _ReflectionServer, _make_reflection_server, create_reflection_asgi_app

from genkit._web.typing import ServerSpec

from ._runtime import RuntimeManager

logger = get_logger(__name__)

# TypeVars for generic input/output typing
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')
P = ParamSpec('P')
R = TypeVar('R')
T = TypeVar('T')


class Genkit:
    """Genkit asyncio user-facing API.

    This class combines registry functionality (defining models, tools, flows,
    retrievers, etc.) with server infrastructure for the reflection API.
    """

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
                server. If not provided in dev mode, a default will be used.
        """
        self.registry: Registry = Registry()
        self._reflection_server_spec: ServerSpec | None = reflection_server_spec
        self._reflection_ready = threading.Event()
        self._initialize_registry(model, plugins)
        # Ensure the default generate action is registered for async usage.
        define_generate_action(self.registry)
        # In dev mode, start the reflection server immediately in a background
        # daemon thread so it's available regardless of which web framework (or
        # none) the user chooses.
        if is_dev_environment():
            self._start_reflection_background()

        # Load prompts
        load_path = prompt_dir
        if load_path is None:
            default_prompts_path = Path('./prompts')
            if default_prompts_path.is_dir():
                load_path = default_prompts_path

        if load_path:
            load_prompt_folder(self.registry, dir_path=load_path)

    # -------------------------------------------------------------------------
    # Registry methods
    # -------------------------------------------------------------------------

    @overload
    # pyrefly: ignore[inconsistent-overload] - Overloads differentiate async vs sync returns
    def flow(
        self, name: str | None = None, description: str | None = None
    ) -> Callable[[Callable[P, Awaitable[T]]], 'FlowWrapper[P, Awaitable[T], T, Never]']: ...

    @overload
    # pyrefly: ignore[inconsistent-overload] - Overloads differentiate async vs sync returns
    # Overloads appear to overlap because T could be Awaitable[T], but at runtime we
    # distinguish async vs sync functions correctly.
    def flow(  # pyright: ignore[reportOverlappingOverload]
        self, name: str | None = None, description: str | None = None
    ) -> Callable[[Callable[P, T]], 'FlowWrapper[P, T, T, Never]']: ...

    def flow(  # pyright: ignore[reportInconsistentOverload]
        self, name: str | None = None, description: str | None = None
    ) -> Callable[[Callable[P, Awaitable[T]] | Callable[P, T]], 'FlowWrapper[P, Awaitable[T] | T, T, Never]']:
        """Decorator to register a function as a flow.

        Args:
            name: Optional name for the flow. If not provided, uses the
                function name.
            description: Optional description for the flow. If not provided,
                uses the function docstring.

        Returns:
            A decorator function that registers the flow.
        """

        def wrapper(func: Callable[P, Awaitable[T]] | Callable[P, T]) -> 'FlowWrapper[P, Awaitable[T] | T, T, Never]':
            return define_flow(self.registry, func, name, description)

        return wrapper

    def define_helper(self, name: str, fn: Callable[..., Any]) -> None:
        """Define a Handlebars helper function in the registry.

        Args:
            name: The name of the helper function.
            fn: The helper function to register.
        """
        define_helper(self.registry, name, fn)

    def define_partial(self, name: str, source: str) -> None:
        """Define a Handlebars partial template in the registry.

        Args:
            name: The name of the partial.
            source: The template source code for the partial.
        """
        define_partial(self.registry, name, source)

    def define_schema(self, name: str, schema: type[BaseModel]) -> type[BaseModel]:
        """Register a Pydantic schema for use in prompts.

        Args:
            name: The name to register the schema under.
            schema: The Pydantic model class to register.

        Returns:
            The schema that was registered (for convenience).
        """
        define_schema(self.registry, name, schema)
        return schema

    def define_json_schema(self, name: str, json_schema: dict[str, object]) -> dict[str, object]:
        """Register a JSON schema for use in prompts.

        Args:
            name: The name to register the schema under.
            json_schema: The JSON Schema dictionary to register.

        Returns:
            The JSON schema that was registered (for convenience).
        """
        self.registry.register_schema(name, json_schema)
        return json_schema

    def define_dynamic_action_provider(
        self,
        config: DapConfig | str,
        fn: DapFn,
    ) -> DynamicActionProvider:
        """Define and register a Dynamic Action Provider (DAP).

        Args:
            config: DAP configuration (DapConfig) or just a name string.
            fn: Async function that returns actions organized by type.

        Returns:
            The registered DynamicActionProvider.
        """
        return define_dap_block(self.registry, config, fn)

    def tool(
        self, name: str | None = None, description: str | None = None
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Decorator to register a function as a tool.

        Args:
            name: Optional name for the tool. If not provided, uses the function name.
            description: Description for the tool to be passed to the model.

        Returns:
            A decorator function that registers the tool.
        """

        def wrapper(func: Callable[P, T]) -> Callable[P, T]:
            return define_tool(self.registry, func, name, description)

        return wrapper

    def define_retriever(
        self,
        name: str,
        fn: RetrieverFn[Any],
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a retriever action.

        Args:
            name: Name of the retriever.
            fn: Function implementing the retriever behavior.
            config_schema: Optional schema for retriever configuration.
            metadata: Optional metadata for the retriever.
            description: Optional description for the retriever.
        """
        return define_retriever_action(
            self.registry, name, fn, config_schema, metadata, description
        )

    def define_simple_retriever(
        self,
        *,
        options: SimpleRetrieverOptions[R] | str,
        handler: Callable[[DocumentData, Any], list[R] | Awaitable[list[R]]],
        description: str | None = None,
    ) -> Action:
        """Define a simple retriever action.

        Args:
            options: Configuration options for the retriever, or just the name.
            handler: A function that queries a datastore and returns items.
            description: Optional description for the retriever.

        Returns:
            The registered Action for the retriever.
        """
        return define_simple_retriever(self.registry, options, handler, description)

    def define_indexer(
        self,
        name: str,
        fn: IndexerFn[Any],
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define an indexer action.

        Args:
            name: Name of the indexer.
            fn: Function implementing the indexer behavior.
            config_schema: Optional schema for indexer configuration.
            metadata: Optional metadata for the indexer.
            description: Optional description for the indexer.
        """
        return define_indexer_action(
            self.registry, name, fn, config_schema, metadata, description
        )

    def define_reranker(
        self,
        name: str,
        fn: RerankerFn[Any],
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a reranker action.

        Args:
            name: Name of the reranker.
            fn: Function implementing the reranker behavior.
            config_schema: Optional schema for reranker configuration.
            metadata: Optional metadata for the reranker.
            description: Optional description for the reranker.

        Returns:
            The registered Action for the reranker.
        """
        from genkit.core._internal._schema import to_json_schema

        # Extract label and config from metadata
        reranker_label: str = name
        reranker_config_schema: dict[str, object] | None = None

        # Check if metadata has reranker info
        if metadata and 'reranker' in metadata:
            existing = metadata['reranker']
            if isinstance(existing, dict):
                existing_dict = cast(dict[str, object], existing)
                label_val = existing_dict.get('label')
                if isinstance(label_val, str) and label_val:
                    reranker_label = label_val
                opts_val = existing_dict.get('customOptions')
                if isinstance(opts_val, dict):
                    reranker_config_schema = cast(dict[str, object], opts_val)

        # Override with config_schema if provided
        if config_schema:
            reranker_config_schema = to_json_schema(config_schema)

        return define_reranker_block(
            self.registry,
            name=name,
            fn=fn,
            options=RerankerOptions(
                config_schema=reranker_config_schema,
                label=reranker_label,
            ),
            description=description,
        )

    async def rerank(
        self,
        *,
        reranker: str | Action | RerankerRef,
        query: str | DocumentData,
        documents: list[DocumentData],
        options: object | None = None,
    ) -> list[RankedDocument]:
        """Rerank documents based on their relevance to a query.

        Args:
            reranker: The reranker to use.
            query: The query to rank documents against.
            documents: The list of documents to rerank.
            options: Optional configuration options.

        Returns:
            A list of RankedDocument objects sorted by relevance score.
        """
        return await rerank_block(
            self.registry,
            {
                'reranker': reranker,
                'query': query,
                'documents': documents,
                'options': options,
            },
        )

    def define_evaluator(
        self,
        name: str,
        display_name: str,
        definition: str,
        fn: EvaluatorFn[Any],
        is_billed: bool = False,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define an evaluator action.

        Args:
            name: Name of the evaluator.
            display_name: User-visible display name.
            definition: User-visible evaluator definition.
            fn: Function implementing the evaluator behavior.
            is_billed: Whether the evaluator performs any billed actions.
            config_schema: Optional schema for evaluator configuration.
            metadata: Optional metadata for the evaluator.
            description: Optional description for the evaluator.
        """
        return define_evaluator(
            self.registry, name, display_name, definition, fn,
            is_billed, config_schema, metadata, description
        )

    def define_batch_evaluator(
        self,
        name: str,
        display_name: str,
        definition: str,
        fn: BatchEvaluatorFn[Any],
        is_billed: bool = False,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a batch evaluator action.

        Args:
            name: Name of the evaluator.
            display_name: User-visible display name.
            definition: User-visible evaluator definition.
            fn: Function implementing the evaluator behavior.
            is_billed: Whether the evaluator performs any billed actions.
            config_schema: Optional schema for evaluator configuration.
            metadata: Optional metadata for the evaluator.
            description: Optional description for the evaluator.
        """
        return define_batch_evaluator(
            self.registry, name, display_name, definition, fn,
            is_billed, config_schema, metadata, description
        )

    def define_model(
        self,
        name: str,
        fn: ModelFn,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        info: ModelInfo | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a custom model action.

        Args:
            name: Name of the model.
            fn: Function implementing the model behavior.
            config_schema: Optional schema for model configuration.
            metadata: Optional metadata for the model.
            info: Optional ModelInfo for the model.
            description: Optional description for the model.
        """
        return define_model(
            self.registry, name, fn, config_schema, metadata, info, description
        )

    def define_background_model(
        self,
        name: str,
        start: StartModelOpFn,
        check: CheckModelOpFn,
        cancel: CancelModelOpFn | None = None,
        label: str | None = None,
        info: ModelInfo | None = None,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> BackgroundAction:
        """Define a background model for long-running AI operations.

        Args:
            name: Unique name for this background model.
            start: Async function to start the background operation.
            check: Async function to check operation status.
            cancel: Optional async function to cancel operations.
            label: Human-readable label (defaults to name).
            info: Model capability information (ModelInfo).
            config_schema: Schema for model configuration options.
            metadata: Additional metadata for the model.
            description: Description for the model action.

        Returns:
            A BackgroundAction that can be used to start/check/cancel operations.
        """
        return define_background_model_block(
            registry=self.registry,
            name=name,
            start=start,
            check=check,
            cancel=cancel,
            label=label,
            info=info,
            config_schema=config_schema,
            metadata=metadata,
            description=description,
        )

    def define_embedder(
        self,
        name: str,
        fn: EmbedderFn,
        options: EmbedderOptions | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a custom embedder action.

        Args:
            name: Name of the embedder.
            fn: Function implementing the embedder behavior.
            options: Optional options for the embedder.
            metadata: Optional metadata for the embedder.
            description: Optional description for the embedder.
        """
        return define_embedder(
            self.registry, name, fn, options, metadata, description
        )

    def define_format(self, format: FormatDef) -> None:
        """Registers a custom format in the registry.

        Args:
            format: The format to register.
        """
        self.registry.register_value('format', format.name, format)

    # Overload 1: Both input_schema and output_schema typed -> ExecutablePrompt[InputT, OutputT]
    @overload
    def define_prompt(
        self,
        name: str | None = None,
        variant: str | None = None,
        model: str | None = None,
        config: dict[str, object] | ModelConfig | None = None,
        description: str | None = None,
        system: str | Part | list[Part] | Callable[..., Any] | None = None,
        prompt: str | Part | list[Part] | Callable[..., Any] | None = None,
        messages: str | list[Message] | Callable[..., Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_constrained: bool | None = None,
        max_turns: int | None = None,
        return_tool_requests: bool | None = None,
        metadata: dict[str, object] | None = None,
        tools: list[str] | None = None,
        tool_choice: ToolChoice | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | Callable[..., Any] | None = None,
        *,
        input_schema: type[InputT],
        output_schema: type[OutputT],
    ) -> 'ExecutablePrompt[InputT, OutputT]': ...

    # Overload 2: Only input_schema typed -> ExecutablePrompt[InputT, Any]
    @overload
    def define_prompt(
        self,
        name: str | None = None,
        variant: str | None = None,
        model: str | None = None,
        config: dict[str, object] | ModelConfig | None = None,
        description: str | None = None,
        system: str | Part | list[Part] | Callable[..., Any] | None = None,
        prompt: str | Part | list[Part] | Callable[..., Any] | None = None,
        messages: str | list[Message] | Callable[..., Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: dict[str, object] | str | None = None,
        output_constrained: bool | None = None,
        max_turns: int | None = None,
        return_tool_requests: bool | None = None,
        metadata: dict[str, object] | None = None,
        tools: list[str] | None = None,
        tool_choice: ToolChoice | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | Callable[..., Any] | None = None,
        *,
        input_schema: type[InputT],
    ) -> 'ExecutablePrompt[InputT, Any]': ...

    # Overload 3: Only output_schema typed -> ExecutablePrompt[Any, OutputT]
    @overload
    def define_prompt(
        self,
        name: str | None = None,
        variant: str | None = None,
        model: str | None = None,
        config: dict[str, object] | ModelConfig | None = None,
        description: str | None = None,
        input_schema: dict[str, object] | str | None = None,
        system: str | Part | list[Part] | Callable[..., Any] | None = None,
        prompt: str | Part | list[Part] | Callable[..., Any] | None = None,
        messages: str | list[Message] | Callable[..., Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_constrained: bool | None = None,
        max_turns: int | None = None,
        return_tool_requests: bool | None = None,
        metadata: dict[str, object] | None = None,
        tools: list[str] | None = None,
        tool_choice: ToolChoice | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | Callable[..., Any] | None = None,
        *,
        output_schema: type[OutputT],
    ) -> 'ExecutablePrompt[Any, OutputT]': ...

    # Overload 4: Neither typed -> ExecutablePrompt[Any, Any]
    @overload
    def define_prompt(
        self,
        name: str | None = None,
        variant: str | None = None,
        model: str | None = None,
        config: dict[str, object] | ModelConfig | None = None,
        description: str | None = None,
        input_schema: dict[str, object] | str | None = None,
        system: str | Part | list[Part] | Callable[..., Any] | None = None,
        prompt: str | Part | list[Part] | Callable[..., Any] | None = None,
        messages: str | list[Message] | Callable[..., Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: dict[str, object] | str | None = None,
        output_constrained: bool | None = None,
        max_turns: int | None = None,
        return_tool_requests: bool | None = None,
        metadata: dict[str, object] | None = None,
        tools: list[str] | None = None,
        tool_choice: ToolChoice | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | Callable[..., Any] | None = None,
    ) -> 'ExecutablePrompt[Any, Any]': ...

    def define_prompt(
        self,
        name: str | None = None,
        variant: str | None = None,
        model: str | None = None,
        config: dict[str, object] | ModelConfig | None = None,
        description: str | None = None,
        input_schema: type | dict[str, object] | str | None = None,
        system: str | Part | list[Part] | Callable[..., Any] | None = None,
        prompt: str | Part | list[Part] | Callable[..., Any] | None = None,
        messages: str | list[Message] | Callable[..., Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: type | dict[str, object] | str | None = None,
        output_constrained: bool | None = None,
        max_turns: int | None = None,
        return_tool_requests: bool | None = None,
        metadata: dict[str, object] | None = None,
        tools: list[str] | None = None,
        tool_choice: ToolChoice | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | Callable[..., Any] | None = None,
    ) -> 'ExecutablePrompt[Any, Any]':
        """Define a prompt.

        Args:
            name: Optional name for the prompt.
            variant: Optional variant name for the prompt.
            model: Optional model name to use for the prompt.
            config: Optional configuration for the model.
            description: Optional description for the prompt.
            input_schema: Optional schema for the input to the prompt.
            system: Optional system message for the prompt.
            prompt: Optional prompt for the model.
            messages: Optional messages for the model.
            output_format: Optional output format for the prompt.
            output_content_type: Optional output content type for the prompt.
            output_instructions: Optional output instructions for the prompt.
            output_schema: Optional schema for the output from the prompt.
            output_constrained: Optional flag indicating whether the output
                should be constrained.
            max_turns: Optional maximum number of turns for the prompt.
            return_tool_requests: Optional flag indicating whether tool requests
                should be returned.
            metadata: Optional metadata for the prompt.
            tools: Optional list of tools to use for the prompt.
            tool_choice: Optional tool choice for the prompt.
            use: Optional list of model middlewares to use for the prompt.
            docs: Optional list of documents or a callable for grounding.
        """
        return define_prompt(
            self.registry,
            name=name,
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
        )

    # Overload 1: Neither typed -> ExecutablePrompt[Any, Any]
    @overload
    def prompt(
        self,
        name: str,
        variant: str | None = None,
        *,
        input_schema: None = None,
        output_schema: None = None,
    ) -> ExecutablePrompt[Any, Any]: ...

    # Overload 2: Only input_schema typed
    @overload
    def prompt(
        self,
        name: str,
        variant: str | None = None,
        *,
        input_schema: type[InputT],
        output_schema: None = None,
    ) -> ExecutablePrompt[InputT, Any]: ...

    # Overload 3: Only output_schema typed
    @overload
    def prompt(
        self,
        name: str,
        variant: str | None = None,
        *,
        input_schema: None = None,
        output_schema: type[OutputT],
    ) -> ExecutablePrompt[Any, OutputT]: ...

    # Overload 4: Both input_schema and output_schema typed
    @overload
    def prompt(
        self,
        name: str,
        variant: str | None = None,
        *,
        input_schema: type[InputT],
        output_schema: type[OutputT],
    ) -> ExecutablePrompt[InputT, OutputT]: ...

    def prompt(
        self,
        name: str,
        variant: str | None = None,
        *,
        input_schema: type[InputT] | None = None,
        output_schema: type[OutputT] | None = None,
    ) -> ExecutablePrompt[InputT, OutputT] | ExecutablePrompt[Any, Any]:
        """Look up a prompt by name and optional variant.

        Args:
            name: The name of the prompt.
            variant: Optional variant name.
            input_schema: Optional typed input schema (Pydantic model).
            output_schema: Optional typed output schema (Pydantic model).

        Returns:
            An ExecutablePrompt instance.
        """
        return ExecutablePrompt(
            registry=self.registry,
            _name=name,
            variant=variant,
            input_schema=input_schema,
            output_schema=output_schema,
        )

    def define_resource(
        self,
        *,
        fn: 'ResourceFn',
        name: str | None = None,
        uri: str | None = None,
        template: str | None = None,
        description: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Action:
        """Define a resource action.

        Args:
            fn: Function implementing the resource behavior.
            name: Optional name for the resource.
            uri: Optional URI for the resource.
            template: Optional URI template for the resource.
            description: Optional description for the resource.
            metadata: Optional metadata for the resource.

        Returns:
            The registered Action for the resource.
        """
        opts: ResourceOptions = {}
        if name:
            opts['name'] = name
        if uri:
            opts['uri'] = uri
        if template:
            opts['template'] = template
        if description:
            opts['description'] = description
        if metadata:
            opts['metadata'] = metadata

        return define_resource_block(self.registry, opts, fn)

    # -------------------------------------------------------------------------
    # Server infrastructure methods
    # -------------------------------------------------------------------------

    def _start_reflection_background(self) -> None:
        """Start the Dev UI reflection server in a background daemon thread.

        The thread owns its own asyncio event loop so it never conflicts with
        the main thread's loop (whether that's uvicorn, FastAPI, or none).
        Sets ``self._reflection_ready`` once the server is listening.
        """

        def _thread_main() -> None:
            async def _run() -> None:
                sockets: list[socket.socket] | None = None
                spec = self._reflection_server_spec
                if spec is None:
                    # Bind to port 0 to let the OS choose an available port and
                    # pass the socket to uvicorn to avoid a check-then-bind race.
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.bind(('127.0.0.1', 0))
                    sock.listen(2048)
                    host, port = sock.getsockname()
                    spec = ServerSpec(scheme='http', host=host, port=port)
                    self._reflection_server_spec = spec
                    sockets = [sock]

                server = _make_reflection_server(self.registry, spec.host, spec.port, ready=self._reflection_ready)
                async with RuntimeManager(spec, lazy_write=True) as runtime_manager:
                    server_task = asyncio.create_task(server.serve(sockets=sockets))

                    # _ReflectionServer.startup() sets _reflection_ready once uvicorn binds.
                    # Use asyncio.to_thread so we don't block the event loop.
                    await asyncio.to_thread(self._reflection_ready.wait)

                    if server.should_exit:
                        logger.warning(f'Reflection server at {spec.url} failed to start.')
                        return

                    runtime_manager.write_runtime_file()
                    await logger.ainfo(f'Genkit Dev UI reflection server running at {spec.url}')

                    # Keep running until the process exits (daemon thread).
                    await server_task

            asyncio.run(_run())

        t = threading.Thread(target=_thread_main, daemon=True, name='genkit-reflection-server')
        t.start()

    def _initialize_registry(self, model: str | None, plugins: list[Plugin] | None) -> None:
        """Initialize the registry for the Genkit instance.

        Args:
            model: Model name to use.
            plugins: List of plugins to initialize.

        Raises:
            ValueError: If an invalid plugin is provided.

        Returns:
            None
        """
        self.registry.default_model = model
        for fmt in built_in_formats:
            self.define_format(fmt)

        if not plugins:
            logger.warning('No plugins provided to Genkit')
        else:
            for plugin in plugins:
                if isinstance(plugin, Plugin):  # pyright: ignore[reportUnnecessaryIsInstance]
                    self.registry.register_plugin(plugin)
                else:
                    raise ValueError(f'Invalid {plugin=} provided to Genkit: must be of type `genkit.ai.Plugin`')

    def run_main(self, coro: Coroutine[Any, Any, T]) -> T | None:
        """Run the user's main coroutine.

        In development mode (`GENKIT_ENV=dev`), this runs the user's coroutine
        then blocks until Ctrl+C or SIGTERM, keeping the background reflection
        server (started in ``__init__``) alive for the Dev UI.

        In production mode, this simply runs the user's coroutine to completion
        using ``uvloop.run()`` for performance if available, otherwise
        ``asyncio.run()``.

        Args:
            coro: The main coroutine provided by the user.

        Returns:
            The result of the user's coroutine, or None on graceful shutdown.
        """
        if not is_dev_environment():
            logger.info('Running in production mode.')
            return run_loop(coro)

        logger.info('Running in development mode.')

        async def dev_runner() -> T | None:
            user_result: T | None = None
            try:
                user_result = await coro
                logger.debug('User coroutine completed successfully.')
            except Exception:
                logger.exception('User coroutine failed')

            # Block until Ctrl+C (SIGINT handled by anyio) or SIGTERM, keeping
            # the daemon reflection thread alive.
            logger.info('Script done — Dev UI running. Press Ctrl+C to stop.')
            try:
                async with anyio.create_task_group() as tg:

                    async def _handle_sigterm(tg_: anyio.abc.TaskGroup) -> None:  # type: ignore[name-defined]
                        with anyio.open_signal_receiver(signal.SIGTERM) as sigs:
                            async for _ in sigs:
                                tg_.cancel_scope.cancel()
                                return

                    tg.start_soon(_handle_sigterm, tg)
                    await anyio.sleep_forever()
            except anyio.get_cancelled_exc_class():
                pass

            logger.info('Dev UI server stopped.')
            return user_result

        return anyio.run(dev_runner)

    # -------------------------------------------------------------------------
    # Genkit-specific methods (generation, embedding, retrieval, etc.)
    # -------------------------------------------------------------------------

    def _resolve_embedder_name(self, embedder: str | EmbedderRef | None) -> str:
        """Resolve embedder name from string or EmbedderRef.

        Args:
            embedder: The embedder specified as a string name or EmbedderRef.

        Returns:
            The resolved embedder name.

        Raises:
            ValueError: If embedder is not specified or is of invalid type.
        """
        if isinstance(embedder, EmbedderRef):
            return embedder.name
        elif isinstance(embedder, str):
            return embedder
        else:
            raise ValueError('Embedder must be specified as a string name or an EmbedderRef.')

    async def generate(
        self,
        *,
        model: str | None = None,
        prompt: str | Part | list[Part] | None = None,
        system: str | Part | list[Part] | None = None,
        messages: list[Message] | None = None,
        tools: list[str] | None = None,
        return_tool_requests: bool | None = None,
        tool_choice: ToolChoice | None = None,
        tool_responses: list[Part] | None = None,
        config: dict[str, object] | ModelConfig | None = None,
        max_turns: int | None = None,
        context: dict[str, object] | None = None,
        output_schema: type | dict | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_constrained: bool | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[Document] | None = None,
    ) -> ModelResponse[Any]:
        """Generates text or structured data using a language model.

        This function provides a flexible interface for interacting with various
        language models, supporting both simple text generation and more complex
        interactions involving tools and structured conversations.

        Args:
            model: The name of the model to use for generation. If not
                provided, a default model may be used.
            prompt: A single prompt string, a `Part` object, or a list
                of `Part` objects to provide as input to the model.
            system: A system message string, a `Part` object, or a
                list of `Part` objects to provide context or instructions to
                the model, especially for chat-based models.
            messages: A list of `Message` objects representing a
                conversation history.
            tools: A list of tool names (strings) that the model can use.
            return_tool_requests: If `True`, the model will return
                tool requests instead of executing them directly.
            tool_choice: A `ToolChoice` object specifying how the
                model should choose which tool to use.
            tool_responses: Tool response parts corresponding to interrupt tool
                request parts from the most recent model message.
            config: A `ModelConfig` object or a dictionary
                containing configuration parameters for the generation process.
            max_turns: The maximum number of turns in a conversation.
            context: A dictionary containing additional context
                information that can be used during generation.
            output_schema: A Pydantic model class or JSON schema dict for
                structured output.
            output_format: The format to use for the output (e.g., 'json').
            output_content_type: The content type of the output.
            output_instructions: Instructions for formatting the output.
            output_constrained: Whether to constrain the output to the schema.
            use: A list of `ModelMiddleware` functions to apply to the
                generation process.
            docs: A list of documents to be used for grounding.

        Returns:
            A `ModelResponse` object containing the model's response.

        Note:
            For streaming, use `generate_stream()` instead.
        """
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
            middleware=use,
            context=context if context else ActionRunContext._current_context(),  # pyright: ignore[reportPrivateUsage]
        )

    def generate_stream(
        self,
        *,
        model: str | None = None,
        prompt: str | Part | list[Part] | None = None,
        system: str | Part | list[Part] | None = None,
        messages: list[Message] | None = None,
        tools: list[str] | None = None,
        return_tool_requests: bool | None = None,
        tool_choice: ToolChoice | None = None,
        config: dict[str, object] | ModelConfig | None = None,
        max_turns: int | None = None,
        context: dict[str, object] | None = None,
        output_schema: type | dict | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_constrained: bool | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[Document] | None = None,
        timeout: float | None = None,
    ) -> tuple[
        AsyncIterator[ModelResponseChunk],
        asyncio.Future[ModelResponse[Any]],
    ]:
        """Streams generated text or structured data using a language model.

        Args:
            model: The name of the model to use for generation. If not
                provided, a default model may be used.
            prompt: A single prompt string, a `Part` object, or a list
                of `Part` objects to provide as input to the model.
            system: A system message string, a `Part` object, or a
                list of `Part` objects to provide context or instructions to
                the model, especially for chat-based models.
            messages: A list of `Message` objects representing a
                conversation history.
            tools: A list of tool names (strings) that the model can use.
            return_tool_requests: If `True`, the model will return
                tool requests instead of executing them directly.
            tool_choice: A `ToolChoice` object specifying how the
                model should choose which tool to use.
            config: A `ModelConfig` object or a dictionary
                containing configuration parameters for the generation process.
            max_turns: The maximum number of turns in a conversation.
            context: A dictionary containing additional context
                information that can be used during generation.
            output_schema: A Pydantic model class or JSON schema dict for
                structured output.
            output_format: The format to use for the output (e.g., 'json').
            output_content_type: The content type of the output.
            output_instructions: Instructions for formatting the output.
            output_constrained: Whether to constrain the output to the schema.
            use: A list of `ModelMiddleware` functions to apply to the
                generation process.
            docs: A list of documents to be used for grounding.
            timeout: The timeout for the streaming action.

        Returns:
            A tuple of (stream, response_future) where stream is an async
            iterator of chunks and response_future resolves to the final
            ModelResponse.
        """
        stream: Channel[ModelResponseChunk, ModelResponse[Any]] = Channel(timeout=timeout)

        async def _run_generate() -> ModelResponse[Any]:
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
                on_chunk=lambda c: stream.send(c),
                middleware=use,
                context=context if context else ActionRunContext._current_context(),  # pyright: ignore[reportPrivateUsage]
            )

        stream.set_close_future(asyncio.create_task(_run_generate()))

        return stream, stream.closed

    async def retrieve(
        self,
        *,
        retriever: str | RetrieverRef | None = None,
        query: str | DocumentData | None = None,
        options: dict[str, object] | None = None,
    ) -> list[Document]:
        """Retrieves documents based on query.

        Args:
            retriever: Optional retriever name or reference to use.
            query: Text query or a DocumentData containing query text.
            options: Optional retriever-specific options.

        Returns:
            A list of Document objects matching the query.
        """
        retriever_name: str
        retriever_config: dict[str, object] = {}

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

        retrieve_action = await self.registry.resolve_retriever(retriever_name)
        if retrieve_action is None:
            raise ValueError(f'Retriever "{retriever_name}" not found')

        if query is None:
            raise ValueError('Query must be specified for retrieval.')

        response = (
            await retrieve_action.run(
                RetrieverRequest(
                    query=query,
                    options=request_options if request_options else None,
                )
            )
        ).response
        return [Document.from_document_data(doc) for doc in response.documents]

    async def index(
        self,
        *,
        indexer: str | IndexerRef | None = None,
        documents: list[Document] | None = None,
        options: dict[str, object] | None = None,
    ) -> None:
        """Indexes documents.

        Args:
            indexer: Optional indexer name or reference to use.
            documents: Documents to index.
            options: Optional indexer-specific options.
        """
        indexer_name: str
        indexer_config: dict[str, object] = {}

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

        _ = await index_action.run(
            IndexerRequest(
                # Document subclasses DocumentData, so this is type-safe at runtime.
                # list is invariant so list[Document] isn't assignable to list[DocumentData]
                documents=cast(list[DocumentData], documents),
                options=req_options if req_options else None,
            )
        )

    async def embed(
        self,
        *,
        embedder: str | EmbedderRef | None = None,
        content: str | Document | DocumentData | None = None,
        metadata: dict[str, object] | None = None,
        options: dict[str, object] | None = None,
    ) -> list[Embedding]:
        """Embeds a single document or string.

        Generates vector embeddings for a single piece of content using the
        specified embedder. This is the primary method for embedding individual
        items.

        When using an EmbedderRef, the config and version from the ref are
        extracted and merged with any provided options. The merge order is:
        {version, ...config, ...options} (options take precedence).

        Args:
            embedder: Embedder name (e.g., 'googleai/text-embedding-004') or
                an EmbedderRef with configuration.
            content: A single string, Document, or DocumentData to embed.
            metadata: Optional metadata to apply to the document. Only used
                when content is a string.
            options: Optional embedder-specific options (e.g., task_type).

        Returns:
            A list containing the Embedding for the input content.

        Raises:
            ValueError: If embedder is not specified or not found.
            ValueError: If content is not specified.

        Example - Basic string embedding:
            >>> embeddings = await ai.embed(embedder='googleai/text-embedding-004', content='Hello, world!')
            >>> print(len(embeddings[0].embedding))  # Vector dimensions

        Example - With metadata:
            >>> embeddings = await ai.embed(
            ...     embedder='googleai/text-embedding-004',
            ...     content='Product description',
            ...     metadata={'category': 'electronics'},
            ... )

        Example - With embedder options:
            >>> embeddings = await ai.embed(
            ...     embedder='googleai/text-embedding-004',
            ...     content='Search query',
            ...     options={'task_type': 'RETRIEVAL_QUERY'},
            ... )

        Example - Using EmbedderRef:
            >>> ref = create_embedder_ref('googleai/text-embedding-004', config={'task_type': 'CLUSTERING'})
            >>> embeddings = await ai.embed(embedder=ref, content='Text')
        """
        embedder_name = self._resolve_embedder_name(embedder)
        embedder_config: dict[str, object] = {}

        # Extract config and version from EmbedderRef (not done for embed_many per JS behavior)
        if isinstance(embedder, EmbedderRef):
            embedder_config = embedder.config or {}
            if embedder.version:
                embedder_config['version'] = embedder.version  # Handle version from ref

        # Merge options passed to embed() with config from EmbedderRef
        final_options = {**(embedder_config or {}), **(options or {})}

        embed_action = await self.registry.resolve_embedder(embedder_name)
        if embed_action is None:
            raise ValueError(f'Embedder "{embedder_name}" not found')

        if content is None:
            raise ValueError('Content must be specified for embedding.')

        documents = [Document.from_text(content, metadata)] if isinstance(content, str) else [content]

        # Document subclasses DocumentData, so this is type-safe at runtime.
        # list is invariant so list[Document] isn't assignable to list[DocumentData]
        response = (
            await embed_action.run(
                EmbedRequest(
                    input=documents,  # pyright: ignore[reportArgumentType]
                    options=final_options,
                )
            )
        ).response
        return response.embeddings

    async def embed_many(
        self,
        *,
        embedder: str | EmbedderRef | None = None,
        content: list[str] | list[Document] | list[DocumentData] | None = None,
        metadata: dict[str, object] | None = None,
        options: dict[str, object] | None = None,
    ) -> list[Embedding]:
        """Embeds multiple documents or strings in a single batch call.

        Generates vector embeddings for multiple pieces of content in one API
        call. This is more efficient than calling embed() multiple times when
        you have a batch of items to embed.

        Important: Unlike embed(), this method does NOT extract config/version
        from EmbedderRef. It only uses the ref to resolve the embedder name
        and passes options directly. This matches the JS canonical behavior.

        Args:
            embedder: Embedder name (e.g., 'googleai/text-embedding-004') or
                an EmbedderRef.
            content: List of strings, Documents, or DocumentData to embed.
            metadata: Optional metadata to apply to all items. Only used when
                content items are strings.
            options: Optional embedder-specific options.

        Returns:
            List of Embedding objects, one per input item (same order).

        Raises:
            ValueError: If embedder is not specified or not found.
            ValueError: If content is not specified.

        Example - Basic batch embedding:
            >>> embeddings = await ai.embed_many(
            ...     embedder='googleai/text-embedding-004',
            ...     content=['Doc 1', 'Doc 2', 'Doc 3'],
            ... )
            >>> for i, emb in enumerate(embeddings):
            ...     print(f'Doc {i}: {len(emb.embedding)} dims')

        Example - With shared metadata:
            >>> embeddings = await ai.embed_many(
            ...     embedder='googleai/text-embedding-004',
            ...     content=['text1', 'text2'],
            ...     metadata={'batch_id': 'batch-001'},
            ... )

        Example - With options (EmbedderRef config is NOT extracted):
            >>> embeddings = await ai.embed_many(
            ...     embedder='googleai/text-embedding-004',
            ...     content=documents,
            ...     options={'task_type': 'RETRIEVAL_DOCUMENT'},
            ... )
        """
        if content is None:
            raise ValueError('Content must be specified for embedding.')

        # Convert strings to Documents if needed
        documents: list[Document | DocumentData] = [
            Document.from_text(item, metadata) if isinstance(item, str) else item for item in content
        ]

        # Resolve embedder name (JS embedMany does not extract config/version from ref)
        embedder_name = self._resolve_embedder_name(embedder)

        embed_action = await self.registry.resolve_embedder(embedder_name)
        if embed_action is None:
            raise ValueError(f'Embedder "{embedder_name}" not found')

        response = (await embed_action.run(EmbedRequest(input=documents, options=options))).response
        return response.embeddings

    async def evaluate(
        self,
        evaluator: str | EvaluatorRef | None = None,
        dataset: list[BaseDataPoint] | None = None,
        options: dict[str, object] | None = None,
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
        evaluator_config: dict[str, object] = {}

        if isinstance(evaluator, EvaluatorRef):
            evaluator_name = evaluator.name
            evaluator_config = evaluator.config_schema or {}
        elif isinstance(evaluator, str):
            evaluator_name = evaluator
        else:
            raise ValueError('Evaluator must be specified as a string name or an EvaluatorRef.')

        final_options = {**(evaluator_config or {}), **(options or {})}

        eval_action = await self.registry.resolve_evaluator(evaluator_name)
        if eval_action is None:
            raise ValueError(f'Evaluator "{evaluator_name}" not found')

        if not eval_run_id:
            eval_run_id = str(uuid.uuid4())

        if dataset is None:
            raise ValueError('Dataset must be specified for evaluation.')

        return (
            await eval_action.run(
                EvalRequest(
                    dataset=dataset,
                    options=final_options,
                    eval_run_id=eval_run_id,
                )
            )
        ).response

    @staticmethod
    def current_context() -> dict[str, Any] | None:
        """Retrieves the current execution context for the running action.

        This allows tools and other actions to access context data (like auth
        or metadata) passed through the execution chain via ContextVars.
        This provides parity with the JavaScript SDK's context handling.

        Returns:
            The current context dictionary, or None if not running in an action.
        """
        return ActionRunContext._current_context()  # pyright: ignore[reportPrivateUsage]

    def dynamic_tool(
        self,
        *,
        name: str,
        fn: Callable[..., object],
        description: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Action:
        """Creates an unregistered tool action.

        This is useful for creating tools that are passed directly to generate()
        without being registered in the global registry. Dynamic tools behave exactly
        like registered tools but offer more flexibility for runtime-defined logic.

        Args:
            name: The unique name of the tool.
            fn: The function that implements the tool logic.
            description: Optional human-readable description of what the tool does.
            metadata: Optional dictionary of metadata about the tool.

        Returns:
            An Action instance of kind TOOL, configured for dynamic execution.
        """
        tool_meta: dict[str, object] = metadata.copy() if metadata else {}
        tool_meta['type'] = 'tool'
        tool_meta['dynamic'] = True
        return Action(
            kind=ActionKind.TOOL,
            name=name,
            fn=fn,
            description=description,
            metadata=tool_meta,
        )

    async def flush_tracing(self) -> None:
        """Flushes all registered trace processors.

        This ensures all pending spans are exported before the application
        shuts down, preventing loss of telemetry data.
        """
        provider = trace_api.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            await ensure_async(provider.force_flush)()

    async def run(
        self,
        *,
        name: str,
        fn: Callable[[], Awaitable[T]],
        metadata: dict[str, Any] | None = None,
    ) -> T:
        """Runs a function as a discrete step within a trace.

        This method is used to create sub-spans (steps) within a flow or other action.
        Each run step is recorded separately in the trace, making it easier to
        debug and monitor the internal execution of complex flows.

        Args:
            name: The descriptive name of the span/step.
            fn: The async function to execute.
            metadata: Optional metadata to associate with the generated trace span.

        Returns:
            The result of the function execution.

        Raises:
            TypeError: If fn is not a coroutine function.
        """
        import inspect as _inspect

        if not _inspect.iscoroutinefunction(fn):
            raise TypeError('fn must be a coroutine function')

        span_metadata = SpanMetadata(name=name, metadata=metadata)
        with run_in_new_span(span_metadata, labels={'genkit:type': 'flowStep'}) as span:
            try:
                result = await fn()
                span.set_output(result)
                return result
            except Exception:
                # We catch all exceptions here to ensure they are captured by
                # the trace span context manager before being re-raised.
                # The GenkitSpan wrapper (run_in_new_span) handles recording
                # the exception details.
                raise

    async def check_operation(self, operation: Operation) -> Operation:
        """Checks the status of a long-running background operation.

        This method matches JS checkOperation from js/ai/src/check-operation.ts.

        It looks up the background action by the operation's action key and
        calls its check method to get updated status.

        Args:
            operation: The Operation object to check. Must have an action
                field specifying which background model created it.

        Returns:
            An updated Operation object with the current status.

        Raises:
            ValueError: If the operation is missing original request information
                or if the background action cannot be resolved.

        Example:
            >>> # Start a background operation
            >>> response = await ai.generate(model=veo_model, prompt='A cat')
            >>> operation = response.operation
            >>> # Poll until done
            >>> while not operation.done:
            ...     await asyncio.sleep(5)
            ...     operation = await ai.check_operation(operation)
            >>> # Use the result
            >>> print(operation.output)
        """
        return await check_operation_impl(self.registry, operation)

    async def cancel_operation(self, operation: Operation) -> Operation:
        """Cancels a long-running background operation.

        This method attempts to cancel an in-progress operation. Not all
        background models support cancellation.

        If cancellation is not supported, returns the operation unchanged
        (matching JS behavior).

        Args:
            operation: The Operation object to cancel. Must have an action
                field specifying which background model created it.

        Returns:
            An updated Operation object reflecting the cancellation attempt.

        Raises:
            ValueError: If the operation is missing original request information
                or if the background action cannot be resolved.

        Example:
            >>> # Start a background operation
            >>> response = await ai.generate(model=veo_model, prompt='A cat')
            >>> operation = response.operation
            >>> # Cancel it
            >>> operation = await ai.cancel_operation(operation)
        """
        if not operation.action:
            raise ValueError('Provided operation is missing original request information')

        background_action = await lookup_background_action(self.registry, operation.action)
        if background_action is None:
            raise ValueError(f'Failed to resolve background action from original request: {operation.action}')

        return await background_action.cancel(operation)

    async def generate_operation(
        self,
        *,
        model: str | None = None,
        prompt: str | Part | list[Part] | None = None,
        system: str | Part | list[Part] | None = None,
        messages: list[Message] | None = None,
        tools: list[str] | None = None,
        return_tool_requests: bool | None = None,
        tool_choice: ToolChoice | None = None,
        config: dict[str, object] | ModelConfig | None = None,
        max_turns: int | None = None,
        context: dict[str, object] | None = None,
        output_schema: type | dict | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_constrained: bool | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[Document] | None = None,
    ) -> Operation:
        """Generate content using a long-running model and return an Operation.

        This method is for models that support long-running operations (like
        video generation with Veo). It returns an Operation that can be polled
        with check_operation() until completion.

        Note: This is a beta feature. Only models that support long-running
        operations (model.supports.long_running = True) can be used with this
        method.

        The Operation Flow
        ==================

        ┌─────────────────────────────────────────────────────────────────┐
        │                    generate_operation() Flow                     │
        ├─────────────────────────────────────────────────────────────────┤
        │                                                                  │
        │   ┌──────────────────┐                                          │
        │   │ Resolve Model    │                                          │
        │   │ Check supports   │                                          │
        │   │ long_running     │                                          │
        │   └────────┬─────────┘                                          │
        │            │                                                     │
        │      ┌─────┴─────┐                                              │
        │      │           │                                              │
        │      ▼           ▼                                              │
        │   ┌───────┐   ┌───────────────┐                                │
        │   │ Error │   │ Call generate │                                │
        │   │ (no   │   │ Get operation │                                │
        │   │ LRO)  │   └───────┬───────┘                                │
        │   └───────┘           │                                         │
        │                       ▼                                         │
        │              ┌──────────────┐                                   │
        │              │  Operation   │                                   │
        │              │  done=False  │ ──► poll with check_operation()  │
        │              │  id=...      │                                   │
        │              └──────────────┘                                   │
        │                                                                  │
        └─────────────────────────────────────────────────────────────────┘

        Args:
            model: The model to use for generation (must support long_running).
            prompt: The prompt text or parts.
            system: System message for the model.
            messages: Conversation history.
            tools: Tool names available to the model.
            return_tool_requests: Whether to return tool requests.
            tool_choice: How the model should choose tools.
            config: Generation configuration.
            max_turns: Maximum conversation turns.
            context: Additional context data.
            output_schema: A Pydantic model class or JSON schema dict.
            output_format: Output format (e.g., 'json').
            output_content_type: Output content type.
            output_instructions: Output formatting instructions.
            output_constrained: Whether to constrain output to schema.
            use: Middleware to apply.
            docs: Documents for grounding.

        Returns:
            An Operation object for tracking the long-running generation.

        Raises:
            GenkitError: If the model doesn't support long-running operations.
            GenkitError: If the model didn't return an operation.

        Example:
            >>> # Generate video with Veo (long-running operation)
            >>> operation = await ai.generate_operation(
            ...     model='googleai/veo-2.0-generate-001',
            ...     prompt='A banana riding a bicycle.',
            ... )
            >>> # Poll until done
            >>> while not operation.done:
            ...     await asyncio.sleep(5)
            ...     operation = await ai.check_operation(operation)
            >>> # Access result
            >>> print(operation.output)
        """
        # Resolve the model and check for long_running support
        resolved_model = model or self.registry.default_model
        if not resolved_model:
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message='No model specified for generate_operation.',
            )

        model_action = await self.registry.resolve_action(ActionKind.MODEL, resolved_model)
        if not model_action:
            raise GenkitError(
                status='NOT_FOUND',
                message=f"Model '{resolved_model}' not found.",
            )

        # Check if model supports long-running operations
        model_info = model_action.metadata.get('model') if model_action.metadata else None
        supports_long_running = False
        if model_info:
            # model_info can be ModelInfo or dict
            if hasattr(model_info, 'supports'):
                supports_attr = getattr(model_info, 'supports', None)
                if supports_attr:
                    supports_long_running = getattr(supports_attr, 'long_running', False)
            elif isinstance(model_info, dict):
                # Cast to dict[str, Any] for type checker
                model_info_dict: dict[str, Any] = model_info  # type: ignore[assignment]
                supports = model_info_dict.get('supports')
                if isinstance(supports, dict):
                    supports_long_running = bool(supports.get('longRunning', False))

        if not supports_long_running:
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message=f"Model '{model_action.name}' does not support long running operations.",
            )

        # Call generate
        response = await self.generate(
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
            output_schema=output_schema,
            output_format=output_format,
            output_content_type=output_content_type,
            output_instructions=output_instructions,
            output_constrained=output_constrained,
            use=use,
            docs=docs,
        )

        # Extract operation from response
        if not hasattr(response, 'operation') or not response.operation:
            raise GenkitError(
                status='FAILED_PRECONDITION',
                message=f"Model '{model_action.name}' did not return an operation.",
            )

        return response.operation


# Keep GenkitRegistry as an alias for backward compatibility
GenkitRegistry = Genkit
