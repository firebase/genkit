# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Google AI Plugin for Genkit.

This plugin provides integration with Google AI services and models.
"""

from genkit.plugins.google_ai.google_ai import (
    GoogleAi,
    GoogleAiPluginOptions,
    googleai_name,
)


def package_name() -> str:
    """Get the package name for the Google AI plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.google_ai'


__all__ = ['package_name', 'GoogleAi', 'GoogleAiPluginOptions', 'googleai_name']
