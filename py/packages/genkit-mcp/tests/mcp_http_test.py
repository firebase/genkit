# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0

"""Tests driving a Genkit-backed MCP server over streamable HTTP."""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from genkit_mcp import create_mcp_server
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import ASGIApp

from genkit import Genkit

BASE_URL = 'http://localhost:8000'

INITIALIZE = {
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2025-06-18',
        'capabilities': {},
        'clientInfo': {'name': 'test', 'version': '1.0.0'},
    },
}


class Greeting(BaseModel):
    name: str


def app_with_tools() -> Genkit:
    ai = Genkit()

    @ai.tool()
    async def greet(greeting: Greeting) -> str:
        """Greet."""
        return f'hello {greeting.name}'

    @ai.tool()
    async def ping() -> str:
        """Answer."""
        return 'pong'

    return ai


def http_client(app: ASGIApp) -> httpx.AsyncClient:
    """Speak to an ASGI app directly, so no port is bound and nothing is polled."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=BASE_URL)


async def initialize(app: Starlette, **headers: str) -> httpx.Response:
    """POST one initialize request with extra headers, running the app's lifespan around it."""
    async with app.router.lifespan_context(app):
        async with http_client(app) as http:
            return await http.post(
                '/mcp',
                headers={'accept': 'application/json, text/event-stream', **headers},
                json=INITIALIZE,
            )


@asynccontextmanager
async def session_over(app: Starlette, url: str = f'{BASE_URL}/mcp') -> AsyncIterator[ClientSession]:
    """Open an MCP session against an ASGI app, running its lifespan around it."""
    async with app.router.lifespan_context(app):
        async with http_client(app) as http:
            async with streamable_http_client(url, http_client=http) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session


@pytest.mark.asyncio
async def test_a_stateful_app_lists_and_calls_the_apps_tools() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')

    async with session_over(server.asgi_app()) as session:
        listed = await session.list_tools()
        result = await session.call_tool('greet', {'name': 'ada'})

    assert sorted(tool.name for tool in listed.tools) == ['greet', 'ping']
    assert result.content == [TextContent(type='text', text='hello ada')]


@pytest.mark.asyncio
async def test_a_stateless_app_lists_and_calls_the_apps_tools() -> None:
    """Every request gets its own transport, so nothing is carried between them."""
    server = create_mcp_server(app_with_tools(), 'bookshop')

    async with session_over(server.asgi_app(stateless=True)) as session:
        listed = await session.list_tools()
        result = await session.call_tool('ping', {})

    assert sorted(tool.name for tool in listed.tools) == ['greet', 'ping']
    assert result.content == [TextContent(type='text', text='pong')]


@pytest.mark.asyncio
async def test_a_stateful_app_hands_out_a_session_id_and_a_stateless_one_does_not() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')
    stateful = server.asgi_app()
    stateless = server.asgi_app(stateless=True)

    ids = []
    for app in (stateful, stateless):
        async with app.router.lifespan_context(app):
            async with http_client(app) as http:
                async with streamable_http_client(f'{BASE_URL}/mcp', http_client=http) as (
                    read,
                    write,
                    get_session_id,
                ):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        ids.append(get_session_id())

    assert ids[0] is not None
    assert ids[1] is None


@pytest.mark.asyncio
async def test_a_json_response_app_answers_without_an_event_stream() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')
    app = server.asgi_app(json_response=True)

    response = await initialize(app)

    assert response.headers['content-type'].startswith('application/json')
    assert response.json()['result']['serverInfo']['name'] == 'bookshop'


@pytest.mark.asyncio
async def test_the_path_is_configurable() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')

    async with session_over(server.asgi_app('/tools'), f'{BASE_URL}/tools') as session:
        listed = await session.list_tools()

    assert [tool.name for tool in listed.tools] == ['greet', 'ping']


@pytest.mark.asyncio
async def test_the_app_mounts_into_a_host_app_that_chains_its_lifespan() -> None:
    """Starlette runs no mounted app's lifespan, so the host has to chain it."""
    server = create_mcp_server(app_with_tools(), 'bookshop')
    mcp_app = server.asgi_app('/mcp')

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with mcp_app.router.lifespan_context(app):
            yield

    host = Starlette(routes=[Mount('/api', app=mcp_app)], lifespan=lifespan)

    async with session_over(host, f'{BASE_URL}/api/mcp') as session:
        listed = await session.list_tools()

    assert [tool.name for tool in listed.tools] == ['greet', 'ping']


