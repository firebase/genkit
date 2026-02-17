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

"""AI-powered changelog summarization using Genkit.

Summarizes raw changelogs into structured :class:`ReleaseSummary`
objects using the model fallback chain. Results are cached by
content hash to avoid re-summarizing unchanged changelogs.

Key Concepts::

    ┌─────────────────────────┬────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ summarize_changelogs    │ Takes raw changelog text and returns a    │
    │                         │ structured summary. Like asking someone   │
    │                         │ to read a long report and give you the    │
    │                         │ key bullet points.                        │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Content-hash caching    │ If the changelog hasn't changed, reuse   │
    │                         │ the previous summary. Like remembering    │
    │                         │ the answer to a question you already      │
    │                         │ asked.                                    │
    └─────────────────────────┴────────────────────────────────────────────┘

Usage::

    from releasekit.summarize import summarize_changelogs

    summary = await summarize_changelogs(
        changelog_text=raw_changelog,
        ai_config=config.ai,
        workspace_root=Path('/path/to/workspace'),
    )
    if summary is not None:
        print(summary.overview)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from releasekit._wordfilter import get_filter_async
from releasekit.ai import generate_with_fallback, get_ai
from releasekit.config import AiConfig
from releasekit.logging import get_logger
from releasekit.prompts import SYSTEM_PROMPT, build_user_prompt
from releasekit.schemas_ai import ReleaseSummary

logger = get_logger(__name__)

# Cache directory relative to workspace root.
_CACHE_DIR = '.releasekit/cache/summaries'


def _content_hash(text: str) -> str:
    """Compute a SHA-256 hash of the input text."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _cache_path(workspace_root: Path, content_hash: str) -> Path:
    """Return the cache file path for a given content hash."""
    cache_dir = workspace_root / _CACHE_DIR
    return cache_dir / f'{content_hash}.json'


def _load_cached(workspace_root: Path, content_hash: str) -> ReleaseSummary | None:
    """Load a cached summary if it exists and is valid."""
    path = _cache_path(workspace_root, content_hash)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return ReleaseSummary.model_validate(data)
    except Exception:  # noqa: BLE001
        logger.debug('cache_invalid', path=str(path))
        return None


def _save_cached(
    workspace_root: Path,
    content_hash: str,
    summary: ReleaseSummary,
) -> None:
    """Save a summary to the cache."""
    path = _cache_path(workspace_root, content_hash)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            summary.model_dump_json(indent=2),
            encoding='utf-8',
        )
        logger.debug('cache_saved', path=str(path))
    except OSError as exc:
        logger.warning('cache_save_failed', path=str(path), error=str(exc))


async def summarize_changelogs(
    *,
    changelog_text: str,
    ai_config: AiConfig,
    workspace_root: Path,
    package_count: int = 0,
    commit_count: int = 0,
    days_since_last: int = 0,
) -> ReleaseSummary | None:
    """Summarize raw changelogs into a structured release summary.

    Uses the model fallback chain from ``ai_config.models``. Results
    are cached by content hash under ``.releasekit/cache/summaries/``.

    Args:
        changelog_text: Raw changelog entries (conventional commits,
            grouped by package).
        ai_config: Resolved AI configuration.
        workspace_root: Path to the workspace root (for caching).
        package_count: Number of packages with changes.
        commit_count: Total number of commits.
        days_since_last: Days since the last release.

    Returns:
        A :class:`ReleaseSummary` if AI succeeds, or ``None`` if all
        models fail (caller should fall back to non-AI behavior).
    """
    if not ai_config.enabled:
        logger.debug('ai_disabled', feature='summarize')
        return None

    if not ai_config.features.summarize:
        logger.debug('ai_feature_disabled', feature='summarize')
        return None

    if not changelog_text.strip():
        logger.debug('ai_empty_changelog')
        return None

    # Check cache first.
    ch = _content_hash(changelog_text)
    cached = _load_cached(workspace_root, ch)
    if cached is not None:
        logger.info('ai_cache_hit', content_hash=ch[:12])
        return cached

    # Build prompt.
    user_prompt = build_user_prompt(
        changelog_text=changelog_text,
        package_count=package_count,
        commit_count=commit_count,
        days_since_last=days_since_last,
    )
    full_prompt = f'{SYSTEM_PROMPT}\n\n{user_prompt}'

    # Generate with fallback chain.
    ai = get_ai(ai_config)
    response = await generate_with_fallback(
        ai=ai,
        models=ai_config.models,
        prompt=full_prompt,
        output_schema=ReleaseSummary,
        config={
            'temperature': ai_config.temperature,
            'maxOutputTokens': ai_config.max_output_tokens,
        },
    )

    if response is None:
        return None

    # Layer 1: Model-level safety — Gemini's own safety filters.
    if hasattr(response, 'finish_reason') and response.finish_reason == 'blocked':
        logger.warning(
            'summary_model_safety_blocked',
            finish_reason=str(response.finish_reason),
            hint='Model safety filters blocked the summary response.',
        )
        return None

    summary: ReleaseSummary = response.output  # type: ignore[attr-defined]

    # Layer 2: Scan AI-generated text fields for harmful content.
    wf = await get_filter_async(ai_config.blocklist_file, workspace_root)
    if wf.contains_blocked(summary.overview):
        logger.warning(
            'summary_blocked_content',
            field='overview',
            hint='AI-generated summary overview contains blocked content. Discarding.',
        )
        return None

    # Scan highlights and strip any that contain blocked content.
    if summary.highlights:
        safe_highlights = []
        for h in summary.highlights:
            if wf.contains_blocked(h):
                logger.warning(
                    'summary_highlight_blocked',
                    hint='AI-generated highlight contains blocked content. Redacting.',
                )
            else:
                safe_highlights.append(h)
        if safe_highlights != summary.highlights:
            summary = summary.model_copy(update={'highlights': safe_highlights})

    logger.info('ai_summary_generated', overview_len=len(summary.overview))

    # Cache the result.
    _save_cached(workspace_root, ch, summary)

    return summary
