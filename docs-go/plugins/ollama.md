# Ollama plugin

The Ollama plugin provides interfaces to any of the local LLMs supported by
[Ollama](https://ollama.com/).

## Prerequisites

This plugin requires that you first install and run the Ollama server. You can
follow the instructions on the [Download Ollama](https://ollama.com/download)
page.

Use the Ollama CLI to download the models you are interested in. For example:

```posix-terminal
ollama pull gemma2
```

For development, you can run Ollama on your development machine. Deployed apps
usually run Ollama on a different, GPU-accelerated, machine from the app backend
that runs Genkit.

## Configuration

To use this plugin, call `ollama.Init()`, specifying the address of your Ollama
server:

```go
import "github.com/firebase/genkit/go/plugins/ollama"
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/ollama.go" region_tag="init" %}
```

## Usage

To generate content, you first need to create a model definition based on the
model you installed and want to use. For example, if you installed Gemma 2:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/ollama.go" region_tag="definemodel" %}
```

Then, you can use the model reference to send requests to your Ollama server:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/ollama.go" region_tag="gen" %}
```

See [Generating content](models.md) for more information.
