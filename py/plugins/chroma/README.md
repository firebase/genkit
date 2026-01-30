# Genkit ChromaDB Plugin

ChromaDB vector store plugin for [Genkit](https://github.com/firebase/genkit).

## Installation

```bash
pip install genkit-plugin-chroma
```

## Quick Start

```python
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.chroma import chroma, chroma_retriever_ref, chroma_indexer_ref

# Initialize Genkit with Chroma plugin
ai = Genkit(
    plugins=[
        GoogleAI(),
        chroma(
            collections=[
                {
                    'collection_name': 'my_documents',
                    'embedder': 'googleai/text-embedding-004',
                    'create_collection_if_missing': True,
                }
            ]
        ),
    ]
)

# Get references to retriever and indexer
retriever = chroma_retriever_ref(collection_name='my_documents')
indexer = chroma_indexer_ref(collection_name='my_documents')

# Index documents
await ai.index(
    indexer=indexer,
    documents=[
        {'content': [{'text': 'Paris is the capital of France.'}]},
        {'content': [{'text': 'Tokyo is the capital of Japan.'}]},
    ],
)

# Retrieve documents
results = await ai.retrieve(
    retriever=retriever,
    query='What is the capital of France?',
    options={'k': 3},
)
for doc in results.documents:
    print(doc.text)
```

## Configuration

### Plugin Options

```python
chroma(
    collections=[
        {
            # Required: Name of the Chroma collection
            'collection_name': 'my_documents',
            
            # Required: Embedder to use for generating embeddings
            'embedder': 'googleai/text-embedding-004',
            
            # Optional: Embedder-specific options
            'embedder_options': {'task_type': 'RETRIEVAL_DOCUMENT'},
            
            # Optional: Create collection if it doesn't exist (default: False)
            'create_collection_if_missing': True,
            
            # Optional: Chroma client configuration
            'client_params': {
                'host': 'localhost',
                'port': 8000,
            },
        }
    ]
)
```

### Retriever Options

```python
results = await ai.retrieve(
    retriever=retriever,
    query='search query',
    options={
        'k': 10,  # Number of results (default: 10)
        'where': {'metadata_field': 'value'},  # Metadata filter
        'where_document': {'$contains': 'keyword'},  # Document content filter
        'include': ['documents', 'metadatas', 'distances'],  # Fields to include
    },
)
```

## Features

- **Automatic embedding generation**: Uses Genkit embedders for both indexing and retrieval
- **Flexible configuration**: Supports both local and remote Chroma instances
- **Metadata filtering**: Filter results by metadata or document content
- **Collection management**: Create and delete collections programmatically

## Cross-Language Parity

This plugin maintains API parity with the JavaScript implementation:
- `js/plugins/chroma/src/index.ts`

## License

Apache 2.0
