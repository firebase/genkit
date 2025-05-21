# Retrieval-augmented generation (RAG)

Genkit provides abstractions that help you build retrieval-augmented generation
(RAG) flows, as well as plugins that provide integrations with related tools.

## What is RAG?

Retrieval-augmented generation is a technique used to incorporate external
sources of information into an LLM’s responses. It's important to be able to do
so because, while LLMs are typically trained on a broad body of
material, practical use of LLMs often requires specific domain knowledge (for
example, you might want to use an LLM to answer customers' questions about your
company’s products).

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

- It can be more cost effective because you don't have to retrain the model.
- You can continuously update your data source and the LLM can immediately make
  use of the updated information.
- You now have the potential to cite references in your LLM's responses.

On the other hand, using RAG naturally means longer prompts, and some LLM API
services charge for each input token you send. Ultimately, you must evaluate the
cost tradeoffs for your applications.

RAG is a very broad area and there are many different techniques used to achieve
the best quality RAG. The core Genkit framework offers two main abstractions to
help you do RAG:

- Indexers: add documents to an "index".
- Embedders: transforms documents into a vector representation
- Retrievers: retrieve documents from an "index", given a query.

These definitions are broad on purpose because Genkit is un-opinionated about
what an "index" is or how exactly documents are retrieved from it. Genkit only
provides a `Document` format and everything else is defined by the retriever or
indexer implementation provider.

### Indexers

The index is responsible for keeping track of your documents in such a way that
you can quickly retrieve relevant documents given a specific query. This is most
often accomplished using a vector database, which indexes your documents using
multidimensional vectors called embeddings. A text embedding (opaquely)
represents the concepts expressed by a passage of text; these are generated
using special-purpose ML models. By indexing text using its embedding, a vector
database is able to cluster conceptually related text and retrieve documents
related to a novel string of text (the query).

Before you can retrieve documents for the purpose of generation, you need to
ingest them into your document index. A typical ingestion flow does the
following:

1.  Split up large documents into smaller documents so that only relevant
    portions are used to augment your prompts – "chunking". This is necessary
    because many LLMs have a limited context window, making it impractical to
    include entire documents with a prompt.

    Genkit doesn't provide built-in chunking libraries; however, there are open
    source libraries available that are compatible with Genkit.

1.  Generate embeddings for each chunk. Depending on the database you're using,
    you might explicitly do this with an embedding generation model, or you
    might use the embedding generator provided by the database.

1.  Add the text chunk and its index to the database.

You might run your ingestion flow infrequently or only once if you are working
with a stable source of data. On the other hand, if you are working with data
that frequently changes, you might continuously run the ingestion flow (for
example, in a Cloud Firestore trigger, whenever a document is updated).

### Embedders

An embedder is a function that takes content (text, images, audio, etc.) and creates a numeric vector that encodes the semantic meaning of the original content. As mentioned above, embedders are leveraged as part of the process of indexing, however, they can also be used independently to create embeddings without an index.

### Retrievers

A retriever is a concept that encapsulates logic related to any kind of document
retrieval. The most popular retrieval cases typically include retrieval from
vector stores, however, in Genkit a retriever can be any function that returns data.

To create a retriever, you can use one of the provided implementations or
create your own.

## Supported indexers, retrievers, and embedders

Genkit provides indexer and retriever support through its plugin system. The
following plugins are officially supported:

- [Pinecone](plugins/pinecone.md) cloud vector database

In addition, Genkit supports the following vector stores through predefined
code templates, which you can customize for your database configuration and
schema:

- PostgreSQL with [`pgvector`](templates/pgvector.md)

Embedding model support is provided through the following plugins:

| Plugin                    | Models               |
| ------------------------- | -------------------- |
| [Google Generative AI][1] | Gecko text embedding |
| [Google Vertex AI][2]     | Gecko text embedding |

[1]: plugins/google-genai.md
[2]: plugins/vertex-ai.md

## Defining a RAG Flow

The following examples show how you could ingest a collection of restaurant menu PDF documents
into a vector database and retrieve them for use in a flow that determines what food items are available.

### Install dependencies

In this example, we will use the `textsplitter` library from `langchaingo` and
the `ledongthuc/pdf` PDF parsing Library:

```posix-terminal
go get github.com/tmc/langchaingo/textsplitter

go get github.com/ledongthuc/pdf
```

### Define an Indexer

The following example shows how to create an indexer to ingest a collection of PDF documents
and store them in a local vector database.

It uses the local file-based vector similarity retriever
that Genkit provides out-of-the box for simple testing and prototyping (_do not
use in production_)

#### Create the indexer

```go
// Import Genkit's file-based vector retriever, (Don't use in production.)
import "github.com/firebase/genkit/go/plugins/localvec"

// Vertex AI provides the text-embedding-004 embedder model.
import "github.com/firebase/genkit/go/plugins/vertexai"
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/rag/main.go" region_tag="vec" adjust_indentation="auto" %}
```

#### Create chunking config

This example uses the `textsplitter` library which provides a simple text
splitter to break up documents into segments that can be vectorized.

The following definition configures the chunking function to return document
segments of 200 characters, with an overlap between chunks of 20 characters.

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/rag/main.go" region_tag="splitcfg" adjust_indentation="auto" %}
```

More chunking options for this library can be found in the
[`langchaingo` documentation](https://pkg.go.dev/github.com/tmc/langchaingo/textsplitter#Option).

#### Define your indexer flow

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/rag/main.go" region_tag="indexflow" adjust_indentation="auto" %}
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/rag/main.go" region_tag="readpdf" adjust_indentation="auto" %}
```

#### Run the indexer flow

```posix-terminal
genkit flow:run indexMenu "'menu.pdf'"
```

After running the `indexMenu` flow, the vector database will be seeded with
documents and ready to be used in Genkit flows with retrieval steps.

### Define a flow with retrieval

The following example shows how you might use a retriever in a RAG flow. Like
the indexer example, this example uses Genkit's file-based vector retriever,
which you should not use in production.

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/rag/main.go" region_tag="retrieve" adjust_indentation="auto" %}
```

## Write your own indexers and retrievers

It's also possible to create your own retriever. This is useful if your
documents are managed in a document store that is not supported in Genkit (eg:
MySQL, Google Drive, etc.). The Genkit SDK provides flexible methods that let
you provide custom code for fetching documents.

You can also define custom retrievers that build on top of existing retrievers
in Genkit and apply advanced RAG techniques (such as reranking or prompt
extension) on top.

For example, suppose you have a custom re-ranking function you want to use. The
following example defines a custom retriever that applies your function to the
menu retriever defined earlier:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/rag/main.go" region_tag="customret" adjust_indentation="auto" %}
```
