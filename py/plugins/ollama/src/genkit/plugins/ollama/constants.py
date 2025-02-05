# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
from enum import StrEnum

DEFAULT_OLLAMA_SERVER_URL = 'http://127.0.0.1:11434'


class OllamaAPITypes(StrEnum):
    CHAT = 'chat'
    GENERATE = 'generate'
