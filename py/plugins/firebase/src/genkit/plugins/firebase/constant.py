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

from pydantic import BaseModel
from typing import Callable, Optional, Any, Dict
from enum import StrEnum

class DistanceMeasure(StrEnum):
    """Enumeration of supported distance measures."""
    COSINE = 'COSINE'
    EUCLIDEAN = 'EUCLIDEAN'
    DOT_PRODUCT = 'DOT_PRODUCT'

class FirestoreRetrieverConfig(BaseModel):
    """The name of the retriever."""
    name:str
    """The name of the Firestore collection to query."""
    collection: str
    """The name of the field containing the vector embeddings."""
    vector_field: str
    """The name of the field containing the document content, you wish to return."""
    content_field: str
    """The embedder to use with this retriever."""
    embedder: str
    """The distance measure to use when comparing vectors. Defaults to 'COSINE'."""
    distance_measure: DistanceMeasure = DistanceMeasure.COSINE
    """The Firestore database instance from which to query."""
    firestore_client: firestore.client
    """Optional list of metadata fields to include, or a function to extract metadata.
    If None, all fields except vector and content are included."""
    metadata_fields: Optional[list[str] | Callable[[firestore.DocumentSnapshot], Dict[str, Any]]] = None

