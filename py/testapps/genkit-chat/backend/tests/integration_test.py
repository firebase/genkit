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

"""Integration tests for genkit-chat backend API endpoints.

These tests verify that both FastAPI and Robyn frameworks work correctly
for the chat backend's HTTP endpoints.

Test Coverage::

    ┌─────────────────────────────────────────────────────────────────┐
    │ Endpoint              │ FastAPI  │ Robyn    │ Description       │
    ├───────────────────────┼──────────┼──────────┼───────────────────┤
    │ GET /                 │ ✓        │ ✓        │ Health check      │
    │ GET /api/config       │ ✓        │ ✓        │ API key status    │
    │ GET /api/models       │ ✓        │ ✓        │ Available models  │
    └───────────────────────┴──────────┴──────────┴───────────────────┘

Usage:
    # Run tests from backend directory
    cd backend && uv run pytest tests/ -v

    # Run specific test
    uv run pytest tests/integration_test.py::test_fastapi_health -v
"""

from __future__ import annotations

import asyncio
import multiprocessing
import os
import time

import httpx
import pytest

# Test configuration
FASTAPI_PORT = 18080
ROBYN_PORT = 18081
STARTUP_TIMEOUT = 15  # seconds to wait for server to start


def _run_fastapi_server(port: int) -> None:
    """Run FastAPI server in a separate process."""
    import sys

    # Set up paths correctly
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    src_dir = os.path.join(backend_dir, 'src')
    os.chdir(backend_dir)

    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    import uvicorn

    from main import create_fastapi_server  # type: ignore[import-not-found]

    app = create_fastapi_server()
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')


def _run_robyn_server(port: int) -> None:
    """Run Robyn server in a separate process."""
    import sys

    # Set up paths correctly
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    src_dir = os.path.join(backend_dir, 'src')
    os.chdir(backend_dir)

    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from main import create_http_server  # type: ignore[import-not-found]

    app = create_http_server()
    app.start(port=port)


async def _wait_for_server(port: int, timeout: float = STARTUP_TIMEOUT) -> bool:
    """Wait for server to become available."""
    start = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            try:
                response = await client.get(f'http://127.0.0.1:{port}/', timeout=1.0)
                if response.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.ReadTimeout):
                pass
            await asyncio.sleep(0.5)
    return False


@pytest.fixture(scope='module')
def fastapi_server():
    """Start FastAPI server for testing."""
    process = multiprocessing.Process(target=_run_fastapi_server, args=(FASTAPI_PORT,))
    process.start()

    # Wait for server to start
    loop = asyncio.new_event_loop()
    try:
        if not loop.run_until_complete(_wait_for_server(FASTAPI_PORT)):
            process.terminate()
            process.join(timeout=5)
            pytest.skip('FastAPI server failed to start')
    finally:
        loop.close()

    yield f'http://127.0.0.1:{FASTAPI_PORT}'

    process.terminate()
    process.join(timeout=5)
    if process.is_alive():
        process.kill()


@pytest.fixture(scope='module')
def robyn_server():
    """Start Robyn server for testing."""
    process = multiprocessing.Process(target=_run_robyn_server, args=(ROBYN_PORT,))
    process.start()

    # Wait for server to start
    loop = asyncio.new_event_loop()
    try:
        if not loop.run_until_complete(_wait_for_server(ROBYN_PORT)):
            process.terminate()
            process.join(timeout=5)
            pytest.skip('Robyn server failed to start')
    finally:
        loop.close()

    yield f'http://127.0.0.1:{ROBYN_PORT}'

    process.terminate()
    process.join(timeout=5)
    if process.is_alive():
        process.kill()


