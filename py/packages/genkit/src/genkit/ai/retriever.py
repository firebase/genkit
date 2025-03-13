# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Retriever type definitions for the Genkit framework.

This module defines the type interfaces for retrievers in the Genkit framework.
Retrievers are used for fetching Genkit documents from a datastore, given a
query. These documents can then be used to provide additional context to models
to accomplish a task.
"""

from typing import Any, Callable
from xml.dom.minidom import Document

from genkit.core.typing import RetrieverResponse

# User-provided retriever function that queries the datastore
type RetrieverFn[T] = Callable[[Document, T], RetrieverResponse]
