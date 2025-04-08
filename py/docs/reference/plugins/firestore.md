# Firestore Vector Store

The Firestore plugin provides retriever implementations that use Google Cloud
Firestore as a vector store.

## Installation

```bash
pip3 install genkit-plugin-firebase
```

## Prerequisites

*   A Firebase project with Cloud Firestore enabled.
*   The `genkit` package installed.
*   `gcloud` CLI for managing credentials and Firestore indexes.

## Configuration

To use this plugin, specify it when you initialize Genkit:

```python
from genkit.ai import Genkit
from genkit.plugins.firebase.firestore import FirestoreVectorStore
from google.cloud import firestore

firestore_client = firestore.Client()

ai = Genkit(
    plugins=[
        FirestoreVectorStore(
            name='my_firestore_retriever',
            collection='my_collection',
            vector_field='embedding',
            content_field='text',
            embedder='vertexai/text-embedding-004',
            firestore_client=firestore_client,
        ),
    ]
)
```

### Configuration Options

*   **name** (str): A unique name for this retriever instance.
*   **collection** (str): The name of the Firestore collection to query.
*   **vector_field** (str): The name of the field in the Firestore documents that contains the vector embedding.
*   **content_field** (str): The name of the field in the Firestore documents that contains the text content.
*   **embedder** (str): The name of the embedding model to use.  Must match a configured embedder in your Genkit project.
*   **firestore_client**: A firestore client object that will be used for all queries to the vectorstore.

## Usage

1.  **Create a Firestore Client**:

    ```python
    from google.cloud import firestore
    firestore_client = firestore.Client()
    ```

2.  **Define a Firestore Retriever**:

    ```python
    from genkit.ai import Genkit
    from genkit.plugins.firebase.firestore import FirestoreVectorStore

    ai = Genkit(
        plugins=[
            FirestoreVectorStore(
                name='my_firestore_retriever',
                collection='my_collection',
                vector_field='embedding',
                content_field='text',
                embedder='vertexai/text-embedding-004',
                firestore_client=firestore_client,
            ),
        ]
    )
    ```

3.  **Retrieve Documents**:

    ```python
    async def retreive_documents():
        return await ai.retrieve(
            query="What are the main topics?",
            retriever='my_firestore_retriever',
        )
    ```

## Populating the Index

Before you can retrieve documents, you need to populate your Firestore collection with data and their corresponding vector embeddings.  Here's how you can do it:

1. **Prepare your Data**: Organize your data into documents. Each document should have at least two fields: a `text` field containing the content you want to retrieve, and an `embedding` field that holds the vector embedding of the content.  You can add any other metadata as well.

2. **Generate Embeddings**: Use the same embedding model configured in your `FirestoreVectorStore` to generate vector embeddings for your text content. The `ai.embed()` method can be used.

3. **Upload Documents to Firestore**: Use the Firestore client to upload the documents with their embeddings to the specified collection.

Here's an example of how to index data:

```python
from genkit.ai import Document
from genkit.types import TextPart

async def index_documents(documents: list[str], collection_name: str):
    """Indexes the documents in Firestore."""
    genkit_documents = [Document(content=[TextPart(text=doc)]) for doc in documents]
    embed_response = await ai.embed(embedder='vertexai/text-embedding-004', documents=genkit_documents)
    embeddings = [emb.embedding for emb in embed_response.embeddings]

    for i, document_text in enumerate(documents):
        doc_id = f'doc-{i + 1}'
        embedding = embeddings[i]

        doc_ref = firestore_client.collection(collection_name).document(doc_id)
        result = doc_ref.set({
            'text': document_text,
            'embedding': embedding,
            'metadata': f'metadata for doc {i + 1}',
        })

# Example Usage
documents = [
    "This is document one.",
    "This is document two.",
    "This is document three.",
]
await index_documents(documents, 'my_collection')
```

## Creating a Firestore Index
To enable vector similarity search you will need to configure the index in your Firestore database. Use the following command

```bash
gcloud firestore indexes composite create \
  --project=<FIREBASE-PROJECT>\
  --collection-group=<COLLECTION-NAME> \
  --query-scope=COLLECTION \
  --field-config=vector-config='{"dimension":"<YOUR_DIMENSION_COUNT>","flat": "{}"}',field-path=<VECTOR-FIELD>
```

* Replace `<FIREBASE-PROJECT>` with the name of your Firebase project
* Replace `<COLLECTION-NAME>` with the name of your Firestore collection
* Replace `<YOUR_DIMENSION_COUNT>` with the correct dimension for your embedding model. Common values are:
    * `768` for `vertexai/text-embedding-004`
* Replace `<VECTOR-FIELD>` with the name of the field containing vector embeddings (e.g. `embedding`).

## API Reference

::: genkit.plugins.firebase.firestore.FirestoreVectorStore
