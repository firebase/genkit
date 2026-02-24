#!/usr/bin/env python3
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the automatic background Dev UI reflection server.

Covers the key invariants of the background-thread approach:
- Server starts on Genkit() construction in dev mode, no extra wiring needed
- Works alongside FastAPI with no lifespan hooks
- Multiple Genkit instances each get their own port
- Flows registered after construction are immediately visible
- No server starts in production mode
"""

import os
import socket
from unittest import mock

import httpx
import pytest

from genkit.ai._aio import Genkit
from genkit.ai._server import ServerSpec
from genkit.core.environment import EnvVar, GenkitEnvironment


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _wait_and_get(ai: Genkit, path: str) -> httpx.Response:
    assert ai._reflection_ready.wait(timeout=5), 'Reflection server never became ready'
    url = ai._reflection_server_spec.url  # type: ignore[union-attr]
    return httpx.get(f'{url}{path}', timeout=1.0)


def test_server_starts_on_construction() -> None:
    """Core invariant: Genkit() in dev mode brings up Dev UI automatically.

    No run_main(), no lifespan hooks — construction is sufficient.
    """
    port = _find_free_port()
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}):
        ai = Genkit(reflection_server_spec=ServerSpec(scheme='http', host='127.0.0.1', port=port))
        resp = _wait_and_get(ai, '/api/__health')
    assert resp.status_code == 200


def test_flow_registered_after_construction_is_visible() -> None:
    """Flows defined after Genkit() are visible in /api/actions.

    Note: this is a sequential test (flow registered before the HTTP request),
    so it proves the plumbing works but NOT concurrent thread-safety.
    See test_registry_reads_concurrent_with_writes for that.
    """
    port = _find_free_port()
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}):
        ai = Genkit(reflection_server_spec=ServerSpec(scheme='http', host='127.0.0.1', port=port))

        @ai.flow()
        async def greet(name: str) -> str:
            return f'Hello, {name}!'

        resp = _wait_and_get(ai, '/api/actions')

    assert resp.status_code == 200
    assert '/flow/greet' in resp.json()


def test_registry_reads_concurrent_with_writes() -> None:
    """The reflection thread reads the registry while the main thread writes to it.

    Spams /api/actions from a background thread while registering flows via
    @ai.flow() on the main thread simultaneously. The registry uses
    threading.RLock — responses must always be valid JSON dicts, never empty
    or corrupted.
    """
    import threading

    port = _find_free_port()
    errors: list[Exception] = []

    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}):
        ai = Genkit(reflection_server_spec=ServerSpec(scheme='http', host='127.0.0.1', port=port))
        assert ai._reflection_ready.wait(timeout=5)

        stop = threading.Event()

        def spam_reads() -> None:
            url = f'http://127.0.0.1:{port}/api/actions'
            while not stop.is_set():
                try:
                    resp = httpx.get(url, timeout=1.0)
                    data = resp.json()
                    assert isinstance(data, dict), f'Got non-dict: {data!r}'
                except Exception as e:
                    errors.append(e)

        reader = threading.Thread(target=spam_reads, daemon=True)
        reader.start()

        # Register flows via the real public API while the reader is active
        for i in range(20):

            @ai.flow()
            async def _flow(x: str, _i: int = i) -> str:
                return f'flow_{_i}: {x}'

        stop.set()
        reader.join(timeout=2)

    assert not errors, f'Concurrent read/write errors: {errors}'


def test_two_instances_get_different_ports() -> None:
    """Two Genkit() instances each bind their own port — no collision."""
    port1, port2 = _find_free_port(), _find_free_port()
    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}):
        ai1 = Genkit(reflection_server_spec=ServerSpec(scheme='http', host='127.0.0.1', port=port1))
        ai2 = Genkit(reflection_server_spec=ServerSpec(scheme='http', host='127.0.0.1', port=port2))

        assert ai1._reflection_ready.wait(timeout=5)
        assert ai2._reflection_ready.wait(timeout=5)

    assert port1 != port2
    assert httpx.get(f'http://127.0.0.1:{port1}/api/__health', timeout=1.0).status_code == 200
    assert httpx.get(f'http://127.0.0.1:{port2}/api/__health', timeout=1.0).status_code == 200


def test_fastapi_app_needs_no_lifespan() -> None:
    """FastAPI + Genkit: both servers serve requests concurrently.

    Runs real uvicorn for the FastAPI app (in a background thread) alongside
    the Genkit reflection server (also in a background thread), then hits both
    simultaneously. This is the actual production topology — two uvicorn event
    loops in the same process, each owning its own thread.
    """
    import threading

    import uvicorn
    from fastapi import FastAPI

    reflection_port = _find_free_port()
    fastapi_port = _find_free_port()

    with mock.patch.dict(os.environ, {EnvVar.GENKIT_ENV: GenkitEnvironment.DEV}):
        ai = Genkit(reflection_server_spec=ServerSpec(scheme='http', host='127.0.0.1', port=reflection_port))

        app = FastAPI()  # No lifespan= argument

        @app.get('/ping')
        def ping() -> dict:
            return {'pong': True}

        # Spin up real uvicorn for FastAPI — same topology as `uvicorn main:app`
        fastapi_server = uvicorn.Server(
            uvicorn.Config(app, host='127.0.0.1', port=fastapi_port, loop='asyncio', log_level='warning')
        )
        fastapi_thread = threading.Thread(target=fastapi_server.run, daemon=True)
        fastapi_thread.start()

        # Wait for both servers to be ready
        assert ai._reflection_ready.wait(timeout=5), 'Reflection server never became ready'
        deadline = __import__('time').monotonic() + 5
        while not fastapi_server.started:
            if __import__('time').monotonic() > deadline:
                raise AssertionError('FastAPI server never became ready')
            __import__('time').sleep(0.05)

    # Both servers respond while running concurrently in the same process
    assert httpx.get(f'http://127.0.0.1:{fastapi_port}/ping', timeout=1.0).json() == {'pong': True}
    assert httpx.get(f'http://127.0.0.1:{reflection_port}/api/__health', timeout=1.0).status_code == 200

    fastapi_server.should_exit = True


def test_no_server_in_prod_mode() -> None:
    """Genkit() with no GENKIT_ENV must NOT start a background server."""
    port = _find_free_port()
    with mock.patch.dict(os.environ, {}, clear=True):
        ai = Genkit(reflection_server_spec=ServerSpec(scheme='http', host='127.0.0.1', port=port))

    assert not ai._reflection_ready.is_set()
    with pytest.raises(httpx.ConnectError):
        httpx.get(f'http://127.0.0.1:{port}/api/__health', timeout=0.5)
