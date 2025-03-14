# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
OpenAI Compatible model provider for Genkit.
"""

from .openai_plugin import OpenAI, openai_model
from .typing import OpenAIConfig


def package_name() -> str:
    return 'genkit.plugins.compat_oai'


__all__ = ['OpenAI', 'OpenAIConfig', 'openai_model', 'package_name']
