# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable

from genkit.core.schemas import GenerateRequest, GenerateResponse

ModelFn = Callable[[GenerateRequest], GenerateResponse]
