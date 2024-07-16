# Google Generative AI plugin

The Google Generative AI plugin provides interfaces to Google's Gemini models
through the [Gemini API](https://ai.google.dev/docs/gemini_api_overview).

## Configuration

To use this plugin, import the `googleai` package and call `googleai.Init()`:

```go
import "github.com/firebase/genkit/go/plugins/googleai"
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/googleai.go" region_tag="init" adjust_indentation="auto" %}
```

The plugin requires an API key for the Gemini API, which you can get from
[Google AI Studio](https://aistudio.google.com/app/apikey).

Configure the plugin to use your API key by doing one of the following:

- Set the `GOOGLE_GENAI_API_KEY` environment variable to your API key.

- Specify the API key when you initialize the plugin:

  ```golang
  {% includecode github_path="firebase/genkit/go/internal/doc-snippets/googleai.go" region_tag="initkey" adjust_indentation="auto" %}
  ```

  However, don't embed your API key directly in code! Use this feature only
  in conjunction with a service like Cloud Secret Manager or similar.

## Usage

### Generative models

To get a reference to a supported model, specify its identifier:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/googleai.go" region_tag="model" adjust_indentation="auto" %}
```

The following models are supported: `gemini-1.0-pro`, `gemini-1.5-pro`, and
`gemini-1.5-flash`.

Model references have a `Generate()` method that calls the Google AI API:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/googleai.go" region_tag="gen" adjust_indentation="auto" %}
```

See [Generating content](models.md) for more information.

### Embedding models

To get a reference to a supported embedding model, specify its identifier:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/googleai.go" region_tag="embedder" adjust_indentation="auto" %}
```

The following models are supported: `text-embedding-004` and `embedding-001`.

Embedder references have an `Embed()` method that calls the Google AI API:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/googleai.go" region_tag="embed" adjust_indentation="auto" %}
```

You can also pass an Embedder to an indexer's `Index()` method and a retriever's
`Retrieve()` method:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/googleai.go" region_tag="index" adjust_indentation="auto" %}
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/googleai.go" region_tag="retrieve" adjust_indentation="auto" %}
```

See [Retrieval-augmented generation (RAG)](rag.md) for more information.
