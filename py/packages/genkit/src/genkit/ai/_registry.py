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

"""Genkit maintains a registry of all actions.

An **action** is a remote callable function that uses typed-JSON RPC over HTTP
to allow the framework and users to define custom AI functionality.  There are
several kinds of action defined by [ActionKind][genkit.core.action.ActionKind]:

| Kind          | Description |
|---------------|-------------|
| `'chat-llm'`  | Chat LLM    |
| `'custom'`    | Custom      |
| `'embedder'`  | Embedder    |
| `'evaluator'` | Evaluator   |
| `'flow'`      | Flow        |
| `'indexer'`   | Indexer     |
| `'model'`     | Model       |
| `'prompt'`    | Prompt      |
| `'resource'`  | Resource    |
| `'retriever'` | Retriever   |
| `'text-llm'`  | Text LLM    |
| `'tool'`      | Tool        |
| `'util'`      | Utility     |
"""

import asyncio
import inspect
import traceback
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, Generic, ParamSpec, TypeVar, cast

from genkit.aio import ensure_async

if TYPE_CHECKING:
    from genkit.blocks.prompt import ExecutablePrompt
    from genkit.blocks.resource import FlexibleResourceFn, ResourceOptions

import structlog
from pydantic import BaseModel

from genkit.blocks.embedding import EmbedderFn, EmbedderOptions
from genkit.blocks.evaluator import BatchEvaluatorFn, EvaluatorFn
from genkit.blocks.formats.types import FormatDef
from genkit.blocks.model import ModelFn, ModelMiddleware
from genkit.blocks.prompt import (
    define_helper,
    define_partial,
    define_prompt,
    define_schema,
)
from genkit.blocks.reranker import (
    RankedDocument,
    RerankerFn,
    RerankerOptions,
    RerankerRef,
    define_reranker as define_reranker_block,
    rerank as rerank_block,
)
from genkit.blocks.retriever import IndexerFn, RetrieverFn
from genkit.blocks.tools import ToolRunContext
from genkit.codec import dump_dict
from genkit.core.action import Action, ActionResponse
from genkit.core.action.types import ActionKind
from genkit.core.registry import Registry
from genkit.core.schema import to_json_schema
from genkit.core.tracing import run_in_new_span
from genkit.core.typing import (
    DocumentData,
    DocumentPart,
    EvalFnResponse,
    EvalRequest,
    EvalResponse,
    EvalStatusEnum,
    GenerationCommonConfig,
    Message,
    ModelInfo,
    Part,
    RetrieverResponse,
    Score,
    SpanMetadata,
    ToolChoice,
)

EVALUATOR_METADATA_KEY_DISPLAY_NAME = 'evaluatorDisplayName'
EVALUATOR_METADATA_KEY_DEFINITION = 'evaluatorDefinition'
EVALUATOR_METADATA_KEY_IS_BILLED = 'evaluatorIsBilled'

logger = structlog.get_logger(__name__)
P = ParamSpec('P')
R = TypeVar('R')
T = TypeVar('T')


def get_func_description(func: Callable, description: str | None = None) -> str:
    """Get the description of a function.

    Args:
        func: The function to get the description of.
        description: The description to use if the function docstring is
            empty.
    """
    if description is not None:
        return description
    if func.__doc__ is not None:
        return func.__doc__
    return ''


R = TypeVar('R')


class SimpleRetrieverOptions(BaseModel, Generic[R]):
    """Configuration options for `define_simple_retriever`.

    This class defines how items returned by a simple retriever handler are
    mapped into Genkit `DocumentData` objects.

    Attributes:
        name: The unique name of the retriever.
        content: Specifies how to extract content from the returned items.
            Can be a string key (for dict items) or a callable that transforms the item.
        metadata: Specifies how to extract metadata from the returned items.
            Can be a list of keys (for dict items) or a callable that transforms the item.
        config_schema: Optional Pydantic schema or JSON schema for retriever configuration.
    """

    name: str
    content: str | Callable[[R], str | list[DocumentPart]] | None = None
    metadata: list[str] | Callable[[R], dict[str, Any]] | None = None
    config_schema: type[BaseModel] | dict[str, Any] | None = None


