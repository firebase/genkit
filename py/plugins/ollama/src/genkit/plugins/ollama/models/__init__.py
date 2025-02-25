# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Ollama Models for Genkit."""


def package_name() -> str:
    """Get the package name for the Ollama models subpackage.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.ollama.models'


__all__ = ['package_name']
