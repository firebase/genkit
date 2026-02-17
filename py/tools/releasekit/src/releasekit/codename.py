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

"""AI-generated release codenames using Genkit.

Generates themed release codenames (like Debian's Toy Story names,
Ubuntu's alliterative animals, or macOS's California landmarks).
The theme is configurable via ``ai.codename_theme`` in
``releasekit.toml`` or the ``--codename-theme`` CLI flag.

Key Concepts::

    ┌─────────────────────────┬────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Codename theme          │ A category for names. Like picking names  │
    │                         │ from a hat labeled "mountains" or          │
    │                         │ "animals" or "space missions".             │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ generate_codename       │ Ask AI to pick a name from the theme      │
    │                         │ that fits the release's character.         │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Previous codenames      │ Passed to the AI so it doesn't repeat     │
    │                         │ names. Like crossing off used names.       │
    └─────────────────────────┴────────────────────────────────────────────┘

Built-in themes::

    mountains   — Alpine peaks (Denali, Rainier, Fuji, Elbrus)
    animals     — Alliterative animals (Agile Antelope, Bold Bison)
    space       — Celestial bodies and missions (Andromeda, Voyager)
    mythology   — Gods, heroes, legends (Athena, Prometheus, Valkyrie)
    gems        — Precious stones (Topaz, Sapphire, Obsidian)
    weather     — Meteorological phenomena (Aurora, Monsoon, Zephyr)
    cities      — World cities (Kyoto, Marrakech, Reykjavik)

Any custom string is also accepted (e.g. ``"deep sea creatures"``).

Usage::

    from releasekit.codename import generate_codename

    codename = await generate_codename(
        ai_config=config.ai,
        version='0.6.0',
        highlights=['New Cloudflare plugin', 'Faster streaming'],
        previous_codenames=['Denali', 'Rainier'],
    )
    if codename is not None:
        print(f'{codename.codename} — {codename.tagline}')
"""

from __future__ import annotations

from pathlib import Path

from releasekit._wordfilter import WordFilter, get_default_filter, get_filter_async
from releasekit.ai import generate_with_fallback, get_ai
from releasekit.config import AiConfig
from releasekit.logging import get_logger
from releasekit.prompts import CODENAME_SYSTEM_PROMPT, build_codename_prompt
from releasekit.schemas_ai import ReleaseCodename

logger = get_logger(__name__)

# File storing previously used codenames (one per line).
_CODENAMES_FILE = '.releasekit/codenames.txt'

# These are curated to produce wholesome, family-friendly codenames.
# Custom themes are allowed but go through the same safety check.
SAFE_BUILTIN_THEMES: frozenset[str] = frozenset({
    'animals',
    'birds',
    'butterflies',
    'cities',
    'clouds',
    'colors',
    'constellations',
    'coral',
    'deserts',
    'flowers',
    'forests',
    'galaxies',
    'gems',
    'islands',
    'lakes',
    'lighthouses',
    'mountains',
    'mythology',
    'nebulae',
    'oceans',
    'rivers',
    'seasons',
    'space',
    'trees',
    'volcanoes',
    'weather',
    'wildflowers',
})

# Words that must never appear in a codename (case-insensitive).
# Loaded lazily from ``data/blocked_words.txt`` via the shared singleton.
# The Aho-Corasick automaton provides O(n) scanning with word-boundary semantics.


def _is_safe_codename(codename: str, word_filter: WordFilter | None = None) -> bool:
    """Check if a codename passes the post-generation safety filter.

    This is a defense-in-depth check. The system prompt instructs the
    model to generate safe names, but this catches obvious failures.
    Uses a trie-based word filter loaded from ``data/blocked_words.txt``
    for O(n) scanning with word-boundary semantics.

    Args:
        codename: The generated codename string.
        word_filter: Optional custom :class:`WordFilter`.  When ``None``,
            falls back to :func:`get_default_filter`.

    Returns:
        ``True`` if the codename is safe, ``False`` otherwise.
    """
    if not codename or not codename.strip():
        return False
    wf = word_filter or get_default_filter()
    return not wf.contains_blocked(codename)


