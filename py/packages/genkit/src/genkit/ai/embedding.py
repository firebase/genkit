# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from collections.abc import Callable

from genkit.core.typing import EmbedRequest, EmbedResponse

type EmbedderFn = Callable[[EmbedRequest], EmbedResponse]
