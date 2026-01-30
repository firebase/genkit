#!/usr/bin/env python3
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""RAG demo using Pinecone with Genkit - Cat Knowledge Base.

This sample demonstrates Retrieval-Augmented Generation (RAG) using Pinecone
as a managed vector database. It includes a cat-themed knowledge base with
documents about cat care, famous cats, and fun cat facts.

Architecture
============

┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG with Pinecone                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐        │
│  │   Genkit     │     │  Pinecone    │     │   Pinecone Cloud     │        │
│  │   + GoogleAI │ ──► │   Plugin     │ ──► │   (Managed)          │        │
│  └──────────────┘     └──────────────┘     └──────────────────────┘        │
│                                                                              │
│  Data Sources (./data/):                                                    │
│  - cat_care_guide.txt    - Complete cat care information                   │
│  - famous_cats.txt       - Famous cats throughout history                  │
│  - cat_facts.json        - Fun and interesting cat facts                   │
│                                                                              │
│  Flows:                                                                      │
│  - index_cat_knowledge_flow: Load and index all cat documents              │
│  - ask_about_cats_flow: Ask questions about cats with RAG                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

Prerequisites
=============

1. Create a Pinecone account at https://www.pinecone.io/
2. Create an index with:
   - Dimension: 768 (for text-embedding-004)
   - Metric: cosine
3. Set environment variables:
   - PINECONE_API_KEY: Your Pinecone API key
   - GOOGLE_API_KEY: Your Google AI API key

Quick Start
===========

1. Set your API keys:
   ```
   export PINECONE_API_KEY=your-pinecone-key
   export GOOGLE_API_KEY=your-google-key
   ```

2. Run the demo:
   ```
   ./run.sh
   ```

3. Open http://localhost:4000 in your browser

4. The cat knowledge base is automatically indexed at startup!
   (Note: First run may take longer to create embeddings)

5. Run `ask_about_cats_flow` with questions like:
   - "How often should I feed my cat?"
   - "Tell me about Grumpy Cat"
   - "Why do cats purr?"
