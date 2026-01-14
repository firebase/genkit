# Copyright 2026 Google LLC
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

"""Tests for the reranker module.

This module contains tests for the reranker functionality including
RankedDocument, define_reranker, and rerank functions.
"""

import pytest

from genkit.blocks.document import Document
from genkit.blocks.reranker import (
    RankedDocument,
    RerankerInfo,
    RerankerOptions,
    RerankerRef,
    create_reranker_ref,
    define_reranker,
    rerank,
    reranker_action_metadata,
)
from genkit.core.action.types import ActionKind
from genkit.core.registry import Registry
from genkit.core.typing import (
    DocumentData,
    DocumentPart,
    RankedDocumentData,
    RankedDocumentMetadata,
    RerankerResponse,
)


class TestRankedDocument:
    """Tests for the RankedDocument class."""

    def test_ranked_document_creation(self):
        """Test creating a RankedDocument with content and score."""
        content = [DocumentPart(text='Test content')]
        metadata = {'key': 'value'}
        score = 0.95

        doc = RankedDocument(content=content, metadata=metadata, score=score)

        assert doc.score == 0.95
        assert doc.text() == 'Test content'
        assert doc.metadata == {'key': 'value', 'score': 0.95}
        # Original metadata should not be modified
        assert metadata == {'key': 'value'}

    def test_ranked_document_default_score(self):
        """Test that RankedDocument has a default score of None."""
        content = [DocumentPart(text='Test')]
        doc = RankedDocument(content=content)

        assert doc.score is None

    def test_ranked_document_from_data(self):
        """Test creating RankedDocument from RankedDocumentData."""
        data = RankedDocumentData(
            content=[DocumentPart(text='Test content')],
            metadata=RankedDocumentMetadata(score=0.85),
        )

        doc = RankedDocument.from_ranked_document_data(data)

        assert doc.score == 0.85
        assert doc.text() == 'Test content'


class TestRerankerRef:
    """Tests for RerankerRef and related helper functions."""

    def test_create_reranker_ref_basic(self):
        """Test creating a basic reranker reference."""
        ref = create_reranker_ref('test-reranker')

        assert ref.name == 'test-reranker'
        assert ref.config is None
        assert ref.version is None
        assert ref.info is None

    def test_create_reranker_ref_with_options(self):
        """Test creating a reranker reference with all options."""
        info = RerankerInfo(label='Test Reranker')
        ref = create_reranker_ref(
            name='test-reranker',
            config={'k': 10},
            version='1.0.0',
            info=info,
        )

        assert ref.name == 'test-reranker'
        assert ref.config == {'k': 10}
        assert ref.version == '1.0.0'
        assert ref.info.label == 'Test Reranker'


class TestRerankerActionMetadata:
    """Tests for reranker action metadata creation."""

    def test_action_metadata_basic(self):
        """Test creating basic action metadata."""
        metadata = reranker_action_metadata('test-reranker')

        assert metadata.kind == ActionKind.RERANKER
        assert metadata.name == 'test-reranker'
        assert 'reranker' in metadata.metadata

    def test_action_metadata_with_options(self):
        """Test creating action metadata with options."""
        options = RerankerOptions(
            label='Custom Label',
            config_schema={'type': 'object'},
        )
        metadata = reranker_action_metadata('test-reranker', options)

        assert metadata.metadata['reranker']['label'] == 'Custom Label'
        assert metadata.metadata['reranker']['customOptions'] == {'type': 'object'}


