# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Core foundations for the Genkit framework.

This package provides the fundamental building blocks and abstractions used
throughout the Genkit framework. It includes:

    - Action system for defining and managing callable functions
    - Plugin architecture for extending framework functionality
    - Registry for managing resources and actions
    - Tracing and telemetry for monitoring and debugging
    - Schema types for data validation and serialization
"""


def package_name() -> str:
    """Get the fully qualified package name.

    Returns:
        The string 'genkit.core', which is the fully qualified package name.
    """
    return 'genkit.core'


__all__ = ['package_name']
