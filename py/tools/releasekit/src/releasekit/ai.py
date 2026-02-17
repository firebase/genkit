# Copyright 2026 Google LLC
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

"""Genkit AI integration for releasekit.

Provides the core AI infrastructure: Genkit initialization, model
fallback chain, and the ``generate_with_fallback()`` function used
by all AI features (summarization, changelog enhancement, breaking
change detection, etc.).

Key Concepts::

    ┌─────────────────────────┬────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Model fallback chain    │ A list of models to try in order. Like    │
    │                         │ having backup phone numbers — if the      │
    │                         │ first doesn't answer, try the next.       │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ generate_with_fallback  │ Try each model until one works. If none   │
    │                         │ work, return None and warn.               │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ resolve_ai_config       │ Merge CLI flags + env vars + TOML config  │
    │                         │ into a final AiConfig.                    │
    └─────────────────────────┴────────────────────────────────────────────┘

Usage::

    from releasekit.ai import get_ai, generate_with_fallback, resolve_ai_config
    from releasekit.schemas_ai import ReleaseSummary

    ai_config = resolve_ai_config(config.ai, no_ai=args.no_ai, model=args.model)
    if ai_config.enabled:
        ai = get_ai(ai_config)
        response = await generate_with_fallback(
            ai=ai,
            models=ai_config.models,
            prompt=prompt,
            output_schema=ReleaseSummary,
            config={'temperature': ai_config.temperature},
        )
        if response is not None:
            summary = response.output
"""

from __future__ import annotations

import importlib
import os
from dataclasses import replace
from typing import TYPE_CHECKING, Any, TypeVar

from genkit import Genkit
from genkit.core.typing import GenerateResponse
from releasekit.config import AiConfig
from releasekit.logging import get_logger
from releasekit.prompts import PROMPTS_DIR

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = get_logger(__name__)

T = TypeVar('T', bound='BaseModel')

#
# Maps provider name (the prefix before ``/`` in model strings like
# ``"ollama/gemma3:4b"``) to ``(module_path, class_name, extras_name)``.
#
# ``extras_name`` is the pip extras key so error messages can suggest
# ``pip install releasekit[extras_name]``.
#
# To add a new provider, add an entry here and a corresponding
# ``[project.optional-dependencies]`` section in ``pyproject.toml``.
_KNOWN_PLUGINS: dict[str, tuple[str, str, str]] = {
    'ollama': ('genkit.plugins.ollama', 'Ollama', 'ollama'),
    'google-genai': ('genkit.plugins.google_genai', 'GoogleGenai', 'google-genai'),
    'vertexai': ('genkit.plugins.vertex_ai', 'VertexAi', 'vertex-ai'),
    'anthropic': ('genkit.plugins.anthropic', 'Anthropic', 'anthropic'),
}


def _discover_plugins(
    models: list[str],
    explicit_plugins: list[str] | None = None,
) -> list[Any]:
    """Auto-discover and instantiate Genkit plugins.

    When *explicit_plugins* is provided (from ``ai.plugins`` config),
    only those plugins are loaded.  Otherwise, the provider prefix of
    each model string is used to determine which plugins are needed.

    Args:
        models: Model strings like ``["ollama/gemma3:4b"]``.
        explicit_plugins: Optional explicit list of plugin names to
            load (e.g. ``["ollama", "google-genai"]``).

    Returns:
        List of instantiated plugin objects.
    """
    if explicit_plugins:
        needed = set(explicit_plugins)
    else:
        # Derive from model prefixes.
        needed = {m.split('/')[0] for m in models if '/' in m}

    plugins: list[Any] = []
    for provider in sorted(needed):
        entry = _KNOWN_PLUGINS.get(provider)
        if entry is None:
            logger.warning(
                'ai_unknown_provider',
                provider=provider,
                hint=(
                    f"Provider '{provider}' is not in the known plugin registry. "
                    'If this is a custom provider, ensure its Genkit plugin is '
                    'installed and registered.'
                ),
            )
            continue

        module_path, class_name, extras_name = entry
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            plugins.append(cls())
            logger.debug('ai_plugin_loaded', provider=provider)
        except ImportError:
            logger.warning(
                'ai_plugin_not_installed',
                provider=provider,
                hint=f"Install with: pip install 'releasekit[{extras_name}]'",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                'ai_plugin_init_failed',
                provider=provider,
                error=str(exc),
                hint=f'Plugin {provider} failed to initialize. Check configuration.',
            )

    return plugins


# Singleton Genkit instance, lazily initialized.
_ai_instance: Genkit | None = None


