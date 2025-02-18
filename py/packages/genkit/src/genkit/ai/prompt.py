# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


from collections.abc import Callable
from typing import Any

from genkit.core.schema_types import GenerateRequest

PromptFn = Callable[[Any | None], GenerateRequest]
