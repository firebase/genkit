# Vertex AI plugin

The Vertex AI plugin provides interfaces to several Google generative AI models
through the [Vertex AI API](https://cloud.google.com/vertex-ai/generative-ai/docs/).

## Requirements

If you want to locally run flows that use this plugin, you need the
[Google Cloud CLI tool](https://cloud.google.com/sdk/docs/install) installed.

## Configuration

To use this plugin, import the `vertexai` package and call `vertexai.Init()`:

```go
import "github.com/firebase/genkit/go/plugins/vertexai"
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="init" adjust_indentation="auto" %}
```

The plugin requires you to specify your Google Cloud project ID, the
[region](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations)
to which you want to make Vertex API requests, and your Google Cloud project
credentials.

- By default, `vertexai.Init()` gets your Google Cloud project ID from the
  `GCLOUD_PROJECT` environment variable.

  You can also pass this value directly:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="initproj" adjust_indentation="auto" %}
  ```

- By default, `vertexai.Init()` gets the Vertex AI API location from the
  `GCLOUD_LOCATION` environment variable.

  You can also pass this value directly:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="initloc" adjust_indentation="auto" %}
  ```

- To provide API credentials, you need to set up Google Cloud Application
  Default Credentials.

  1.  To specify your credentials:

      - If you're running your flow from a Google Cloud environment (Cloud
        Functions, Cloud Run, and so on), this is set automatically.

      - On your local dev environment, do this by running:

        ```posix-terminal
        gcloud auth application-default login
        ```

      - For other environments, see the [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc)
        docs.

  1.  In addition, make sure the account is granted the Vertex AI User IAM role
      (`roles/aiplatform.user`). See the Vertex AI [access control](https://cloud.google.com/vertex-ai/generative-ai/docs/access-control)
      docs.

## Usage

### Generative models

To get a reference to a supported model, specify its identifier:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="model" adjust_indentation="auto" %}
```

The following models are supported: `gemini-1.0-pro`, `gemini-1.5-pro`, and
`gemini-1.5-flash`.

Model references have a `Generate()` method that calls the Vertex AI API:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="gen" adjust_indentation="auto" %}
```

See [Generating content](models.md) for more information.

### Embedding models

To get a reference to a supported embedding model, specify its identifier:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="embedder" adjust_indentation="auto" %}
```

The following models are supported: `textembedding-gecko@003`,
`textembedding-gecko@002`, `textembedding-gecko@001`, `text-embedding-004`,
`textembedding-gecko-multilingual@001`, `text-multilingual-embedding-002`, and
`multimodalembedding`.

Embedder references have an `Embed()` method that calls the Vertex AI API:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="embed" adjust_indentation="auto" %}
```

You can also pass an Embedder to an indexer's `Index()` method and a retriever's
`Retrieve()` method:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="index" adjust_indentation="auto" %}
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/vertexai.go" region_tag="retrieve" adjust_indentation="auto" %}
```

See [Retrieval-augmented generation (RAG)](rag.md) for more information.
