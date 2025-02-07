# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable
from pydantic import BaseModel
from genkit.core.schemas import GenerateRequest, GenerateResponse, ModelInfo


ModelFn = Callable[[GenerateRequest], GenerateResponse]


class ModelReference(BaseModel):
  name: str
  info: ModelInfo
