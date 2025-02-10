# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


from typing import Callable, Optional, Any
from genkit.core.schemas import GenerateRequest


PromptFn = Callable[[Optional[Any]], GenerateRequest]
