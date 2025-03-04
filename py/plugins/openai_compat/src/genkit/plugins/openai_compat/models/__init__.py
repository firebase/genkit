# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
OpenAI Models for Genkit.
"""

from .handler import OpenAIModelHandler
from .model import OpenAIModel
from .model_info import SUPPORTED_OPENAI_MODELS


def package_name() -> str:
    return 'genkit.plugins.openai_compat.models'


__all__ = [
    'OpenAIModel',
    'SUPPORTED_OPENAI_MODELS',
    'OpenAIModelHandler',
    'package_name',
]
