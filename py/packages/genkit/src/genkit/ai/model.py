# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable

from genkit.core.schema_types import GenerateRequest, GenerateResponse

ModelFn = Callable[[GenerateRequest], GenerateResponse]