def get_ai(config: AiConfig) -> Genkit:
    """Get or create the singleton Genkit instance.

    Plugins are auto-discovered from model prefixes in
    ``config.models``, or loaded explicitly from ``config.plugins``
    when set.  Missing plugins produce a warning with an install
    command rather than a hard failure.

    Args:
        config: AI configuration (used for first-time init only).

    Returns:
        Configured Genkit instance.
    """
    global _ai_instance  # noqa: PLW0603
    if _ai_instance is not None:
        return _ai_instance

    from genkit.blocks.prompt import load_prompt_folder  # noqa: PLC0415

    plugins = _discover_plugins(
        config.models,
        explicit_plugins=config.plugins or None,
    )
    _ai_instance = Genkit(plugins=plugins)

    # Load .prompt files from releasekit/prompts/ directory.
    if PROMPTS_DIR.is_dir():
        load_prompt_folder(_ai_instance.registry, PROMPTS_DIR, ns='releasekit')

    return _ai_instance


def reset_ai() -> None:
    """Reset the singleton Genkit instance (for testing)."""
    global _ai_instance  # noqa: PLW0603
    _ai_instance = None


async def generate_with_fallback(
    ai: Genkit,
    models: list[str],
    prompt: str,
    output_schema: type[T],
    config: dict | None = None,
) -> GenerateResponse | None:
    """Try each model in order. Return None if all fail.

    This is the core function for all AI features. It iterates the
    model fallback chain, logging a warning for each failure, and
    returns ``None`` if every model is exhausted — allowing the
    caller to fall back to non-AI behavior.

    Args:
        ai: Genkit instance (from :func:`get_ai`).
        models: Ordered list of ``"provider/model"`` strings.
        prompt: The prompt text to send to the model.
        output_schema: Pydantic model class for structured output.
        config: Optional generation config (temperature, etc.).

    Returns:
        The :class:`GenerateResponse` from the first successful model,
        or ``None`` if all models failed.
    """
    from genkit.ai import Output  # noqa: PLC0415

    for model in models:
        try:
            response = await ai.generate(
                model=model,
                prompt=prompt,
                output=Output(schema=output_schema),
                config=config or {},
            )
            logger.info('ai_model_success', model=model)
            return response
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                'ai_model_unavailable',
                model=model,
                error=str(exc),
            )

    # All models exhausted.
    logger.warning(
        'ai_all_models_failed',
        models=models,
        hint="Falling back to non-AI behavior. Run 'ollama pull gemma3:4b' to enable AI.",
    )
    return None


def resolve_ai_config(
    base: AiConfig,
    *,
    no_ai: bool = False,
    model: str | None = None,
    codename_theme: str | None = None,
) -> AiConfig:
    """Merge CLI flags and env vars into the final AI config.

    Priority order (highest wins):
    1. ``--model`` CLI flag (overrides models list with single entry)
    2. ``--codename-theme`` CLI flag (overrides codename theme)
    3. ``--no-ai`` CLI flag (disables all AI)
    4. ``RELEASEKIT_AI_MODELS`` env var (comma-separated model list)
    5. ``RELEASEKIT_NO_AI`` env var (``1`` or ``true`` disables)
    6. ``releasekit.toml`` ``[ai]`` section (the ``base`` param)

    Args:
        base: AiConfig from ``releasekit.toml``.
        no_ai: ``True`` if ``--no-ai`` CLI flag was passed.
        model: Model override from ``--model`` CLI flag.
        codename_theme: Theme override from ``--codename-theme`` CLI flag.

    Returns:
        Resolved :class:`AiConfig`.
    """
    # Start from the TOML config.
    enabled = base.enabled
    models = list(base.models)
    theme = base.codename_theme

    # Layer 4: env var RELEASEKIT_NO_AI.
    env_no_ai = os.environ.get('RELEASEKIT_NO_AI', '').lower()
    if env_no_ai in ('1', 'true', 'yes'):
        enabled = False

    # Layer 3: env var RELEASEKIT_AI_MODELS.
    env_models = os.environ.get('RELEASEKIT_AI_MODELS', '').strip()
    if env_models:
        models = [m.strip() for m in env_models.split(',') if m.strip()]

    # Layer 2: --no-ai CLI flag.
    if no_ai:
        enabled = False

    # Layer 1: --model CLI flag (single model, bypasses chain).
    if model:
        models = [model]

    # --codename-theme CLI flag.
    if codename_theme is not None:
        theme = codename_theme

    return replace(base, enabled=enabled, models=models, codename_theme=theme)
