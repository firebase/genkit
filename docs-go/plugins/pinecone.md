# Pinecone plugin

The Pinecone plugin provides indexer and retriever implementatons that use the
[Pinecone](https://www.pinecone.io/) cloud vector database.

## Configuration

To use this plugin, import the `pinecone` package and call `pinecone.Init()`:

```go
import "github.com/firebase/genkit/go/plugins/pinecone"
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/pinecone.go" region_tag="init" adjust_indentation="auto" %}
```

The plugin requires your Pinecone API key. 
Configure the plugin to use your API key by doing one of the following:

- Set the `PINECONE_API_KEY` environment variable to your API key.

- Specify the API key when you initialize the plugin:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/pinecone.go" region_tag="initkey" adjust_indentation="auto" %}
  ```

  However, don't embed your API key directly in code! Use this feature only
  in conjunction with a service like Cloud Secret Manager or similar.

## Usage

To add documents to a Pinecone index, first create an index definition that
specifies the name of the index and the embedding model you're using:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/pinecone.go" region_tag="defineindex" adjust_indentation="auto" %}
```

You can also optionally specify the key that Pinecone uses for document data
(`_content`, by default).

Then, call the index's `Index()` method, passing it a list of the documents you
want to add:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/pinecone.go" region_tag="index" adjust_indentation="auto" %}
```

Similarly, to retrieve documents from an index, first create a retriever
definition:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/pinecone.go" region_tag="defineretriever" adjust_indentation="auto" %}
```

Then, call the retriever's `Retrieve()` method, passing it a text query:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/pinecone.go" region_tag="retrieve" adjust_indentation="auto" %}
```

See the [Retrieval-augmented generation](../rag.md) page for a general
discussion on using indexers and retrievers for RAG.
