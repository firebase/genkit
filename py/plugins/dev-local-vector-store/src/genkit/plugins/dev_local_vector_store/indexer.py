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


import asyncio
import json
from hashlib import md5

from genkit.blocks.document import Document
from genkit.plugins.dev_local_vector_store.constant import DbValue
from genkit.plugins.dev_local_vector_store.local_vector_store_api import (
    LocalVectorStoreAPI,
)
from genkit.types import Docs, Embedding


class DevLocalVectorStoreIndexer(LocalVectorStoreAPI):
    async def index(self, docs: Docs) -> None:
        data = self._load_filestore()
        tasks = []

        for doc_data in docs.root:
            tasks.append(
                self.process_document(
                    document=Document.from_document_data(document_data=doc_data),
                    data=data,
                )
            )

        await asyncio.gather(*tasks)

        with open(self.index_file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    async def process_document(self, document: Document, data: dict[str, DbValue]) -> None:
        embeddings = await self.ai.embed(
            embedder=self.params.embedder,
            documents=[document],
            options=self.params.embedder_options,
        )
        embedding_docs = document.get_embedding_documents(embeddings.embeddings)

        for embedding, emb_doc in zip(embeddings, embedding_docs, strict=False):
            self._add_document(data=data, embedding=embedding, doc=emb_doc)

    def _add_document(
        self,
        data: dict[str, DbValue],
        embedding: Embedding,
        doc: Document,
    ) -> None:
        data_str = json.dumps(self._serialize_data(data=data), ensure_ascii=False)
        _idx = md5(data_str.encode('utf-8')).hexdigest()
        if _idx not in data:
            data[_idx] = DbValue(
                doc=doc,
                embedding=embedding,
            )
