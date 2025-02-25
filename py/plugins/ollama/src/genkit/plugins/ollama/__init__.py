# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Ollama Plugin for Genkit."""


def package_name() -> str:
    """Get the package name for the Ollama plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.ollama'


__all__ = ['package_name']
