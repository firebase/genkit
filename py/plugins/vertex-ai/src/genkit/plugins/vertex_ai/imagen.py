# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum
from typing import Any

from genkit.core.schema_types import GenerateRequest, GenerateResponse
from vertexai.preview.vision_models import ImageGenerationModel


class ImagenVersion(StrEnum):
    IMAGEN3 = 'imagen-3.0-generate-002'
    IMAGEN3_FAST = 'imagen-3.0-fast-generate-001'
    IMAGEN2 = 'imagegeneration@006'
    IMAGEN1 = 'imagegeneration@002'


class Imagen:
    def __init__(self, version):
        self.version = version

    @property
    def image_model(self) -> ImageGenerationModel:
        return ImageGenerationModel.from_pretrained(self.version)

    def handle_request(self, request: GenerateRequest) -> GenerateResponse:
        """Function to be stored in the registry."""

    @property
    def model_metadata(self) -> dict[str, Any]:
        return {}
