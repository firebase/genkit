# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""User-facing API for Genkit.

To use Genkit in your application, construct an instance of the `Genkit`
class while customizing it with any plugins, models, and tooling.  Then use the
instance to define application flows.

??? example "Examples"

    === "Chat bot"

        ```python
        # TODO
        ai = Genkit(...)

        @ai.flow()
        async def foo(...):
            await ...
        ```

    === "Structured Output"


        ```python
        # TODO
        ai = Genkit(...)

        @ai.flow()
        async def foo(...):
            await ...
        ```

    === "Tool Calling"


        ```python
        # TODO
        ai = Genkit(...)

        @ai.flow()
        async def foo(...):
            await ...
        ```

## Operations

The `Genkit` class defines the following methods to allow users to generate
content, define flows, define formats, etc.

| Category         | Method                                                                       | Description                          |
|------------------|------------------------------------------------------------------------------|--------------------------------------|
| **AI**           | [`generate()`][genkit.veneer.veneer.Genkit.generate]                         | Generates content.                   |
|                  | [`generate_stream()`][genkit.veneer.veneer.Genkit.generate_stream]           | Generates a stream of content.       |
|                  | [`embed()`][genkit.veneer.veneer.Genkit.embed]                               | Calculates embeddings for documents. |
| **Registration** | [`define_embedder()`][genkit.veneer.registry.GenkitRegistry.define_embedder] | Defines and registers an embedder.   |
|                  | [`define_format()`][genkit.veneer.registry.GenkitRegistry.define_format]     | Defines and registers a format.      |
|                  | [`define_model()`][genkit.veneer.registry.GenkitRegistry.define_model]       | Defines and registers a model.       |

??? info "Under the hood"

    Creating an instance of [Genkit][genkit.veneer.veneer.Genkit]:

    * creates a runtime configuration in the working directory
    * initializes a registry of actions including plugins, formats, etc.
    * starts server daemons to expose actions over HTTP

    The following servers are started depending on the environment:

    | Server Type | Purpose                                                         | Notes                                                   |
    |-------------|-----------------------------------------------------------------|---------------------------------------------------------|
    | Reflection  | Development-time API for inspecting and interacting with Genkit | Only starts in development mode (`GENKIT_ENV=dev`).     |
    | Flow        | Exposes registered flows as HTTP endpoints                      | Main server for production environment.                 |

