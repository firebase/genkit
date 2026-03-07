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

"""Multi-modal document types for Genkit."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from genkit._core._typing import (
    DocumentData,
    DocumentPart,
    Media,
    MediaPart,
    TextPart,
)

TEXT_DATA_TYPE: str = 'text'


class Document(DocumentData):
    """Multi-part document that can be embedded, indexed, or retrieved."""

    def __init__(
        self,
        content: list[DocumentPart],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize with content parts and optional metadata."""
        doc_content = deepcopy(content)
        doc_metadata = deepcopy(metadata)
        super().__init__(content=doc_content, metadata=doc_metadata)

    @staticmethod
    def from_text(text: str, metadata: dict[str, Any] | None = None) -> Document:
        """Create a document from a text string."""
        # NOTE: DocumentPart is a RootModel requiring root=TextPart(...) syntax.
        return Document(content=[DocumentPart(root=TextPart(text=text))], metadata=metadata)

    @staticmethod
    def from_media(
        url: str,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Create a document from a media URL."""
        return Document(
            # NOTE: DocumentPart is a RootModel requiring root=MediaPart(...) syntax.
            # Using contentType alias for ty type checker compatibility.
            content=[DocumentPart(root=MediaPart(media=Media(url=url, content_type=content_type)))],
            metadata=metadata,
        )

    @staticmethod
    def from_data(
        data: str,
        data_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Create a document from data, inferring text vs media from data_type."""
        if data_type == TEXT_DATA_TYPE:
            return Document.from_text(data, metadata)
        return Document.from_media(data, data_type, metadata)

    def text(self) -> str:
        """Concatenate all text parts."""
        texts = []
        for p in self.content:
            # Handle both TextPart objects and potential dict representations
            # p.root is the underlying TextPart or MediaPart
            part = p.root if hasattr(p, 'root') else p
            text_val = getattr(part, 'text', None)
            if isinstance(text_val, str):
                texts.append(text_val)
        return ''.join(texts)

    def media(self) -> list[Media]:
        """Get all media parts."""
        return [
            part.root.media for part in self.content if isinstance(part.root, MediaPart) and part.root.media is not None
        ]

    def data(self) -> str:
        """Primary data: text if available, otherwise first media URL."""
        if self.text():
            return self.text()

        if self.media():
            return self.media()[0].url

        return ''

    def data_type(self) -> str | None:
        """Type of primary data: 'text' or first media's content type."""
        if self.text():
            return TEXT_DATA_TYPE

        if self.media() and self.media()[0].content_type:
            return self.media()[0].content_type

        return None
