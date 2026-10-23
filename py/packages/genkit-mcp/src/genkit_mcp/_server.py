# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0

"""A Genkit app served to MCP clients as an MCP server."""

import sys
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from io import TextIOWrapper
from typing import Any
from weakref import WeakKeyDictionary

import anyio
import structlog
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http import EventStore
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, Tool
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from genkit import Genkit, GenkitError, MultipartToolResponse
from genkit.plugin_api import Action
from genkit_mcp._export import error_result, multipart_to_call_result, tool_to_mcp

logger = structlog.get_logger(__name__)

DEFAULT_VERSION = '1.0.0'
"""What JS and Go both advertise when the app names no version."""

LOCAL_HOSTS = ('localhost', 'localhost:*', '127.0.0.1', '127.0.0.1:*', '[::1]', '[::1]:*')
"""``Host`` values the HTTP endpoint accepts unless told otherwise."""

LOCAL_ORIGINS = (
    'http://localhost',
    'http://localhost:*',
    'http://127.0.0.1',
    'http://127.0.0.1:*',
    'http://[::1]',
    'http://[::1]:*',
)
"""``Origin`` values the HTTP endpoint accepts unless told otherwise."""


class McpServer:
    """Serves a Genkit app's tools to MCP clients.

    Tools are read from the app on every ``tools/list``, so a tool defined
    after the server was built is still served. Tools a dynamic action
    provider serves are not.

    Attributes:
        name: Name the server advertises to clients.
        version: Version the server advertises to clients.
    """

    def __init__(
        self,
        ai: Genkit,
        name: str,
        *,
        version: str = DEFAULT_VERSION,
        instructions: str | None = None,
        redirect_stdout: bool = True,
    ) -> None:
        """Build a server over a Genkit app.

        Args:
            ai: The app whose tools are served.
            name: Name the server advertises.
            version: Version the server advertises.
            instructions: How a client should use this server.
            redirect_stdout: Whether ``start`` moves this process's stdout to
                stderr. Leave it on unless the app already keeps stdout clear.
        """
        self._ai = ai
        self._name = name
        self._version = version
        self._redirect_stdout = redirect_stdout
        self._described: WeakKeyDictionary[Action, Tool | None] = WeakKeyDictionary()
        self._server: Server[Any, Any] = Server(name, version=version, instructions=instructions)
        self._server.list_tools()(self._list_tools)
        self._server.call_tool()(self._call_tool)

    @property
    def name(self) -> str:
        """Name the server advertises to clients."""
        return self._name

    @property
    def version(self) -> str:
        """Version the server advertises to clients."""
        return self._version

    async def serve(self, read_stream: Any, write_stream: Any, *, raise_exceptions: bool = False) -> None:  # noqa: ANN401
        """Serve on a stream pair until the client disconnects.

        Args:
            read_stream: Where requests arrive, as the MCP SDK shapes it.
            write_stream: Where responses go, as the MCP SDK shapes it.
            raise_exceptions: Whether a handler error propagates instead of
                becoming an error response. For tests.
        """
        await self._server.run(
            read_stream,
            write_stream,
            self._server.create_initialization_options(),
            raise_exceptions=raise_exceptions,
        )

    async def start(self) -> None:
        """Serve on this process's stdin and stdout until stdin closes.

        stdout is the wire, so it is captured before anything can write to it
        and the process's own stdout is then pointed at stderr for the rest of
        its life. A logger built before this call keeps the descriptor it
        captured.
        """
        sys.stdout.flush()
        streams = stdio_server(
            stdin=anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding='utf-8')),
            stdout=anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding='utf-8')),
        )
        if self._redirect_stdout:
            _redirect_stdout_to_stderr()
        async with streams as (read_stream, write_stream):
            await self.serve(read_stream, write_stream)

    def _session_manager(
        self,
        *,
        stateless: bool = False,
        json_response: bool = False,
        event_store: EventStore | None = None,
        security: TransportSecuritySettings,
    ) -> StreamableHTTPSessionManager:
        """Build a new streamable HTTP session manager, since one can run only once."""
        return StreamableHTTPSessionManager(
            app=self._server,
            event_store=event_store,
            json_response=json_response,
            stateless=stateless,
            security_settings=security,
        )

    def asgi_app(
        self,
        path: str = '/mcp',
        *,
        stateless: bool = False,
        json_response: bool = False,
        event_store: EventStore | None = None,
        allowed_hosts: Sequence[str] = LOCAL_HOSTS,
        allowed_origins: Sequence[str] = LOCAL_ORIGINS,
    ) -> Starlette:
        """Build an ASGI app serving this server over streamable HTTP.

        The app owns a manager of its own and opens it in its lifespan, so
        whatever runs the app has to run that lifespan. Starlette does not run a
        mounted app's lifespan, so mounting this one means chaining its
        ``router.lifespan_context`` into the host app's.

        The endpoint has no authentication: anyone who can reach it can call
        every tool. A request whose ``Host`` is not in ``allowed_hosts`` gets a
        421, and one whose ``Origin`` is not in ``allowed_origins`` gets a 403,
        so a web page cannot reach a local server through DNS rebinding.

        stdout is untouched here, unlike ``start``: HTTP carries no wire on it.

        Args:
            path: Route the endpoint answers on, within this app.
            stateless: Whether each request gets a fresh transport.
            json_response: Whether a response is one JSON body rather than an
                SSE stream.
            event_store: Where to record events for a reconnecting client.
            allowed_hosts: ``Host`` header values to accept. ``name:*``
                accepts any port. Defaults to localhost on any port.
            allowed_origins: ``Origin`` header values to accept from a
                browser. ``scheme://name:*`` accepts any port. A request
                with no ``Origin`` is accepted. Defaults to localhost on any
                port.

        Returns:
            A Starlette app to serve, mount, or wrap in middleware.

        Raises:
            TypeError: If ``allowed_hosts`` or ``allowed_origins`` is a single
                string rather than a sequence of them.
        """
        for argument, value in (('allowed_hosts', allowed_hosts), ('allowed_origins', allowed_origins)):
            if isinstance(value, str):
                raise TypeError(f'{argument} takes a sequence of strings, not one string: [{value!r}]')
        manager = self._session_manager(
            stateless=stateless,
            json_response=json_response,
            event_store=event_store,
            security=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=list(allowed_hosts),
                allowed_origins=list(allowed_origins),
            ),
        )

        @asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncIterator[None]:
            async with manager.run():
                yield

        return Starlette(routes=[Route(path, endpoint=_StreamableHttpEndpoint(manager))], lifespan=lifespan)

    async def _list_tools(self) -> list[Tool]:
        """Describe every tool this server offers, read fresh from the app."""
        return [tool for _, tool in await self._served_tools()]

    async def _served_tools(self) -> list[tuple[Action, Tool]]:
        """Pair each action this server serves with how it is described.

        Listing and calling read the same pairs, so a tool MCP cannot describe
        is not reachable by name either.
        """
        served: list[tuple[Action, Tool]] = []
        for handle in await self._ai.list_tools():
            action = handle.action()
            if action not in self._described:
                self._described[action] = tool_to_mcp(action)
            tool = self._described[action]
            if tool is not None:
                served.append((action, tool))
        return served

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> CallToolResult:
        """Run one tool and map what it returned, reporting every failure as a result.

        A raised error becomes an ``isError`` result and is logged here, where
        its traceback is still useful.
        """
        action = await self._find_tool(name)
        if action is None:
            return error_result(f'Tool {name!r} is not registered')

        context = self._request_context()
        try:
            response = (await action.run(arguments, context=context)).response
            if not isinstance(response, MultipartToolResponse):
                return error_result(f'Tool {name!r} did not return a tool response')
            return multipart_to_call_result(response, name)
        except Exception as error:
            await logger.aexception('an MCP tool call failed', tool=name)
            return error_result(_client_message(name, error))

    def _request_context(self) -> dict[str, Any] | None:
        """Pass the request's MCP ``_meta`` in the shape the client's handler reads."""
        try:
            meta = self._server.request_context.meta
        except LookupError:
            return None
        if meta is None:
            return None
        return {'mcp': {'_meta': meta.model_dump(by_alias=True, exclude_none=True)}}

    async def _find_tool(self, name: str) -> Action | None:
        """Find a tool by the name it was listed under."""
        for action, tool in await self._served_tools():
            if tool.name == name:
                return action
        return None