class TestDefineReranker:
    """Tests for the define_reranker function."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return Registry()

    @pytest.mark.asyncio
    async def test_define_reranker_registers_action(self, registry):
        """Test that define_reranker registers an action in the registry."""

        async def simple_reranker(query, documents, options):
            # Return documents in same order with scores
            return RerankerResponse(
                documents=[
                    RankedDocumentData(
                        content=doc.content,
                        metadata=RankedDocumentMetadata(score=1.0 - i * 0.1),
                    )
                    for i, doc in enumerate(documents)
                ]
            )

        action = define_reranker(registry, 'test-reranker', simple_reranker)

        # Verify action was registered
        lookup = registry.lookup_action(ActionKind.RERANKER, 'test-reranker')
        assert lookup is not None
        assert action.name == 'test-reranker'

    @pytest.mark.asyncio
    async def test_define_reranker_with_options(self, registry):
        """Test define_reranker with custom options."""

        async def reranker_fn(query, documents, options):
            return RerankerResponse(documents=[])

        options = RerankerOptions(label='My Reranker')
        action = define_reranker(registry, 'my-reranker', reranker_fn, options)

        assert action is not None


class TestRerank:
    """Tests for the rerank function."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return Registry()

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            DocumentData(content=[DocumentPart(text='First document')]),
            DocumentData(content=[DocumentPart(text='Second document')]),
            DocumentData(content=[DocumentPart(text='Third document')]),
        ]

    @pytest.mark.asyncio
    async def test_rerank_with_string_query(self, registry, sample_documents):
        """Test rerank with a string query."""

        async def score_by_length(query, documents, options):
            # Score documents by content length (longer = higher score)
            scored = []
            for doc in documents:
                length = len(doc.text())
                scored.append(
                    RankedDocumentData(
                        content=doc.content,
                        metadata=RankedDocumentMetadata(score=float(length)),
                    )
                )
            return RerankerResponse(documents=scored)

        define_reranker(registry, 'length-reranker', score_by_length)

        results = await rerank(
            registry,
            {
                'reranker': 'length-reranker',
                'query': 'test query',
                'documents': sample_documents,
            },
        )

        assert len(results) == 3
        assert all(isinstance(r, RankedDocument) for r in results)

    @pytest.mark.asyncio
    async def test_rerank_with_reranker_ref(self, registry, sample_documents):
        """Test rerank with a RerankerRef."""

        async def simple_reranker(query, documents, options):
            return RerankerResponse(
                documents=[
                    RankedDocumentData(
                        content=doc.content,
                        metadata=RankedDocumentMetadata(score=0.5),
                    )
                    for doc in documents
                ]
            )

        define_reranker(registry, 'ref-reranker', simple_reranker)
        ref = create_reranker_ref('ref-reranker')

        results = await rerank(
            registry,
            {
                'reranker': ref,
                'query': 'test',
                'documents': sample_documents,
            },
        )

        assert len(results) == 3
        assert all(doc.score == 0.5 for doc in results)

    @pytest.mark.asyncio
    async def test_rerank_unknown_reranker_raises(self, registry, sample_documents):
        """Test that rerank raises ValueError for unknown reranker."""
        with pytest.raises(ValueError, match='Unable to resolve reranker'):
            await rerank(
                registry,
                {
                    'reranker': 'non-existent-reranker',
                    'query': 'test',
                    'documents': sample_documents,
                },
            )


