# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable

from pydantic import BaseModel


class EmbedRequest(BaseModel):
    documents: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


EmbedderFn = Callable[[EmbedRequest], EmbedResponse]
