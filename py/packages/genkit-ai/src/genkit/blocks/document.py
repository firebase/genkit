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

"""Document model for the Genkit framework.

This module provides types for creating and managing multi-modal documents in
Genkit.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from genkit.typing import (
    DocumentData,
    DocumentPart,
    Embedding,
    Media,
    MediaPart,
    TextPart,
)

TEXT_DATA_TYPE: str = 'text'


class Document(DocumentData):
    """Represents document content along with its metadata.

    This object can be embedded, indexed or retrieved. Each document can contain
    multiple parts (for example text and an image).
    """

    def __init__(
        self,
        content: list[DocumentPart],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize Document object."""
        doc_content = deepcopy(content)
        doc_metadata = deepcopy(metadata)
        super().__init__(content=doc_content, metadata=doc_metadata)

    @staticmethod
    def from_document_data(document_data: DocumentData) -> Document:
        """Construct a Document from DocumentData."""
        return Document(
            content=document_data.content, metadata=document_data.metadata
        )

    @staticmethod
    def from_text(
        text: str, metadata: dict[str, Any] | None = None
    ) -> Document:
        """Construct a Document from a single text part."""
        return Document(content=[DocumentPart(text=text)], metadata=metadata)

    @staticmethod
    def from_media(
        url: str,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Construct a Document from a single media part."""
        return Document(
            content=[
                DocumentPart(media=Media(url=url, content_type=content_type))
            ],
            metadata=metadata,
        )

    @staticmethod
    def from_data(
        data: str,
        data_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Construct a Document from a single media part."""
        if data_type == TEXT_DATA_TYPE:
            return Document.from_text(data, metadata)
        return Document.from_media(data, data_type, metadata)

    def text(self) -> str:
        """Concatenates all `text` parts with no delimiter."""
        return ''.join(
            p.root.text if p.root.text is not None else '' for p in self.content
        )

    def media(self) -> list[Media]:
        """Media array getter."""
        media_parts = [part.root.media for part in self.content]
        return list(filter(lambda m: m is not None, media_parts))

    def data(self) -> str:
        """Gets the first item in the document. Either text or media url."""
        if self.text():
            return self.text()

        if self.media():
            return self.media()[0].url

        return ''

    def data_type(self) -> str | None:
        """Gets the content_type of the data that is returned by data()."""
        if self.text():
            return TEXT_DATA_TYPE

        if self.media() and self.media()[0].content_type:
            return self.media()[0].content_type

        return None

    def get_embedding_documents(
        self, embeddings: list[Embedding]
    ) -> list[Document]:
        """Creates documents from embeddings.

        Embedders may return multiple embeddings for a single document. But
        storage still requires a 1:1 relationship. So we create an array of
        Documents from a single document - one per embedding.
        """
        documents = []
        for embedding in embeddings:
            content = deepcopy(self.content)
            metadata = deepcopy(self.metadata)
            if embedding.metadata:
                if not metadata:
                    metadata = {}
                metadata['embedMetadata'] = embedding.metadata
            documents.append(Document(content=content, metadata=metadata))
        check_unique_documents(documents)
        return documents


def check_unique_documents(documents: list[Document]) -> bool:
    """Check for unique documents in given array.

    Unique documents are important because we key
    our vector storage on the Md5 hash of the JSON string of document
    So if we have multiple duplicate documents with
    different embeddings, we will either skip or overwrite
    those entries and lose embedding information.
    Boolean return value for testing only.
    """
    seen = set()
    for doc in documents:
        if doc.model_dump_json() in seen:
            print(
                """
                Warning: embedding documents are not unique.
                Are you missing embed metadata?
                """
            )
            return False
        seen.add(doc.model_dump_json())
    return True
