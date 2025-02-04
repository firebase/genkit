# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum
from typing import List, Dict, Optional

from pydantic import BaseModel, HttpUrl, Field

from genkit.plugins.ollama.constants import DEFAULT_OLLAMA_SERVER_URL


class OllamaAPITypes(StrEnum):
    CHAT = 'chat'
    GENERATE = 'generate'


class ModelDefinition(BaseModel):
    name: str
    api_type: OllamaAPITypes


class EmbeddingModelDefinition(BaseModel):
    name: str
    dimensions: int


class OllamaPluginParams(BaseModel):
    models: List[ModelDefinition] = Field(default_factory=list)
    embedders: List[EmbeddingModelDefinition] = Field(default_factory=list)
    server_address: HttpUrl = Field(default=HttpUrl(DEFAULT_OLLAMA_SERVER_URL))
    request_headers: Optional[Dict[str, str]] = None
