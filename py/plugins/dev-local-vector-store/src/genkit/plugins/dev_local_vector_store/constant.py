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


from typing import Any

from pydantic import BaseModel

from genkit.types import DocumentData, Embedding


class Params(BaseModel):
    index_name: str
    embedder: str
    embedder_options: dict[str, Any] | None = None


class DbValue(BaseModel):
    doc: DocumentData
    embedding: Embedding