def _load_previous_codenames(workspace_root: Path) -> list[str]:
    """Load previously used codenames from the workspace."""
    path = workspace_root / _CODENAMES_FILE
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding='utf-8').strip().splitlines()
        return [line.strip() for line in lines if line.strip()]
    except OSError:
        return []


def _save_codename(workspace_root: Path, codename: str) -> None:
    """Append a codename to the history file."""
    path = workspace_root / _CODENAMES_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as f:
            f.write(f'{codename}\n')
        logger.debug('codename_saved', codename=codename, path=str(path))
    except OSError as exc:
        logger.warning('codename_save_failed', path=str(path), error=str(exc))


async def generate_codename(
    *,
    ai_config: AiConfig,
    version: str = '',
    highlights: list[str] | None = None,
    workspace_root: Path | None = None,
) -> ReleaseCodename | None:
    """Generate a themed release codename using AI.

    Uses the model fallback chain from ``ai_config.models``. Previously
    used codenames are loaded from ``.releasekit/codenames.txt`` and
    passed to the AI to avoid duplicates.

    Args:
        ai_config: Resolved AI configuration.
        version: The version string (e.g. ``"0.6.0"``).
        highlights: Top release highlights to inspire the tagline.
        workspace_root: Path to the workspace root (for codename
            history). If ``None``, no history is loaded or saved.

    Returns:
        A :class:`ReleaseCodename` if AI succeeds, or ``None`` if
        all models fail or codenames are disabled.
    """
    if not ai_config.enabled:
        logger.debug('ai_disabled', feature='codename')
        return None

    if not ai_config.features.codename:
        logger.debug('ai_feature_disabled', feature='codename')
        return None

    theme = ai_config.codename_theme
    if not theme:
        logger.debug('codename_no_theme')
        return None

    # Load previous codenames to avoid duplicates.
    previous: list[str] = []
    if workspace_root is not None:
        previous = _load_previous_codenames(workspace_root)

    # Build prompt.
    user_prompt = build_codename_prompt(
        theme=theme,
        version=version,
        highlights=highlights,
        previous_codenames=previous if previous else None,
    )
    full_prompt = f'{CODENAME_SYSTEM_PROMPT}\n\n{user_prompt}'

    # Generate with fallback chain.
    ai = get_ai(ai_config)
    response = await generate_with_fallback(
        ai=ai,
        models=ai_config.models,
        prompt=full_prompt,
        output_schema=ReleaseCodename,
        config={
            'temperature': 0.8,  # Higher temperature for creativity.
            'maxOutputTokens': 256,
        },
    )

    if response is None:
        return None

    # Layer 1: Model-level safety — Gemini's own safety filters.
    # If the model flagged the response as unsafe, discard it.
    if hasattr(response, 'finish_reason') and response.finish_reason == 'blocked':
        logger.warning(
            'codename_model_safety_blocked',
            theme=theme,
            finish_reason=str(response.finish_reason),
            hint='Model safety filters blocked the response. Discarding.',
        )
        return None

    result: ReleaseCodename = response.output  # type: ignore[attr-defined]

    # Fill in the theme if the model didn't.
    if not result.theme:
        result = result.model_copy(update={'theme': theme})

    # Post-generation safety check.
    wf = await get_filter_async(ai_config.blocklist_file, workspace_root)
    if not _is_safe_codename(result.codename, wf):
        logger.warning(
            'codename_safety_rejected',
            codename=result.codename,
            theme=theme,
            hint='AI generated an unsafe codename. Discarding.',
        )
        return None

    # Also check the tagline.
    if result.tagline and not _is_safe_codename(result.tagline, wf):
        # Keep the codename but strip the unsafe tagline.
        result = result.model_copy(update={'tagline': ''})
        logger.warning(
            'codename_tagline_safety_rejected',
            codename=result.codename,
            theme=theme,
        )

    logger.info(
        'codename_generated',
        codename=result.codename,
        theme=result.theme,
        tagline=result.tagline,
    )

    # Save to history.
    if workspace_root is not None and result.codename:
        _save_codename(workspace_root, result.codename)

    return result