"""

import asyncio
import logging
import os
import threading
from asyncio import Future
from collections.abc import AsyncIterator
from typing import Any

import uvicorn

from genkit.ai.document import Document
from genkit.ai.embedding import EmbedRequest, EmbedResponse
from genkit.ai.formats import built_in_formats
from genkit.ai.generate import (
    StreamingCallback as ModelStreamingCallback,
    generate_action,
)
from genkit.ai.model import (
    GenerateResponseChunkWrapper,
    GenerateResponseWrapper,
    ModelMiddleware,
)
from genkit.ai.prompt import to_generate_action_options
from genkit.aio import Channel
from genkit.core.action import ActionKind, ActionRunContext
from genkit.core.environment import is_dev_environment
from genkit.core.reflection import create_reflection_asgi_app
from genkit.core.typing import (
    DocumentData,
    GenerationCommonConfig,
    Message,
    Part,
    ToolChoice,
)
from genkit.veneer import server
from genkit.veneer.plugin import Plugin
from genkit.veneer.registry import GenkitRegistry

DEFAULT_REFLECTION_SERVER_SPEC = server.ServerSpec(
    scheme='http', host='127.0.0.1', port=3100
)

logger = logging.getLogger(__name__)


class Genkit(GenkitRegistry):
    """Veneer user-facing API for application developers who use the SDK.

    The methods exposed by the
    [GenkitRegistry][genkit.veneer.registry.GenkitRegistry] class are also part
    of the API.


    """

    def __init__(
        self,
        plugins: list[Plugin] | None = None,
        model: str | None = None,
        reflection_server_spec: server.ServerSpec = DEFAULT_REFLECTION_SERVER_SPEC,
    ) -> None:
        """Initialize a new Genkit instance.

        Args:
            plugins: List of plugins to initialize.
            model: Model name to use.
            reflection_server_spec: Server spec for the reflection
                server.
        """
        super().__init__()
        self.registry.default_model = model
        self._reflection_server_stop_event = threading.Event()
        self._reflection_server_thread = None

        if is_dev_environment():
            self._reflection_server_thread = threading.Thread(
                target=self._run_asgi_server_in_thread,
                args=[reflection_server_spec],
                # daemon=True,
            )
            self._reflection_server_thread.start()

        for format in built_in_formats:
            self.define_format(format)

        if not plugins:
            logger.warning('No plugins provided to Genkit')
        else:
            for plugin in plugins:
                if isinstance(plugin, Plugin):
                    plugin.initialize(ai=self)

                    def resolver(kind, name, plugin=plugin):
                        return plugin.resolve_action(self, kind, name)

                    self.registry.register_action_resolver(
                        plugin.plugin_name(), resolver
                    )
                else:
                    raise ValueError(
                        f'Invalid {plugin=} provided to Genkit: '
                        f'must be of type `genkit.veneer.plugin.Plugin`'
                    )

    def _run_asgi_server_in_thread(self, spec: server.ServerSpec) -> None:
        """Run the ASGI reflection server in a dedicated event loop.

        Args:
            spec: Server spec for the reflection server.
        """
        # Create a runtime for the reflection server before starting the server.
        runtimes_dir = os.path.join(os.getcwd(), '.genkit/runtimes')
        server.create_runtime(
            runtime_dir=runtimes_dir,
            reflection_server_spec=spec,
            at_exit_fn=os.remove,
        )

        # Create a new event loop for this thread.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Create the ASGI app
        app = create_reflection_asgi_app(
            registry=self.registry,
            on_lifespan_begin=None,
            on_lifespan_end=self._signal_server_shutdown,
        )

        # Config for uvicorn
        config = uvicorn.Config(
            app=app,
            host=spec.host,
            port=spec.port,
            log_level='info',
            loop='asyncio',
        )

        # Create the server
        server_instance = uvicorn.Server(config)
        loop.create_task(
            self._run_server_with_graceful_shutdown(server_instance)
        )
        loop.run_forever()
        # loop.run_until_complete(
        #    self._run_server_with_graceful_shutdown(server_instance)
        # )
        # loop.close()

    async def _run_server_with_graceful_shutdown(
        self, server_instance: uvicorn.Server
    ) -> None:
        """Run the server with graceful shutdown capability.

        Args:
            server_instance: The uvicorn server instance to run.
        """
        server_task = asyncio.create_task(server_instance.serve())
        stop_event_task = asyncio.create_task(self._wait_for_stop_event())
        _, pending = await asyncio.wait(
            [server_task, stop_event_task], return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        server_instance.should_exit = True
        await server_task

    async def _wait_for_stop_event(self) -> None:
        """Wait for the stop event to be set."""
        # Check the stop event periodically
        while not self._reflection_server_stop_event.is_set():
            await asyncio.sleep(0.1)

    def stop_reflection_server(self) -> None:
        """Stop the reflection server if it's running."""
        if (
            self._reflection_server_thread
            and self._reflection_server_thread.is_alive()
        ):
            self._reflection_server_stop_event.set()
            self._reflection_server_thread.join(timeout=5.0)
            self._reflection_server_stop_event.clear()
            self._reflection_server_thread = None

    async def generate(
        self,
        model: str | None = None,
        prompt: str | Part | list[Part] | None = None,
        system: str | Part | list[Part] | None = None,
        messages: list[Message] | None = None,
        tools: list[str] | None = None,
        return_tool_requests: bool | None = None,
        tool_choice: ToolChoice = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        max_turns: int | None = None,
        on_chunk: ModelStreamingCallback | None = None,
        context: dict[str, Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: type | dict[str, Any] | None = None,
        output_constrained: bool | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | None = None,
        # TODO:
        #  resume: ResumeOptions
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
        return await generate_action(
            self.registry,
            to_generate_action_options(
                registry=self.registry,
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
        tool_choice: ToolChoice = None,
        config: GenerationCommonConfig | dict[str, Any] | None = None,
        max_turns: int | None = None,
        context: dict[str, Any] | None = None,
        output_format: str | None = None,
        output_content_type: str | None = None,
        output_instructions: bool | str | None = None,
        output_schema: type | dict[str, Any] | None = None,
        output_constrained: bool | None = None,
        use: list[ModelMiddleware] | None = None,
        docs: list[DocumentData] | None = None,
    ) -> tuple[
        AsyncIterator[GenerateResponseChunkWrapper],
        Future[GenerateResponseWrapper],
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
        stream = Channel()

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
            docs=docs,
            use=use,
            on_chunk=lambda c: stream.send(c),
        )
        stream.set_close_future(resp)

        return (stream, stream.closed)

    async def embed(
        self,
        model: str | None = None,
        documents: list[Document] | None = None,
        options: dict[str, Any] | None = None,
    ) -> EmbedResponse:
        """Calculates embeddings for documents.

        Args:
            model: Optional embedder model name to use.
            documents: Texts to embed.
            options: embedding options

        Returns:
            The generated response with embeddings.
        """
        embed_action = self.registry.lookup_action(ActionKind.EMBEDDER, model)

        return (
            await embed_action.arun(
                EmbedRequest(input=documents, options=options)
            )
        ).response