@pytest.mark.asyncio
async def test_each_app_from_one_server_runs_its_own_lifespan() -> None:
    """A session manager runs once, so every asgi_app call owns a fresh one and both serve."""
    server = create_mcp_server(app_with_tools(), 'bookshop')

    for app in (server.asgi_app(), server.asgi_app()):
        async with session_over(app) as session:
            listed = await session.list_tools()
        assert [tool.name for tool in listed.tools] == ['greet', 'ping']


@pytest.mark.asyncio
async def test_serving_over_http_leaves_stdout_alone() -> None:
    """Only stdio makes stdout the wire, so only start() moves this process's."""
    server = create_mcp_server(app_with_tools(), 'bookshop')
    before = sys.stdout

    async with session_over(server.asgi_app()) as session:
        await session.list_tools()

    assert sys.stdout is before


@pytest.mark.asyncio
@pytest.mark.parametrize('host', ['localhost', 'localhost:3000', '127.0.0.1:8000', '[::1]:8000'])
async def test_a_local_host_is_served_on_any_port(host: str) -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')

    response = await initialize(server.asgi_app(json_response=True), host=host)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_a_host_outside_the_allowed_list_is_refused() -> None:
    """A page that rebinds its own name to 127.0.0.1 still sends that name as Host."""
    server = create_mcp_server(app_with_tools(), 'bookshop')

    response = await initialize(server.asgi_app(json_response=True), host='evil.example:8000')

    assert response.status_code == 421
    assert 'mcp-session-id' not in response.headers


@pytest.mark.asyncio
async def test_an_origin_outside_the_allowed_list_is_refused() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')

    response = await initialize(server.asgi_app(json_response=True), origin='http://evil.example')

    assert response.status_code == 403
    assert 'mcp-session-id' not in response.headers


@pytest.mark.asyncio
async def test_a_local_origin_is_served() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')

    response = await initialize(server.asgi_app(json_response=True), origin='http://localhost:5173')

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_allowed_hosts_and_origins_replace_the_local_defaults() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')

    def app() -> Starlette:
        return server.asgi_app(
            json_response=True,
            allowed_hosts=['tools.example.com'],
            allowed_origins=['https://app.example.com'],
        )

    served = await initialize(app(), host='tools.example.com', origin='https://app.example.com')
    local = await initialize(app(), host='localhost:8000')

    assert served.status_code == 200
    assert local.status_code == 421


def test_a_single_string_for_allowed_hosts_is_refused() -> None:
    """A str is a Sequence[str] of its characters, which would refuse every request."""
    server = create_mcp_server(app_with_tools(), 'bookshop')

    with pytest.raises(TypeError, match='allowed_hosts'):
        server.asgi_app(allowed_hosts='tools.example.com')


def test_a_single_string_for_allowed_origins_is_refused() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')

    with pytest.raises(TypeError, match='allowed_origins'):
        server.asgi_app(allowed_origins='https://app.example.com')


@pytest.mark.asyncio
async def test_a_trailing_slash_redirects_to_the_endpoint() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')
    app = server.asgi_app()

    async with app.router.lifespan_context(app):
        async with http_client(app) as http:
            response = await http.post('/mcp/', json=INITIALIZE)

    assert response.status_code == 307
    assert response.headers['location'] == f'{BASE_URL}/mcp'


@pytest.mark.asyncio
async def test_delete_ends_a_stateful_session() -> None:
    server = create_mcp_server(app_with_tools(), 'bookshop')
    app = server.asgi_app(json_response=True)
    accept = {'accept': 'application/json, text/event-stream'}

    async with app.router.lifespan_context(app):
        async with http_client(app) as http:
            opened = await http.post('/mcp', headers=accept, json=INITIALIZE)
            session = {'mcp-session-id': opened.headers['mcp-session-id']}
            deleted = await http.delete('/mcp', headers={**accept, **session})
            after = await http.post(
                '/mcp',
                headers={**accept, **session},
                json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            )

    assert deleted.status_code == 200
    assert after.status_code == 404


@pytest.mark.asyncio
async def test_an_app_whose_lifespan_never_ran_fails_every_request() -> None:
    """Mounting without chaining the lifespan fails loudly rather than hanging."""
    server = create_mcp_server(app_with_tools(), 'bookshop')
    app = server.asgi_app(json_response=True)

    async with http_client(app) as http:
        with pytest.raises(RuntimeError, match='Task group is not initialized'):
            await http.post('/mcp', headers={'accept': 'application/json, text/event-stream'}, json=INITIALIZE)
