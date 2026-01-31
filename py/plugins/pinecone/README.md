# Genkit Pinecone Plugin

Pinecone vector store plugin for [Genkit](https://github.com/firebase/genkit).

## Installation

```bash
pip install genkit-plugin-pinecone
```

## Quick Start

```python
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.pinecone import pinecone, pinecone_retriever_ref, pinecone_indexer_ref

# Initialize Genkit with Pinecone plugin
ai = Genkit(
    plugins=[
        GoogleAI(),
        pinecone(
            indexes=[
                {
                    'index_id': 'my-index',
                    'embedder': 'googleai/text-embedding-004',
                }
            ]
        ),
    ]
)

# Get references to retriever and indexer
retriever = pinecone_retriever_ref(index_id='my-index')
indexer = pinecone_indexer_ref(index_id='my-index')

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

### Environment Variable

Set your Pinecone API key:

```bash
export PINECONE_API_KEY=your-api-key
```

### Plugin Options

```python
pinecone(
    indexes=[
        {
            # Required: Pinecone index name
            'index_id': 'my-index',
            
            # Required: Embedder to use for generating embeddings
            'embedder': 'googleai/text-embedding-004',
            
            # Optional: Embedder-specific options
            'embedder_options': {'task_type': 'RETRIEVAL_DOCUMENT'},
            
            # Optional: Metadata key for document content (default: '_content')
            'content_key': '_content',
            
            # Optional: Pinecone client configuration
            'client_params': {
                'api_key': 'your-api-key',  # Or use PINECONE_API_KEY env var
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
        'k': 10,  # Number of results (max: 1000)
        'namespace': 'my-namespace',  # Pinecone namespace
        'filter': {'category': 'tech'},  # Metadata filter
    },
)
```

### Indexer Options

```python
await ai.index(
    indexer=indexer,
    documents=documents,
    options={
        'namespace': 'my-namespace',  # Pinecone namespace
    },
)
```

## Features

- **Automatic embedding generation**: Uses Genkit embedders for both indexing and retrieval
- **Namespace support**: Multi-tenancy via Pinecone namespaces
- **Metadata filtering**: Filter results by metadata at query time
- **Index management**: Create, describe, and delete indexes programmatically

## Index Management

```python
from genkit.plugins.pinecone import (
    create_pinecone_index,
    describe_pinecone_index,
    delete_pinecone_index,
)

# Create an index
await create_pinecone_index(
    name='my-index',
    dimension=768,
    metric='cosine',
)

# Describe an index
info = await describe_pinecone_index(name='my-index')
print(f"Dimension: {info['dimension']}")

# Delete an index
await delete_pinecone_index(name='my-index')
```

## Cross-Language Parity

This plugin maintains API parity with the JavaScript implementation:
- `js/plugins/pinecone/src/index.ts`

## License

Apache 2.0
