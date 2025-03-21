# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
from typing import Any

from pydantic import BaseModel

from genkit.core.typing import DocumentData, Embedding


class Params(BaseModel):
    index_name: str
    embedder: str
    embedder_options: dict[str, Any] | None = None


class DbValue(BaseModel):
    doc: DocumentData
    embedding: Embedding