def _item_to_document(item: R, options: SimpleRetrieverOptions[R]) -> DocumentData:
    """Internal helper to convert a raw item to a Genkit DocumentData."""
    from genkit.blocks.document import Document

    if isinstance(item, (Document, DocumentData)):
        return item

    if isinstance(item, str):
        return Document.from_text(item)

    if callable(options.content):
        transformed = options.content(item)
        if isinstance(transformed, str):
            return Document.from_text(transformed)
        else:
            # transformed is list[DocumentPart]
            return DocumentData(content=cast(list[DocumentPart], transformed))

    if isinstance(options.content, str) and isinstance(item, dict):
        return Document.from_text(str(item[options.content]))

    if options.content is None and isinstance(item, str):
        return Document.from_text(item)

    raise ValueError(f'Cannot convert item to document without content option. Item: {item}')


def _item_to_metadata(item: R, options: SimpleRetrieverOptions[R]) -> dict[str, Any] | None:
    """Internal helper to extract metadata from a raw item for a Document."""
    if isinstance(item, str):
        return None

    if isinstance(options.metadata, list) and isinstance(item, dict):
        return {str(k): item[k] for k in options.metadata if k in item}

    if callable(options.metadata):
        return options.metadata(item)

    if options.metadata is None and isinstance(item, dict):
        out = cast(dict[str, Any], item.copy())
        if isinstance(options.content, str) and options.content in out:
            del out[options.content]
        return out

    return None


