# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


from genkit.core.types import GenerateRequest
from typing import Callable, Optional, Any

PromptFn = Callable[[Optional[Any]], GenerateRequest]