def create_mcp_server(
    ai: Genkit,
    name: str,
    *,
    version: str = DEFAULT_VERSION,
    instructions: str | None = None,
    redirect_stdout: bool = True,
) -> McpServer:
    """Build a server over a Genkit app, registering nothing.

    Args:
        ai: The app whose tools are served.
        name: Name the server advertises.
        version: Version the server advertises.
        instructions: How a client should use this server.
        redirect_stdout: Whether ``start`` moves this process's stdout to stderr.

    Returns:
        A server ready for ``start`` or ``serve``.
    """
    return McpServer(
        ai,
        name,
        version=version,
        instructions=instructions,
        redirect_stdout=redirect_stdout,
    )


def _client_message(tool_name: str, error: Exception) -> str:
    """Say why a tool failed without passing on text the app never chose to show.

    A ``GenkitError`` keeps its status and message but not its cause's text,
    which can carry a request URL or a credential.
    """
    if isinstance(error, GenkitError):
        return f'{error.status}: {error.original_message}'
    return f'Tool {tool_name!r} failed'


def _redirect_stdout_to_stderr() -> None:
    """Point this process's stdout at stderr, so nothing can corrupt the wire.

    Rebinding ``sys.stdout`` is enough to move a logger that was built before
    this call: structlog's default ``PrintLogger`` passes ``file=None`` to
    ``print``, which reads ``sys.stdout`` at call time. A logger bound to an
    explicit stream is the app's own choice and is left where it points.
    """
    sys.stdout = sys.stderr


class _StreamableHttpEndpoint:
    """A streamable HTTP session manager as a plain ASGI app.

    A class rather than a function because Starlette reads a function endpoint
    as a request handler, which never sees the GET and DELETE streamable HTTP
    needs. It sits on a ``Route``, since a ``Mount`` redirects its own path to
    one with a trailing slash that no client asks for.
    """

    def __init__(self, manager: StreamableHTTPSessionManager) -> None:
        """Wrap one session manager.

        Args:
            manager: The manager to serve, whose ``run()`` context has to be
                open before this app handles anything.
        """
        self.manager = manager

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Hand one ASGI request to the session manager.

        Args:
            scope: The ASGI connection scope.
            receive: Where the request body arrives.
            send: Where the response goes.
        """
        await self.manager.handle_request(scope, receive, send)
