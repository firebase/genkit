# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""AI foundations for the Genkit framework.

This package provides the artificial intelligence and machine learning
capabilities of the Genkit framework. It includes:

    - Model interfaces for various AI models
    - Prompt management and templating
    - AI-specific utilities and helpers

The AI package enables seamless integration of AI models and capabilities
into applications built with Genkit.
"""


def package_name() -> str:
    """Get the fully qualified package name.

    Returns:
        The string 'genkit.ai', which is the fully qualified package name.
    """
    return 'genkit.ai'


__all__ = ['package_name']
