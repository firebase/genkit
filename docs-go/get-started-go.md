# Get started with Genkit using Go (alpha)

The Firebase Genkit libraries for Go are now available for preview! Because the
Go libraries are currently in Alpha, you might see API and functional changes as
development progresses. We recommend using it only for prototyping and
exploration.

If you discover issues with the libraries or this documentation please report
them in our [GitHub repository](https://github.com/firebase/genkit/).

This page shows you how to get started with Genkit in a Go project.

## Requirements

Go 1.22 or later. See [Download and install](https://go.dev/doc/install) in
the official Go docs.

## Install Genkit dependencies {:#install}

1.  If you don't already have a Go project that you want to add AI features to,
    create a new module in an empty directory:

    ```posix-terminal
    go mod init example/genkit-getting-started
    ```

1.  Install the Genkit package and the `googleai` model plugin:

    ```posix-terminal
    go get "github.com/firebase/genkit/go"

    go get "github.com/firebase/genkit/go/plugins/googleai"
    ```

## Configure your model API key

For this guide, we’ll show you how to use the Gemini API which provides a
generous free tier and does not require a credit card to get started. To use the
Gemini API, you'll need an API key. If you don't already have one, create a key
in Google AI Studio.

[Get an API key from Google AI Studio](https://makersuite.google.com/app/apikey)

After you’ve created an API key, set the `GOOGLE_GENAI_API_KEY` environment
variable to your key with the following command:

```posix-terminal
export GOOGLE_GENAI_API_KEY=<your API key>
```

Note: While this tutorial uses the Gemini API from AI Studio, Genkit supports a
wide variety of model providers including
[Gemini from Vertex AI](/docs/genkit/plugins/vertex-ai#generative_ai_models),
Anthropic’s Claude 3 models and Llama 3.1 through the
[Vertex AI Model Garden](/docs/genkit/plugins/vertex-ai#anthropic_claude_3_on_vertex_ai_model_garden),
open source models through
[Ollama](/docs/genkit/plugins/ollama), and several other
[community-supported providers](/docs/genkit/models#models-supported) like
OpenAI and Cohere.

## Make your first request

Get started with Genkit in just a few lines of simple code.

```go
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/init/main.go" region_tag="main" adjust_indentation="auto" %}
```

## Optional: Install the Genkit CLI

Genkit has a CLI and developer UI that helps you locally test and debug your
app. To install these tools:

1.  If you don't already have Node 20 or newer on your system,
    the [`nvm`](https://github.com/nvm-sh/nvm) and
    [`nvm-windows`](https://github.com/coreybutler/nvm-windows) tools are a
    convenient way to install specific versions of Node if it's not already
    installed on your system. These tools install Node on a per-user basis, so you
    don't need to make system-wide changes.

    To install `nvm`:

    - {Linux, macOS, etc.}

      Run the following command:

      ```posix-terminal
      curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
      ```

    - {Windows}

      Download and run the installer as described in the [nvm-windows docs](https://github.com/coreybutler/nvm-windows?tab=readme-ov-file#install-nvm-windows).

    Then, to install Node and `npm`, open a new shell and run the following
    command:

    ```posix-terminal
    nvm install 20
    ```

1.  Install the Genkit CLI by running the following command:

    ```posix-terminal
    npm i -g genkit-cli
    ```

    This command installs the Genkit CLI into your Node installation directory
    so that it can be used outside of a Node project.

## Next steps

Now that you’re set up to make model requests with Genkit, learn how to use more
Genkit capabilities to build your AI-powered apps and workflows. To get started
with additional Genkit capabilities, see the following guides:

*   [Generating content](/docs/genkit-go/models): Learn how to use Genkit’s unified
    generation API to generate text and structured data from any supported
    model.
*   [Creating flows](/docs/genkit-go/flows): Learn how to use special Genkit
    functions, called flows, that provide end-to-end observability for workflows
    and rich debugging from Genkit tooling.
*   [Prompting models](/docs/genkit-go/prompts): Learn how Genkit lets you treat
    prompt templates as functions, encapsulating model configurations and
    input/output schema.
