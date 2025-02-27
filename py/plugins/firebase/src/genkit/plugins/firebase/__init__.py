# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Firebase Plugin for Genkit."""


def package_name() -> str:
    """Get the package name for the Firebase plugin.

    Returns:
        The fully qualified package name as a string.
    """
    return 'genkit.plugins.firebase'


__all__ = ['package_name']
