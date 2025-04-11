# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import hashlib
import json

import structlog

from genkit.core.error import GenkitError
from genkit.core.typing import GenerateRequest
from genkit.plugins.google_genai.models.context_caching.constants import (
    CONTEXT_CACHE_SUPPORTED_MODELS,
    INVALID_ARGUMENT_MESSAGES,
)

logger = structlog.getLogger(__name__)


def generate_cache_key(request: GenerateRequest) -> str:
    """Generates context cache key by hashing the given request instance

    Args:
        request: `GenerateRequest` instance to hash

    Returns:
        Generated cache key string
    """
    return hashlib.sha256(json.dumps(request.model_dump(), sort_keys=True).encode()).hexdigest()


def validate_context_cache_request(request: GenerateRequest, model_name: str) -> bool:
    """Verifies that the context cache request could be processed for the request

    Args:
        request: `GenerateRequest` instance to check
        model_name: Name of the generation model to check

    Returns:
        True if the context cache request could be processed for the request, False otherwise
    """
    if not model_name or model_name not in CONTEXT_CACHE_SUPPORTED_MODELS:
        raise GenkitError(
            status='INVALID_ARGUMENT',
            message=INVALID_ARGUMENT_MESSAGES['modelVersion'],
        )
    if request.tools:
        raise GenkitError(
            status='INVALID_ARGUMENT',
            message=INVALID_ARGUMENT_MESSAGES['tools'],
        )
    # TODO: add this check when code execution is added to Genkit
    # if request.config and request.config.get("codeExecution"):
    #     raise GenkitError(
    #         status="INVALID_ARGUMENT",
    #         message=INVALID_ARGUMENT_MESSAGES["codeExecution"],
    #     )
    return True
