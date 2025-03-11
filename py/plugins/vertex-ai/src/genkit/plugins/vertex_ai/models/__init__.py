# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Google Cloud Vertex AI Models for Genkit."""


def package_name() -> str:
    """Get the package name for the Vertex AI models subpackage.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.vertex_ai.models'


__all__ = ['package_name']
