# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
OpenAI Plugin for Genkit.
"""

from .openai_plugin import OpenAI, openai_model


def package_name() -> str:
    return 'genkit.plugins.openai_compat'


__all__ = ['OpenAI', 'openai_model', 'package_name']