"""

import json
from pathlib import Path

import structlog
from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit
from genkit.blocks.document import Document
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.pinecone import pinecone, pinecone_indexer_ref, pinecone_retriever_ref

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

logger = structlog.get_logger(__name__)

# Update this to match your Pinecone index name
INDEX_ID = 'cat-knowledge'
EMBEDDER = 'googleai/text-embedding-004'
DATA_DIR = Path(__file__).parent.parent / 'data'

ai = Genkit(
    plugins=[
        GoogleAI(),
        pinecone(
            indexes=[
                {
                    'index_id': INDEX_ID,
                    'embedder': EMBEDDER,
                }
            ]
        ),
    ],
    model='googleai/gemini-2.0-flash',
)


class IndexInput(BaseModel):
    """Input for indexing cat knowledge documents."""

    include_care_guide: bool = Field(
        default=True,
        description='Include the comprehensive cat care guide',
    )
    include_famous_cats: bool = Field(
        default=True,
        description='Include information about famous cats',
    )
    include_cat_facts: bool = Field(
        default=True,
        description='Include fun cat facts',
    )
    namespace: str | None = Field(
        default=None,
        description='Optional Pinecone namespace for data isolation',
    )


class IndexResult(BaseModel):
    """Result of indexing operation."""

    total_documents: int
    sources_indexed: list[str]
    namespace: str | None
    message: str


class QueryInput(BaseModel):
    """Input for asking questions about cats."""

    question: str = Field(
        default='Why do cats purr and what does it mean?',
        description='Your question about cats',
    )
    num_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description='Number of relevant documents to retrieve',
    )
    namespace: str | None = Field(
        default=None,
        description='Optional Pinecone namespace to query',
    )


class QueryResult(BaseModel):
    """Result of RAG query about cats."""

    answer: str
    sources_used: list[str]
    confidence: str


def load_text_file(filepath: Path) -> list[str]:
    """Load a text file and split into chunks by section.

    Args:
        filepath: Path to the text file.

    Returns:
        List of text chunks.
    """
    if not filepath.exists():
        return []

    content = filepath.read_text(encoding='utf-8')

    # Split by headers (## or #)
    chunks = []
    current_chunk = []

    for line in content.split('\n'):
        if line.startswith('## ') and current_chunk:
            chunks.append('\n'.join(current_chunk).strip())
            current_chunk = [line]
        else:
            current_chunk.append(line)

    if current_chunk:
        chunks.append('\n'.join(current_chunk).strip())

    # Filter out very short chunks
    return [c for c in chunks if len(c) > 50]


def load_json_facts(filepath: Path) -> list[str]:
    """Load cat facts from JSON file.

    Args:
        filepath: Path to the JSON file.

    Returns:
        List of fact strings.
    """
    if not filepath.exists():
        return []

    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    facts = []
    for fact_obj in data.get('cat_facts', []):
        category = fact_obj.get('category', 'general')
        fact = fact_obj.get('fact', '')
        if fact:
            facts.append(f'[{category.upper()}] {fact}')

    return facts


@ai.flow()
async def index_cat_knowledge_flow(input: IndexInput) -> IndexResult:
    """Index cat knowledge documents into Pinecone.

    This flow loads cat-themed documents from the ./data/ directory and
    indexes them into Pinecone for retrieval. Documents are split into
    chunks for better retrieval accuracy.

    Args:
        input: Configuration for which document sources to include.

    Returns:
        Summary of the indexing operation.
    """
    all_texts: list[str] = []
    sources: list[str] = []

    # Load cat care guide
    if input.include_care_guide:
        care_chunks = load_text_file(DATA_DIR / 'cat_care_guide.txt')
        all_texts.extend(care_chunks)
        if care_chunks:
            sources.append(f'cat_care_guide.txt ({len(care_chunks)} chunks)')

    # Load famous cats
    if input.include_famous_cats:
        famous_chunks = load_text_file(DATA_DIR / 'famous_cats.txt')
        all_texts.extend(famous_chunks)
        if famous_chunks:
            sources.append(f'famous_cats.txt ({len(famous_chunks)} chunks)')

    # Load cat facts
    if input.include_cat_facts:
        facts = load_json_facts(DATA_DIR / 'cat_facts.json')
        all_texts.extend(facts)
        if facts:
            sources.append(f'cat_facts.json ({len(facts)} facts)')

    if not all_texts:
        return IndexResult(
            total_documents=0,
            sources_indexed=[],
            namespace=input.namespace,
            message='No documents found to index. Check that data files exist in ./data/',
        )

    # Convert to Document objects
    documents = [Document.from_text(text) for text in all_texts]

    # Build options
    options: dict[str, object] | None = None
    if input.namespace:
        options = {'namespace': input.namespace}

    # Index into Pinecone
    await ai.index(
        indexer=pinecone_indexer_ref(index_id=INDEX_ID),
        documents=documents,
        options=options,
    )

    namespace_msg = f' (namespace: {input.namespace})' if input.namespace else ''
    return IndexResult(
        total_documents=len(documents),
        sources_indexed=sources,
        namespace=input.namespace,
        message=f'Successfully indexed {len(documents)} documents into "{INDEX_ID}"{namespace_msg}',
    )


@ai.flow()
async def ask_about_cats_flow(input: QueryInput) -> QueryResult:
    """Ask a question about cats using RAG.

    This flow retrieves relevant documents from the cat knowledge base
    and uses them to generate an informed, accurate answer.

    Args:
        input: The question and retrieval parameters.

    Returns:
        The answer along with source information.
    """
    # Build retrieval options
    options: dict[str, object] = {'k': input.num_results}
    if input.namespace:
        options['namespace'] = input.namespace

    # Retrieve relevant documents
    result = await ai.retrieve(
        retriever=pinecone_retriever_ref(index_id=INDEX_ID),
        query=input.question,
        options=options,
    )

    # Extract text from retrieved documents
    sources: list[str] = []
    context_parts: list[str] = []

    for doc_data in result.documents:
        # Use Document helper to extract text from all parts
        doc = Document.from_document_data(doc_data)
        text = doc.text()
        if text:
            # Truncate for display in sources
            preview = text[:100] + '...' if len(text) > 100 else text
            sources.append(preview)
            context_parts.append(text)

    # Build context string
    if not context_parts:
        return QueryResult(
            answer="I don't have information about that in my cat knowledge base. "
            'Please make sure to run the indexing flow first!',
            sources_used=[],
            confidence='low',
        )

    context = '\n\n---\n\n'.join(context_parts)

    # Generate answer using retrieved context
    response = await ai.generate(
        prompt=f"""You are a helpful cat expert assistant. Answer the following question
based ONLY on the provided context about cats. If the context doesn't contain
relevant information, say so. Be friendly and informative!

CONTEXT:
{context}

QUESTION: {input.question}

Provide a helpful, accurate answer based on the context above. If citing specific
facts, mention where they come from (e.g., "According to the care guide..." or
"One famous cat...").""",
    )

    # Determine confidence based on number of relevant sources
    confidence = 'high' if len(sources) >= 3 else 'medium' if len(sources) >= 1 else 'low'

    return QueryResult(
        answer=response.text,
        sources_used=[str(s) for s in sources],
        confidence=confidence,
    )


@ai.flow()
async def list_sample_questions_flow() -> list[str]:
    """Get a list of sample questions you can ask about cats.

    Returns:
        List of example questions.
    """
    return [
        'Why do cats purr?',
        'How often should I feed my cat?',
        'What vaccinations do cats need?',
        'Tell me about Grumpy Cat',
        'Who was Félicette?',
        'What is a group of cats called?',
        'How many bones does a cat have?',
        'Why do cats knead?',
        'What is the oldest cat ever recorded?',
        'Are there any plants toxic to cats?',
        'What cat breeds are known for being calm?',
        'Why do cats bring dead mice to their owners?',
    ]


async def main() -> None:
    """Main entry point for the RAG demo.

    Automatically indexes the cat knowledge base at startup for
    a smooth demo experience. Note: First run may take longer as
    embeddings are generated.
    """
    await logger.ainfo('Starting RAG demo - auto-indexing cat knowledge base')
    try:
        result = await index_cat_knowledge_flow(IndexInput())
        await logger.ainfo(
            'Auto-indexing complete',
            total_documents=result.total_documents,
            sources=result.sources_indexed,
        )
    except Exception as e:
        await logger.awarning(
            'Auto-indexing failed - you may need to run index_cat_knowledge_flow manually',
            error=str(e),
        )


if __name__ == '__main__':
    ai.run_main(main())
