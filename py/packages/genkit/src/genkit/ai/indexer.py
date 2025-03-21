# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from typing import Callable

from genkit.core.typing import Docs

type IndexerFn[T] = Callable[[Docs, T], None]
