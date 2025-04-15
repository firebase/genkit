# Retrieval-augmented generation (RAG)

Genkit provides abstractions that help you build retrieval-augmented
generation (RAG) flows, as well as plugins that provide integrations with
related tools.

## What is RAG?

Retrieval-augmented generation is a technique used to incorporate external
sources of information into an LLM’s responses. It's important to be able to do
so because, while LLMs are typically trained on a broad body of material,
practical use of LLMs often requires specific domain knowledge (for example, you
might want to use an LLM to answer customers' questions about your company’s
products).

One solution is to fine-tune the model using more specific data. However, this
can be expensive both in terms of compute cost and in terms of the effort needed
to prepare adequate training data.

In contrast, RAG works by incorporating external data sources into a prompt at
the time it's passed to the model. For example, you could imagine the prompt,
"What is Bart's relationship to Lisa?" might be expanded ("augmented") by
prepending some relevant information, resulting in the prompt, "Homer and
Marge's children are named Bart, Lisa, and Maggie. What is Bart's relationship
to Lisa?"

This approach has several advantages:

*   It can be more cost-effective because you don't have to retrain the model.
*   You can continuously update your data source and the LLM can immediately
    make use of the updated information.
*   You now have the potential to cite references in your LLM's responses.

On the other hand, using RAG naturally means longer prompts, and some LLM API
services charge for each input token you send. Ultimately, you must evaluate the
cost tradeoffs for your applications.

RAG is a very broad area and there are many different techniques used to achieve
the best quality RAG. The core Genkit framework offers three main abstractions
to help you do RAG:

*   Embedders: transforms documents into a vector representation
*   Retrievers: retrieve documents from an "index", given a query.

These definitions are broad on purpose because Genkit is un-opinionated about
what an "index" is or how exactly documents are retrieved from it. Genkit only
provides a `Document` format and everything else is defined by the retriever or
indexer implementation provider.

### Embedders

An embedder is a function that takes content (text, images, audio, etc.) and
creates a numeric vector that encodes the semantic meaning of the original
content. As mentioned above, embedders are leveraged as part of the process of
indexing, however, they can also be used independently to create embeddings
without an index.

### Retrievers

A retriever is a concept that encapsulates logic related to any kind of document
retrieval. The most popular retrieval cases typically include retrieval from
vector stores, however, in Genkit a retriever can be any function that returns
data.

To create a retriever, you can use one of the provided implementations or create
your own.

## Defining a RAG Flow

The following examples show how you could ingest a collection of restaurant menu
PDF documents into a vector database and retrieve them for use in a flow that
determines what food items are available. Note that indexing is outside the scope
of Genkit and you should use the SDKs/APIs provided by the vector store you are using.

The following example shows how you might use a retriever in a RAG flow. Like
the retriever example, this example uses Firestore Vector Store.

```python
from genkit.ai import Genkit
from genkit.plugins.google_genai import (
    VertexAI,
    vertexai_name,
)
from genkit.plugins.firebase.firestore import FirestoreVectorStore

ai = Genkit(
    plugins=[
        VertexAI(),
        FirestoreVectorStore(
                name='my_firestore_retriever',
                collection='mycollection',
                vector_field='embedding',
                content_field='text',
                embedder=EMBEDDING_MODEL,
                distance_measure=DistanceMeasure.EUCLIDEAN,
                firestore_client=firestore_client,
        ),
    ],
)
@ai.flow()
async def qa_flow(query: str):
    docs = await ai.retrieve(
        query=Document.from_text(query), 
        retriever='firestore/my_firestore_retriever'
    )
    response = await ai.generate(prompt=query, docs=docs)
    return response.text
```

#### Run the retriever flow

```python
result = await qa_flow('Recommend a dessert from the menu while avoiding dairy and nuts')
print(result)
```

The output for this command should contain a response from the model, grounded
in the indexed `menu.pdf` file.

## Write your own retrievers

It's also possible to create your own retriever. This is useful if your
documents are managed in a document store that is not supported in Genkit (eg:
MySQL, Google Drive, etc.). The Genkit SDK provides flexible methods that let
you provide custom code for fetching documents. You can also define custom
retrievers that build on top of existing retrievers in Genkit and apply advanced
RAG techniques (such as reranking or prompt extensions) on top.

```py
from genkit.types import (
    RetrieverRequest,
    RetrieverResponse,
    Document,
    ActionRunContext
)

async def my_retriever(request: RetrieverRequest, ctx: ActionRunContext):
    """Example of a retriever.

    Args:
        request: The request to the retriever.
        ctx: The context of the retriever.
    """
    return RetrieverResponse(documents=[Document.from_text('Hello'), Document.from_text('World')])


ai.define_retriever(name='my_retriever', fn=my_retriever)
```

Then you'll be able to use your retriever with `ai.retrieve`:

```py
docs = await ai.retrieve(
    query=Document.from_text(query), 
    retriever='my_retriever'
)
```