class TestFastAPI:
    """Integration tests for FastAPI backend."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, fastapi_server: str) -> None:
        """Test health check endpoint returns correct status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{fastapi_server}/')

            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'genkit-chat'
            assert data['framework'] == 'fastapi'

    @pytest.mark.asyncio
    async def test_config_endpoint(self, fastapi_server: str) -> None:
        """Test config endpoint returns API key status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{fastapi_server}/api/config')

            assert response.status_code == 200
            data = response.json()

            # Verify structure
            assert 'api_keys' in data
            assert 'features' in data

            # Check required API key entries exist
            assert 'GEMINI_API_KEY' in data['api_keys']
            assert 'OLLAMA_HOST' in data['api_keys']

            # Check features
            assert data['features']['rag_enabled'] is True
            assert data['features']['streaming_enabled'] is True
            assert data['features']['tools_enabled'] is True

    @pytest.mark.asyncio
    async def test_models_endpoint(self, fastapi_server: str) -> None:
        """Test models endpoint returns provider list."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{fastapi_server}/api/models')

            assert response.status_code == 200
            data = response.json()

            # Should be a list of providers
            assert isinstance(data, list)

            # Each provider should have required fields
            for provider in data:
                assert 'id' in provider
                assert 'name' in provider
                assert 'available' in provider
                assert 'models' in provider
                assert isinstance(provider['models'], list)

                # Each model should have required fields
                for model in provider['models']:
                    assert 'id' in model
                    assert 'name' in model
                    assert 'capabilities' in model


class TestRobyn:
    """Integration tests for Robyn backend."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, robyn_server: str) -> None:
        """Test health check endpoint returns correct status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{robyn_server}/')

            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'genkit-chat'
            # Robyn doesn't include framework in health response

    @pytest.mark.asyncio
    async def test_config_endpoint(self, robyn_server: str) -> None:
        """Test config endpoint returns API key status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{robyn_server}/api/config')

            assert response.status_code == 200
            data = response.json()

            # Verify structure
            assert 'api_keys' in data
            assert 'features' in data

            # Check required API key entries exist
            assert 'GEMINI_API_KEY' in data['api_keys']
            assert 'OLLAMA_HOST' in data['api_keys']

    @pytest.mark.asyncio
    async def test_models_endpoint(self, robyn_server: str) -> None:
        """Test models endpoint returns provider list."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{robyn_server}/api/models')

            assert response.status_code == 200
            data = response.json()

            # Should be a list of providers
            assert isinstance(data, list)

            # Each provider should have required fields
            for provider in data:
                assert 'id' in provider
                assert 'name' in provider
                assert 'models' in provider

    @pytest.mark.asyncio
    async def test_cors_preflight(self, robyn_server: str) -> None:
        """Test CORS preflight request is handled correctly."""
        async with httpx.AsyncClient() as client:
            response = await client.options(
                f'{robyn_server}/api/chat',
                headers={
                    'Origin': 'http://localhost:4200',
                    'Access-Control-Request-Method': 'POST',
                },
            )

            # Should handle OPTIONS request
            assert response.status_code in (200, 204)


class TestFrameworkParity:
    """Tests to ensure both frameworks return consistent responses."""

    @pytest.mark.asyncio
    async def test_config_parity(self, fastapi_server: str, robyn_server: str) -> None:
        """Test both frameworks return similar config structure."""
        async with httpx.AsyncClient() as client:
            fastapi_resp = await client.get(f'{fastapi_server}/api/config')
            robyn_resp = await client.get(f'{robyn_server}/api/config')

            assert fastapi_resp.status_code == 200
            assert robyn_resp.status_code == 200

            fastapi_data = fastapi_resp.json()
            robyn_data = robyn_resp.json()

            # Both should have same structure
            assert set(fastapi_data.keys()) == set(robyn_data.keys())
            assert set(fastapi_data['api_keys'].keys()) == set(robyn_data['api_keys'].keys())
            assert fastapi_data['features'] == robyn_data['features']

    @pytest.mark.asyncio
    async def test_models_parity(self, fastapi_server: str, robyn_server: str) -> None:
        """Test both frameworks return same models."""
        async with httpx.AsyncClient() as client:
            fastapi_resp = await client.get(f'{fastapi_server}/api/models')
            robyn_resp = await client.get(f'{robyn_server}/api/models')

            assert fastapi_resp.status_code == 200
            assert robyn_resp.status_code == 200

            fastapi_data = fastapi_resp.json()
            robyn_data = robyn_resp.json()

            # Both should return same number of providers
            assert len(fastapi_data) == len(robyn_data)

            # Provider IDs should match
            fastapi_ids = {p['id'] for p in fastapi_data}
            robyn_ids = {p['id'] for p in robyn_data}
            assert fastapi_ids == robyn_ids
