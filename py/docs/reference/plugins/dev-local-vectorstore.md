# Dev Local Vector Store

The Dev Local Vector Store plugin provides a local, file-based vector store for development and testing purposes. It is not intended for production use.

## Installation

```bash
pip3 install genkit-plugin-dev-local-vectorstore
```

## Configuration

To use this plugin, specify it when you initialize Genkit:

```python
from genkit.ai import Genkit
from genkit.plugins.dev_local_vectorstore import DevLocalVectorStore
from genkit.plugins.google_genai import VertexAI

ai = Genkit(
    plugins=[
        VertexAI(),
        DevLocalVectorStore(
            name='my_vectorstore',
            embedder='vertexai/text-embedding-004',
        ),
    ],
    model='vertexai/gemini-2.0.',
)
```

### Configuration Options

*   **name** (str): A unique name for this vector store instance.  This is used as the `retriever` argument to `ai.retrieve`.
*   **embedder** (str): The name of the embedding model to use. Must match a configured embedder in your Genkit project.
*   **embedder_options** (str, optional): embedder options.

## Usage

### Indexing Documents
The Dev Local Vector Store automatically creates indexes. To populate with data you must call the static method `.index(name, documents)`:

```python
from genkit.ai import Genkit
from genkit.plugins.dev_local_vectorstore import DevLocalVectorStore
from genkit.plugins.google_genai import VertexAI
from genkit.types import Document

ai = Genkit(
    plugins=[
        VertexAI(),
        DevLocalVectorStore(
            name='my_vectorstore',
            embedder='vertexai/text-embedding-004',
        ),
    ],
    model='vertexai/gemini-2.0.',
)

data_list = [
    'This is the first document.',
    'This is the second document.',
    'This is the third document.',
    "This is the fourth document.",
]

genkit_docs = [Document.from_text(text=item) for item in data_list]
await DevLocalVectorStore.index('my_vectorstore', genkit_docs)
```

### Retrieving Documents
Use `ai.retrieve` and pass the store name configured in the DevLocalVectorStore constructor.

```python
from genkit.types import Document

docs = await ai.retrieve(
    query=Document.from_text('search query'),
    retriever='my_vectorstore',
)
```