class TestCustomRerankers:
    """Tests for custom reranker implementations.

    These tests demonstrate how to create custom rerankers as shown
    in the genkit.dev documentation:
    https://genkit.dev/docs/rag/#rerankers-and-two-stage-retrieval
    """

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return Registry()

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents matching genkit.dev documentation example."""
        return [
            DocumentData(content=[DocumentPart(text='pythagorean theorem')]),
            DocumentData(content=[DocumentPart(text='e=mc^2')]),
            DocumentData(content=[DocumentPart(text='pi')]),
            DocumentData(content=[DocumentPart(text='dinosaurs')]),
            DocumentData(content=[DocumentPart(text='quantum mechanics')]),
            DocumentData(content=[DocumentPart(text='pizza')]),
            DocumentData(content=[DocumentPart(text='harry potter')]),
        ]

    @pytest.mark.asyncio
    async def test_custom_keyword_overlap_reranker(self, registry, sample_documents):
        """Test a custom reranker that scores by keyword overlap.

        This demonstrates the pattern shown in genkit.dev docs for
        creating custom reranking logic.
        """

        async def keyword_overlap_reranker(query, documents, options):
            """Reranker that scores documents by keyword overlap with query."""
            query_words = set(query.text().lower().split())
            scored = []

            for doc in documents:
                doc_words = set(doc.text().lower().split())
                overlap = len(query_words & doc_words)
                score = overlap / max(len(query_words), 1)
                scored.append((doc, score))

            # Sort by score descending
            scored.sort(key=lambda x: x[1], reverse=True)

            # Apply k limit if provided in options
            k = options.get('k', len(scored)) if options else len(scored)
            top_k = scored[:k]

            return RerankerResponse(
                documents=[
                    RankedDocumentData(
                        content=doc.content,
                        metadata=RankedDocumentMetadata(score=score),
                    )
                    for doc, score in top_k
                ]
            )

        define_reranker(registry, 'custom/keyword-overlap', keyword_overlap_reranker)

        # Query for 'quantum' should rank 'quantum mechanics' highest
        results = await rerank(
            registry,
            {
                'reranker': 'custom/keyword-overlap',
                'query': 'quantum mechanics physics',
                'documents': sample_documents,
            },
        )

        assert len(results) == 7
        # 'quantum mechanics' should have the highest score (overlaps 2 words)
        assert results[0].text() == 'quantum mechanics'
        assert results[0].score > 0

    @pytest.mark.asyncio
    async def test_custom_reranker_with_top_k_option(self, registry, sample_documents):
        """Test custom reranker with k option to limit results.

        Demonstrates using options to configure reranking behavior.
        """

        async def random_score_reranker(query, documents, options):
            """Reranker that assigns incrementing scores and respects k option."""
            k = options.get('k', 3) if options else 3

            scored_docs = []
            for i, doc in enumerate(documents):
                # Score in reverse order so we have a predictable ranking
                score = float(len(documents) - i)
                scored_docs.append(
                    RankedDocumentData(
                        content=doc.content,
                        metadata=RankedDocumentMetadata(score=score),
                    )
                )

            # Sort by score descending and limit to k
            scored_docs.sort(key=lambda d: d.metadata.score, reverse=True)
            return RerankerResponse(documents=scored_docs[:k])

        define_reranker(registry, 'custom/with-k-option', random_score_reranker)

        results = await rerank(
            registry,
            {
                'reranker': 'custom/with-k-option',
                'query': 'test',
                'documents': sample_documents,
                'options': {'k': 3},
            },
        )

        # Should only return top 3 results
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_custom_reranker_preserves_document_content(self, registry):
        """Test that custom reranker preserves original document content."""

        async def identity_reranker(query, documents, options):
            """Reranker that returns documents with their original content."""
            return RerankerResponse(
                documents=[
                    RankedDocumentData(
                        content=doc.content,
                        metadata=RankedDocumentMetadata(score=1.0),
                    )
                    for doc in documents
                ]
            )

        define_reranker(registry, 'custom/identity', identity_reranker)

        original_texts = ['Document A', 'Document B with more text', 'Doc C']
        documents = [DocumentData(content=[DocumentPart(text=t)]) for t in original_texts]

        results = await rerank(
            registry,
            {
                'reranker': 'custom/identity',
                'query': 'test',
                'documents': documents,
            },
        )

        # Verify all original content is preserved
        result_texts = [doc.text() for doc in results]
        assert result_texts == original_texts

    @pytest.mark.asyncio
    async def test_custom_reranker_two_stage_retrieval_pattern(self, registry):
        """Test the two-stage retrieval pattern: retrieve then rerank.

        This demonstrates the typical RAG pattern where:
        1. Stage 1: Retrieve a broad set of candidates
        2. Stage 2: Rerank to find most relevant documents
        """

        # Simulate stage 1 retrieval results (unranked)
        retrieved_documents = [
            DocumentData(content=[DocumentPart(text='Machine learning is a subset of AI')]),
            DocumentData(content=[DocumentPart(text='Pizza is a popular food')]),
            DocumentData(content=[DocumentPart(text='Deep learning uses neural networks')]),
            DocumentData(content=[DocumentPart(text='Cats are domestic animals')]),
            DocumentData(content=[DocumentPart(text='AI transforms industries')]),
        ]

        async def relevance_reranker(query, documents, options):
            """Reranker that scores by word presence in query."""
            query_lower = query.text().lower()
            scored = []

            for doc in documents:
                doc_text = doc.text().lower()
                # Simple relevance: count query words in document
                score = sum(1 for word in query_lower.split() if word in doc_text)
                scored.append((doc, float(score)))

            scored.sort(key=lambda x: x[1], reverse=True)

            return RerankerResponse(
                documents=[
                    RankedDocumentData(
                        content=doc.content,
                        metadata=RankedDocumentMetadata(score=score),
                    )
                    for doc, score in scored
                ]
            )

        define_reranker(registry, 'custom/relevance', relevance_reranker)

        # Stage 2: Rerank with query about AI
        reranked = await rerank(
            registry,
            {
                'reranker': 'custom/relevance',
                'query': 'artificial intelligence AI',
                'documents': retrieved_documents,
            },
        )

        # AI-related documents should rank higher than unrelated ones
        # Get scores for AI and non-AI documents
        ai_scores = [doc.score for doc in reranked if 'AI' in doc.text() or 'learning' in doc.text()]
        non_ai_scores = [doc.score for doc in reranked if 'Pizza' in doc.text() or 'Cats' in doc.text()]

        # AI-related documents should have higher scores on average
        assert max(ai_scores) > max(non_ai_scores)
