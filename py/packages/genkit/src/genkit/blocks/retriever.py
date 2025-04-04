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

"""Retriever type definitions for the Genkit framework.

This module defines the type interfaces for retrievers in the Genkit framework.
Retrievers are used for fetching Genkit documents from a datastore, given a
query. These documents can then be used to provide additional context to models
to accomplish a task.
"""

from collections.abc import Callable
from typing import Generic, TypeVar

from genkit.blocks.document import Document
from genkit.core.typing import RetrieverResponse

T = TypeVar('T')
# type RetrieverFn[T] = Callable[[Document, T], RetrieverResponse]
RetrieverFn = Callable[[Document, T], RetrieverResponse]


class Retriever(Generic[T]):
    def __init__(
        self,
        retriever_fn: RetrieverFn[T],
    ):
        self.retriever_fn = retriever_fn
