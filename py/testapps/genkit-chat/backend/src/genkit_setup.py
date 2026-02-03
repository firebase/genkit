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

"""Genkit setup and plugin initialization.

This module handles dynamic plugin loading based on available API keys.
It allows the app to run with any subset of model providers.

Supported Providers::

    ┌─────────────────────┬─────────────────────────────────────────────┐
    │ Provider            │ Environment Variable                        │
    ├─────────────────────┼─────────────────────────────────────────────┤
    │ Google AI           │ GOOGLE_GENAI_API_KEY                        │
    │ Vertex AI           │ GOOGLE_CLOUD_PROJECT (+ ADC)                │
    │ Anthropic           │ ANTHROPIC_API_KEY                           │
    │ OpenAI              │ OPENAI_API_KEY                              │
    │ Cloudflare AI       │ CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN│
    │ Ollama (local)      │ OLLAMA_HOST (default: localhost:11434)      │
    └─────────────────────┴─────────────────────────────────────────────┘

Usage:
    from genkit_setup import get_genkit, get_available_models

    g = await get_genkit()
    models = await get_available_models()
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from genkit import Genkit

logger = logging.getLogger(__name__)

# Singleton Genkit instance
_genkit_instance: Genkit | None = None


def _load_plugins() -> list[Any]:
    """Load plugins based on available environment variables.

    Returns:
        List of initialized plugin instances.
    """
    plugins = []

    # Google AI (Gemini) - check GEMINI_API_KEY first, then legacy GOOGLE_GENAI_API_KEY
    gemini_api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_GENAI_API_KEY')
    if gemini_api_key:
        try:
            from genkit.plugins.google_genai import GoogleAI

            plugins.append(GoogleAI())
            logger.info('✓ Loaded Google AI plugin')
        except ImportError:
            logger.warning('Google AI plugin not installed')

    # Vertex AI (Gemini + Imagen + Veo)
    # VertexAI plugin dynamically discovers all available models including:
    # - Gemini text models (gemini-2.0-flash, gemini-2.5-pro, etc.)
    # - Imagen image generation models (imagen-3.0-generate-002, etc.)
    # - Veo video generation models (veo-2.0-generate-001, etc.)
    if os.getenv('GOOGLE_CLOUD_PROJECT'):
        try:
            from genkit.plugins.google_genai import VertexAI

            plugins.append(VertexAI())
            logger.info('✓ Loaded Vertex AI plugin (Gemini, Imagen, Veo)')
        except ImportError:
            logger.warning('Vertex AI plugin not installed')

        # Model Garden (third-party models on Vertex: Claude, Llama, etc.)
        try:
            from genkit.plugins.vertex_ai import ModelGardenPlugin

            plugins.append(ModelGardenPlugin())
            logger.info('✓ Loaded Vertex AI Model Garden plugin')
        except ImportError:
            pass  # Model Garden is optional

    # Anthropic
    if os.getenv('ANTHROPIC_API_KEY'):
        try:
            from genkit.plugins.anthropic import Anthropic

            plugins.append(Anthropic())
            logger.info('Loaded Anthropic plugin')
        except ImportError:
            logger.warning('Anthropic plugin not installed')

    # OpenAI (via compat-oai plugin which supports OpenAI and compatible APIs)
    if os.getenv('OPENAI_API_KEY'):
        try:
            from genkit.plugins.compat_oai import OpenAI

            plugins.append(OpenAI())
            logger.info('Loaded OpenAI plugin (via compat-oai)')
        except ImportError:
            logger.warning('OpenAI plugin not installed')

    # Cloudflare AI
    if os.getenv('CLOUDFLARE_ACCOUNT_ID') and os.getenv('CLOUDFLARE_API_TOKEN'):
        try:
            from genkit.plugins.cf_ai import CfAI

            plugins.append(CfAI())
            logger.info('Loaded Cloudflare AI plugin')
        except ImportError:
            logger.warning('Cloudflare AI plugin not installed')

    # Ollama (always try - it's for local development)
    ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    try:
        from genkit.plugins.ollama import Ollama

        plugins.append(Ollama(server_address=ollama_host))
        logger.info(f'Loaded Ollama plugin (host: {ollama_host})')
    except ImportError:
        logger.warning('Ollama plugin not installed')

    # Note: DevLocalVectorStore is not a plugin - it's a factory function
    # use define_dev_local_vector_store() to create indexers/retrievers

    if not plugins:
        logger.warning('No model plugins loaded! Set at least one API key or start Ollama.')

    return plugins


async def get_genkit() -> Genkit:
    """Get or create the singleton Genkit instance.

    Returns:
        Initialized Genkit instance with available plugins.
    """
    global _genkit_instance

    if _genkit_instance is None:
        plugins = _load_plugins()
        _genkit_instance = Genkit(plugins=plugins)
        logger.info(f'Initialized Genkit with {len(plugins)} plugins')

    return _genkit_instance


async def get_available_models() -> list[dict[str, Any]]:
    """Get available models grouped by provider.

    Returns:
        List of provider info with their available models.

    Note:
        Model lists for cloud providers (Google AI, Anthropic, OpenAI) are hardcoded
        because these providers do not offer public APIs for model discovery, or their
        discovery APIs require authentication and may have rate limits.

        Ollama is the exception - its /api/tags endpoint provides dynamic model discovery.

        Future improvement: When providers offer stable model listing APIs, this function
        should be refactored to query them dynamically. For now, update the hardcoded
        lists when new models are released or deprecated.
    """
    providers = []

    # Google AI models (current as of Feb 2026 - 2.5+ only)
    if os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_GENAI_API_KEY'):
        providers.append({
            'id': 'google-genai',
            'name': 'Google AI',
            'available': True,
            'models': [
                {
                    'id': 'googleai/gemini-3-flash-preview',
                    'name': 'Gemini 3 Flash Preview',
                    'capabilities': ['text', 'vision', 'streaming', 'thinking'],
                    'context_window': 1000000,
                },
                {
                    'id': 'googleai/gemini-3-pro-preview',
                    'name': 'Gemini 3 Pro Preview',
                    'capabilities': ['text', 'vision', 'streaming', 'thinking'],
                    'context_window': 2000000,
                },
                {
                    'id': 'googleai/gemini-2.5-flash',
                    'name': 'Gemini 2.5 Flash',
                    'capabilities': ['text', 'vision', 'streaming', 'thinking'],
                    'context_window': 1000000,
                },
                {
                    'id': 'googleai/gemini-2.5-pro',
                    'name': 'Gemini 2.5 Pro',
                    'capabilities': ['text', 'vision', 'streaming', 'thinking'],
                    'context_window': 1000000,
                },
            ],
        })

    # Anthropic models
    if os.getenv('ANTHROPIC_API_KEY'):
        providers.append({
            'id': 'anthropic',
            'name': 'Anthropic',
            'available': True,
            'models': [
                {
                    'id': 'anthropic/claude-sonnet-4-20250514',
                    'name': 'Claude Sonnet 4',
                    'capabilities': ['text', 'vision', 'streaming'],
                    'context_window': 200000,
                },
                {
                    'id': 'anthropic/claude-opus-4-20250514',
                    'name': 'Claude Opus 4',
                    'capabilities': ['text', 'vision', 'streaming'],
                    'context_window': 200000,
                },
                {
                    'id': 'anthropic/claude-3-7-sonnet',
                    'name': 'Claude 3.7 Sonnet',
                    'capabilities': ['text', 'vision', 'streaming'],
                    'context_window': 200000,
                },
            ],
        })

    # OpenAI models
    if os.getenv('OPENAI_API_KEY'):
        providers.append({
            'id': 'openai',
            'name': 'OpenAI',
            'available': True,
            'models': [
                {
                    'id': 'openai/gpt-4.1',
                    'name': 'GPT-4.1',
                    'capabilities': ['text', 'vision', 'streaming'],
                    'context_window': 128000,
                },
                {
                    'id': 'openai/gpt-4o',
                    'name': 'GPT-4o',
                    'capabilities': ['text', 'vision', 'streaming'],
                    'context_window': 128000,
                },
                {
                    'id': 'openai/gpt-4o-mini',
                    'name': 'GPT-4o Mini',
                    'capabilities': ['text', 'streaming'],
                    'context_window': 128000,
                },
            ],
        })

    # Ollama models (try to detect running server)
    ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{ollama_host}/api/tags', timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                ollama_models = [
                    {
                        'id': f'ollama/{model["name"]}',
                        'name': model['name'].title(),
                        'capabilities': ['text', 'streaming'],
                        'context_window': 4096,  # Default, varies by model
                    }
                    for model in data.get('models', [])
                ]
                if ollama_models:
                    providers.append({
                        'id': 'ollama',
                        'name': 'Ollama (Local)',
                        'available': True,
                        'models': ollama_models,
                    })
    except (httpx.RequestError, json.JSONDecodeError) as e:
        # Ollama not running or response is malformed, that's fine
        logger.debug(f'Could not connect to Ollama or parse response: {e}')

    return providers
