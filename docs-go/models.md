# Generating content

Genkit provides an easy interface for generating content with LLMs.

## Models

Models in Genkit are libraries and abstractions that provide access to
various Google and non-Google LLMs.

Models are fully instrumented for observability and come with tooling
integrations provided by the Genkit Developer UI -- you can try any model using
the model runner.

When working with models in Genkit, you first need to configure the model you
want to work with. Model configuration is performed by the plugin system. In
this example you are configuring the Vertex AI plugin, which provides Gemini
models.

```golang
import {
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="import" %}
}
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="init" adjust_indentation="auto" %}
```

Note: Different plugins and models use different methods of
authentication. For example, Vertex API uses the Google Auth Library so it can
pull required credentials using Application Default Credentials.

To use models provided by the plugin, you need a reference to the specific model
and version:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="model" adjust_indentation="auto" %}
```

## Supported models

Genkit provides model support through its plugin system. The following plugins
are officially supported:

| Plugin                    | Models                                                                   |
| ------------------------- | ------------------------------------------------------------------------ |
| [Google Generative AI][1] | Gemini Pro, Gemini Pro Vision                                            |
| [Google Vertex AI][2]     | Gemini Pro, Gemini Pro Vision, Gemini 1.5 Flash, Gemini 1.5 Pro, Imagen2 |
| [Ollama][3]               | Many local models, including Gemma, Llama 2, Mistral, and more           |

[1]: plugins/google-genai.md
[2]: plugins/vertex-ai.md
[3]: plugins/ollama.md

See the docs for each plugin for setup and usage information.

<!-- TODO: There's also a wide variety of community supported models available
you can discover by ... -->

## How to generate content

Genkit provides a simple helper function for generating content with models.

To just call the model:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="call" adjust_indentation="auto" %}
```

You can pass options along with the model call. The options that are supported
depend on the model and its API.

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="options" adjust_indentation="auto" %}
```

### Streaming responses

Genkit supports chunked streaming of model responses. To use chunked streaming,
pass a callback function to `Generate()`:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="streaming" adjust_indentation="auto" %}
```

## Multimodal input

If the model supports multimodal input, you can pass image prompts:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="multimodal" adjust_indentation="auto" %}
```

<!-- TODO: gs:// wasn't working for me. HTTP? -->

The exact format of the image prompt (`https` URL, `gs` URL, `data` URI) is
model-dependent.

## Function calling (tools)

Genkit models provide an interface for function calling, for models that support
it.

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="tools" adjust_indentation="auto" %}
```

This will automatically call the tools in order to fulfill the user prompt.

<!-- TODO: returnToolRequests: true` -->

<!--

### Adding retriever context

Documents from a retriever can be passed directly to `generate` to provide
grounding context:

```javascript
const docs = await companyPolicyRetriever({ query: question });

await generate({
  model: geminiPro,
  prompt: `Answer using the available context from company policy: ${question}`,

  context: docs,
});
```

The document context is automatically appended to the content of the prompt
sent to the model.

-->

## Recording message history

Genkit models support maintaining a history of the messages sent to the model
and its responses, which you can use to build interactive experiences, such as
chatbots.

In the first prompt of a session, the "history" is simply the user prompt:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="hist1" adjust_indentation="auto" %}
```

When you get a response, add it to the history:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="hist2" adjust_indentation="auto" %}
```

You can serialize this history and persist it in a database or session storage.
For subsequent user prompts, add them to the history before calling
`Generate()`:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="hist3" adjust_indentation="auto" %}
```

If the model you're using supports the system role, you can use the initial
history to set the system message:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/models.go" region_tag="hist4" adjust_indentation="auto" %}
```