class GenkitRegistry:
    """User-facing API for interacting with Genkit registry."""

    def __init__(self) -> None:
        """Initialize the Genkit registry."""
        self.registry: Registry = Registry()

    def flow(
        self, name: str | None = None, description: str | None = None
    ) -> Callable[[Callable[P, T]], 'FlowWrapper[P, T]']:
        """Decorator to register a function as a flow.

        Args:
            name: Optional name for the flow. If not provided, uses the
                function name.
            description: Optional description for the flow. If not provided,
                uses the function docstring.

        Returns:
            A decorator function that registers the flow.
        """

        def wrapper(func: Callable[P, T]) -> 'FlowWrapper[P, T]':
            """Register the decorated function as a flow.

            Args:
                func: The function to register as a flow.

            Returns:
                The wrapped function that executes the flow.
            """
            flow_name = name if name is not None else getattr(func, '__name__', 'unnamed_flow')
            flow_description = get_func_description(func, description)
            action = self.registry.register_action(
                name=flow_name,
                kind=cast(ActionKind, ActionKind.FLOW),
                fn=func,
                description=flow_description,
                span_metadata={'genkit:metadata:flow:name': flow_name},
            )

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:  # noqa: ANN401
                """Asynchronous wrapper for the flow function.

                Args:
                    *args: Positional arguments to pass to the flow function.
                    **kwargs: Keyword arguments to pass to the flow function.

                Returns:
                    The response from the flow function.
                """
                # Flows accept at most one input argument
                input_arg = args[0] if args else None
                return cast(T, (await action.arun(input_arg)).response)

            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                """Synchronous wrapper for the flow function.

                Args:
                    *args: Positional arguments to pass to the flow function.
                    **kwargs: Keyword arguments to pass to the flow function.

                Returns:
                    The response from the flow function.
                """
                # Flows accept at most one input argument
                input_arg = args[0] if args else None
                return cast(T, action.run(input_arg).response)

            return FlowWrapper(
                fn=cast(Callable[P, T], async_wrapper if action.is_async else sync_wrapper),
                action=action,
            )

        return wrapper

    def define_helper(self, name: str, fn: Callable) -> None:
        """Define a Handlebars helper function in the registry.

        Args:
            name: The name of the helper function.
            fn: The helper function to register.
        """
        define_helper(self.registry, name, fn)

    def define_partial(self, name: str, source: str) -> None:
        """Define a Handlebars partial template in the registry.

        Partials are reusable template fragments that can be included
        in other prompts using {{>partialName}} syntax.

        Args:
            name: The name of the partial.
            source: The template source code for the partial.
        """
        define_partial(self.registry, name, source)

    def define_schema(self, name: str, schema: type) -> type:
        """Register a Pydantic schema for use in prompts.

        Schemas registered with this method can be referenced by name in
        .prompt files using the `output.schema` field.

        Args:
            name: The name to register the schema under.
            schema: The Pydantic model class to register.

        Returns:
            The schema that was registered (for convenience).

        Example:
            ```python
            RecipeSchema = ai.define_schema('Recipe', Recipe)
            ```

            Then in a .prompt file:
            ```yaml
            output:
              schema: Recipe
            ```
        """
        define_schema(self.registry, name, schema)
        return schema

    def tool(
        self, name: str | None = None, description: str | None = None
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Decorator to register a function as a tool.

        Args:
            name: Optional name for the flow. If not provided, uses the function
                name.
            description: Description for the tool to be passed to the model;
                if not provided, uses the function docstring.

        Returns:
            A decorator function that registers the tool.
        """

        def wrapper(func: Callable[P, T]) -> Callable[P, T]:
            """Register the decorated function as a tool.

            Args:
                func: The function to register as a tool.

            Returns:
                The wrapped function that executes the tool.
            """
            tool_name = name if name is not None else getattr(func, '__name__', 'unnamed_tool')
            tool_description = get_func_description(func, description)

            input_spec = inspect.getfullargspec(func)

            def tool_fn_wrapper(*args: Any) -> Any:  # noqa: ANN401
                match len(input_spec.args):
                    case 0:
                        return func()
                    case 1:
                        return func(args[0])
                    case 2:
                        return func(args[0], ToolRunContext(args[1]))  # type: ignore[arg-type]
                    case _:
                        raise ValueError('tool must have 0-2 args...')

            action = self.registry.register_action(
                name=tool_name,
                kind=cast(ActionKind, ActionKind.TOOL),
                description=tool_description,
                fn=tool_fn_wrapper,
                metadata_fn=func,
            )

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:  # noqa: ANN401
                """Asynchronous wrapper for the tool function.

                Args:
                    *args: Positional arguments to pass to the tool function.
                    **kwargs: Keyword arguments to pass to the tool function.

                Returns:
                    The response from the tool function.
                """
                return (await action.arun(*args, **kwargs)).response  # type: ignore[arg-type]

            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:  # noqa: ANN401
                """Synchronous wrapper for the tool function.

                Args:
                    *args: Positional arguments to pass to the tool function.
                    **kwargs: Keyword arguments to pass to the tool function.

                Returns:
                    The response from the tool function.
                """
                return action.run(*args, **kwargs).response  # type: ignore[arg-type]

            return cast(Callable[P, T], async_wrapper if action.is_async else sync_wrapper)

        return wrapper

    def define_retriever(
        self,
        name: str,
        fn: RetrieverFn,
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
        retriever_meta = metadata if metadata else {}
        if 'retriever' not in retriever_meta:
            retriever_meta['retriever'] = {}
        if 'label' not in retriever_meta['retriever'] or not retriever_meta['retriever']['label']:
            retriever_meta['retriever']['label'] = name
        if config_schema:
            retriever_meta['retriever']['customOptions'] = to_json_schema(config_schema)

        retriever_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=cast(ActionKind, ActionKind.RETRIEVER),
            fn=fn,
            metadata=retriever_meta,
            description=retriever_description,
        )

    def define_simple_retriever(
        self,
        options: SimpleRetrieverOptions[R] | str,
        handler: Callable[[DocumentData, Any], list[R] | Awaitable[list[R]]],
        description: str | None = None,
    ) -> Action:
        """Define a simple retriever action.

        A simple retriever makes it easy to map existing data into documents
        that can be used for prompt augmentation.

        Args:
            options: Configuration options for the retriever, or just the name.
            handler: A function that queries a datastore and returns items
                from which to extract documents.
            description: Optional description for the retriever.

        Returns:
            The registered Action for the retriever.
        """
        if isinstance(options, str):
            options = SimpleRetrieverOptions(name=options)

        from genkit.blocks.document import Document

        async def retriever_fn(query: Document, options_obj: Any) -> RetrieverResponse:  # noqa: ANN401

            items = await ensure_async(handler)(query, options_obj)
            docs = []
            for item in items:
                doc = _item_to_document(item, options)
                if not isinstance(item, str):
                    doc.metadata = _item_to_metadata(item, options)
                docs.append(doc)
            return RetrieverResponse(documents=docs)

        return self.define_retriever(
            name=options.name,
            fn=retriever_fn,
            config_schema=options.config_schema,
            description=description,
        )

    def define_indexer(
        self,
        name: str,
        fn: IndexerFn,
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
        indexer_meta = metadata if metadata else {}

        if 'indexer' not in indexer_meta:
            indexer_meta['indexer'] = {}
        if 'label' not in indexer_meta['indexer'] or not indexer_meta['indexer']['label']:
            indexer_meta['indexer']['label'] = name
        if config_schema:
            indexer_meta['indexer']['customOptions'] = to_json_schema(config_schema)

        indexer_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=cast(ActionKind, ActionKind.INDEXER),
            fn=fn,
            metadata=indexer_meta,
            description=indexer_description,
        )

    def define_reranker(
        self,
        name: str,
        fn: RerankerFn,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a reranker action.

        Rerankers reorder documents based on their relevance to a query.
        They are commonly used in RAG pipelines to improve retrieval quality.

        Args:
            name: Name of the reranker.
            fn: Function implementing the reranker behavior. Should accept
                (query_doc, documents, options) and return RerankerResponse.
            config_schema: Optional schema for reranker configuration.
            metadata: Optional metadata for the reranker.
            description: Optional description for the reranker.

        Returns:
            The registered Action for the reranker.

        Example:
            >>> async def my_reranker(query, docs, options):
            ...     # Score documents based on relevance to query
            ...     scored = [(doc, compute_score(query, doc)) for doc in docs]
            ...     scored.sort(key=lambda x: x[1], reverse=True)
            ...     return RerankerResponse(documents=[...])
            >>> ai.define_reranker('my-reranker', my_reranker)
        """
        # Extract label and config from metadata
        reranker_label: str = name
        reranker_config_schema: dict[str, object] | None = None

        # Check if metadata has reranker info
        if metadata and 'reranker' in metadata:
            existing = metadata['reranker']
            if isinstance(existing, dict):
                if 'label' in existing and existing['label']:
                    label_val = existing['label']
                    if isinstance(label_val, str):
                        reranker_label = label_val
                if 'customOptions' in existing:
                    opts_val = existing['customOptions']
                    if isinstance(opts_val, dict):
                        reranker_config_schema = opts_val

        # Override with config_schema if provided
        if config_schema:
            reranker_config_schema = to_json_schema(config_schema)

        reranker_description = get_func_description(fn, description)
        return define_reranker_block(
            self.registry,
            name=name,
            fn=fn,
            options=RerankerOptions(
                config_schema=reranker_config_schema,
                label=reranker_label,
            ),
            description=reranker_description,
        )

    async def rerank(
        self,
        reranker: str | Action | RerankerRef,
        query: str | DocumentData,
        documents: list[DocumentData],
        options: object | None = None,
    ) -> list[RankedDocument]:
        """Rerank documents based on their relevance to a query.

        This method takes a query and a list of documents, and returns the
        documents reordered by relevance as determined by the specified reranker.

        Args:
            reranker: The reranker to use - can be a name string, Action, or RerankerRef.
            query: The query to rank documents against - can be a string or DocumentData.
            documents: The list of documents to rerank.
            options: Optional configuration options for this rerank call.

        Returns:
            A list of RankedDocument objects sorted by relevance score.

        Raises:
            ValueError: If the reranker cannot be resolved.

        Example:
            >>> ranked_docs = await ai.rerank(
            ...     reranker='my-reranker',
            ...     query='What is machine learning?',
            ...     documents=[doc1, doc2, doc3],
            ... )
            >>> for doc in ranked_docs:
            ...     print(f'Score: {doc.score}, Text: {doc.text()}')
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
        fn: EvaluatorFn,
        is_billed: bool = False,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define an evaluator action.

        This action runs the callback function on the every sample of
        the input dataset.

        Args:
            name: Name of the evaluator.
            fn: Function implementing the evaluator behavior.
            display_name: User-visible display name
            definition: User-visible evaluator definition
            is_billed: Whether the evaluator performs any billed actions
                        (paid  APIs, LLMs etc.)
            config_schema: Optional schema for evaluator configuration.
            metadata: Optional metadata for the evaluator.
            description: Optional description for the evaluator.
        """
        evaluator_meta = metadata if metadata else {}
        if 'evaluator' not in evaluator_meta:
            evaluator_meta['evaluator'] = {}
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_DEFINITION] = definition
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_DISPLAY_NAME] = display_name
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_IS_BILLED] = is_billed
        if 'label' not in evaluator_meta['evaluator'] or not evaluator_meta['evaluator']['label']:
            evaluator_meta['evaluator']['label'] = name
        if config_schema:
            evaluator_meta['evaluator']['customOptions'] = to_json_schema(config_schema)

        evaluator_description = get_func_description(fn, description)

        async def eval_stepper_fn(req: EvalRequest) -> EvalResponse:
            eval_responses: list[EvalFnResponse] = []
            for index in range(len(req.dataset)):
                datapoint = req.dataset[index]
                if datapoint.test_case_id is None:
                    datapoint.test_case_id = str(uuid.uuid4())
                span_metadata = SpanMetadata(
                    name=f'Test Case {datapoint.test_case_id}',
                    metadata={'evaluator:evalRunId': req.eval_run_id},
                )
                try:
                    # Try to run with tracing, but fallback if tracing infrastructure fails
                    # (e.g., in environments with NonRecordingSpans like pre-commit)
                    try:
                        with run_in_new_span(span_metadata, labels={'genkit:type': 'evaluator'}) as span:
                            span_id = span.span_id
                            trace_id = span.trace_id
                            try:
                                span.set_input(datapoint)
                                test_case_output = await fn(datapoint, req.options)
                                test_case_output.span_id = span_id
                                test_case_output.trace_id = trace_id
                                span.set_output(test_case_output)
                                eval_responses.append(test_case_output)
                            except Exception as e:
                                logger.debug(f'eval_stepper_fn error: {str(e)}')
                                logger.debug(traceback.format_exc())
                                evaluation = Score(
                                    error=f'Evaluation of test case {datapoint.test_case_id} failed: \n{str(e)}',
                                    status=cast(EvalStatusEnum, EvalStatusEnum.FAIL),
                                )
                                eval_responses.append(
                                    # The ty type checker only recognizes aliases, so we use them
                                    # to pass both ty check and runtime validation.
                                    EvalFnResponse(
                                        span_id=span_id,
                                        trace_id=trace_id,
                                        test_case_id=datapoint.test_case_id,
                                        evaluation=evaluation,
                                    )
                                )
                                # Raise to mark span as failed
                                raise e
                    except (AttributeError, UnboundLocalError):
                        # Fallback: run without span
                        try:
                            test_case_output = await fn(datapoint, req.options)
                            eval_responses.append(test_case_output)
                        except Exception as e:
                            logger.debug(f'eval_stepper_fn error: {str(e)}')
                            logger.debug(traceback.format_exc())
                            evaluation = Score(
                                error=f'Evaluation of test case {datapoint.test_case_id} failed: \n{str(e)}',
                                status=cast(EvalStatusEnum, EvalStatusEnum.FAIL),
                            )
                            eval_responses.append(
                                EvalFnResponse(
                                    test_case_id=datapoint.test_case_id,
                                    evaluation=evaluation,
                                )
                            )
                except Exception:
                    # Continue to process other points
                    continue
            return EvalResponse(eval_responses)

        return self.registry.register_action(
            name=name,
            kind=cast(ActionKind, ActionKind.EVALUATOR),
            fn=eval_stepper_fn,
            metadata=evaluator_meta,
            description=evaluator_description,
        )

    def define_batch_evaluator(
        self,
        name: str,
        display_name: str,
        definition: str,
        fn: BatchEvaluatorFn,
        is_billed: bool = False,
        config_schema: type[BaseModel] | dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
        description: str | None = None,
    ) -> Action:
        """Define a batch evaluator action.

        This action runs the callback function on the entire dataset.

        Args:
            name: Name of the evaluator.
            fn: Function implementing the evaluator behavior.
            display_name: User-visible display name
            definition: User-visible evaluator definition
            is_billed: Whether the evaluator performs any billed actions
                        (paid  APIs, LLMs etc.)
            config_schema: Optional schema for evaluator configuration.
            metadata: Optional metadata for the evaluator.
            description: Optional description for the evaluator.
        """
        evaluator_meta = metadata if metadata else {}
        if 'evaluator' not in evaluator_meta:
            evaluator_meta['evaluator'] = {}
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_DEFINITION] = definition
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_DISPLAY_NAME] = display_name
        evaluator_meta['evaluator'][EVALUATOR_METADATA_KEY_IS_BILLED] = is_billed
        if 'label' not in evaluator_meta['evaluator'] or not evaluator_meta['evaluator']['label']:
            evaluator_meta['evaluator']['label'] = name
        if config_schema:
            evaluator_meta['evaluator']['customOptions'] = to_json_schema(config_schema)

        evaluator_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=cast(ActionKind, ActionKind.EVALUATOR),
            fn=fn,
            metadata=evaluator_meta,
            description=evaluator_description,
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
        # Build model options dict
        model_options: dict[str, object] = {}

        # Start with info if provided
        if info:
            model_info_dict = dump_dict(info)
            if isinstance(model_info_dict, dict):
                for key, value in model_info_dict.items():
                    if isinstance(key, str):
                        model_options[key] = value

        # Check if metadata has model info
        if metadata and 'model' in metadata:
            existing = metadata['model']
            if isinstance(existing, dict):
                for key, value in existing.items():
                    if key not in model_options:  # Don't override info
                        model_options[key] = value

        # Default label to name if not set
        if 'label' not in model_options or not model_options['label']:
            model_options['label'] = name

        # Add config schema if provided
        if config_schema:
            model_options['customOptions'] = to_json_schema(config_schema)

        # Build the final metadata dict
        model_meta: dict[str, object] = metadata.copy() if metadata else {}
        model_meta['model'] = model_options

        model_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=cast(ActionKind, ActionKind.MODEL),
            fn=fn,
            metadata=model_meta,
            description=model_description,
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
            name: Name of the model.
            fn: Function implementing the embedder behavior.
            options: Optional options for the embedder.
            metadata: Optional metadata for the model.
            description: Optional description for the embedder.
        """
        embedder_meta: dict[str, object] = metadata or {}
        if 'embedder' not in embedder_meta:
            embedder_meta['embedder'] = {}

        if options:
            if options.label:
                embedder_meta['embedder']['label'] = options.label
            if options.dimensions:
                embedder_meta['embedder']['dimensions'] = options.dimensions
            if options.supports:
                embedder_meta['embedder']['supports'] = options.supports.model_dump(exclude_none=True, by_alias=True)
            if options.config_schema:
                embedder_meta['embedder']['customOptions'] = to_json_schema(options.config_schema)

        embedder_description = get_func_description(fn, description)
        return self.registry.register_action(
            name=name,
            kind=cast(ActionKind, ActionKind.EMBEDDER),
            fn=fn,
            metadata=embedder_meta,
            description=embedder_description,
        )

    def define_format(self, format: FormatDef) -> None:
        """Registers a custom format in the registry.

        Args:
            format: The format to register.
        """
        self.registry.register_value('format', format.name, format)

    def define_prompt(
        self,
        name: str | None = None,
        variant: str | None = None,
        model: str | None = None,
        config: GenerationCommonConfig | dict[str, object] | None = None,
        description: str | None = None,
        input_schema: type | dict[str, object] | str | None = None,
        system: str | Part | list[Part] | Callable | None = None,
        prompt: str | Part | list[Part] | Callable | None = None,
        messages: str | list[Message] | Callable | None = None,
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
        docs: list[DocumentData] | Callable | None = None,
    ) -> 'ExecutablePrompt':
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
            docs: Optional list of documents or a callable to be used for grounding.
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

    def prompt(
        self,
        name: str,
        variant: str | None = None,
    ) -> 'ExecutablePrompt':
        """Look up a prompt by name and optional variant.

        This matches the JavaScript prompt() function behavior.

        Can look up prompts that were:
        1. Defined programmatically using define_prompt()
        2. Loaded from .prompt files using load_prompt_folder()

        Args:
            name: The name of the prompt.
            variant: Optional variant name.

        Returns:
            An ExecutablePrompt instance.
        """
        from genkit.blocks.prompt import ExecutablePrompt

        return ExecutablePrompt(
            registry=self.registry,
            _name=name,
            variant=variant,
        )

    def define_resource(
        self,
        opts: 'ResourceOptions | None' = None,
        fn: 'FlexibleResourceFn | None' = None,
        *,
        name: str | None = None,
        uri: str | None = None,
        template: str | None = None,
        description: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Action:
        """Define a resource action.

        Args:
            opts: Options defining the resource (e.g. uri, template, name).
            fn: Function implementing the resource behavior.
            name: Optional name for the resource.
            uri: Optional URI for the resource.
            template: Optional URI template for the resource.
            description: Optional description for the resource.
            metadata: Optional metadata for the resource.

        Returns:
            The registered Action for the resource.
        """
        from genkit.blocks.resource import (
            define_resource as define_resource_block,
        )

        if fn is None:
            raise ValueError('A function `fn` must be provided to define a resource.')
        if opts is None:
            opts = {}
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


class FlowWrapper(Generic[P, T]):
    """A wapper for flow functions to add `stream` method.

    This class wraps a flow function and provides a `stream` method for
    asynchronous execution.
    """

    def __init__(self, fn: Callable[P, T], action: Action) -> None:
        """Initialize the FlowWrapper.

        Args:
            fn: The function to wrap.
            action: The action to wrap.
        """
        self._fn = fn
        self._action = action

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> T:
        """Call the wrapped function.

        Args:
            *args: Positional arguments to pass to the function.
            **kwds: Keyword arguments to pass to the function.

        Returns:
            The result of the function call.
        """
        return self._fn(*args, **kwds)

    def stream(
        self,
        input: object = None,
        context: dict[str, object] | None = None,
        telemetry_labels: dict[str, object] | None = None,
        timeout: float | None = None,
    ) -> tuple[
        AsyncIterator[object],  # noqa: ANN401
        asyncio.Future[ActionResponse],
    ]:
        """Run the flow and return an async iterator of the results.

        Args:
            input: The input to the action.
            context: The context to pass to the action.
            telemetry_labels: The telemetry labels to pass to the action.
            timeout: The timeout for the streaming action.

        Returns:
            A tuple containing:
            - An AsyncIterator of the chunks from the action.
            - An asyncio.Future that resolves to the final result of the action.
        """
        return self._action.stream(input=input, context=context, telemetry_labels=telemetry_labels, timeout=timeout)
