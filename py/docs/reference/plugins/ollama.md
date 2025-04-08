# Ollama


## Installation

```bash
pip3 install genkit-plugin-ollama
```

You will need to download and install Ollama separately: [https://ollama.com/download](https://ollama.com/download)

User ollama CLI to pull the models you would like to use. For example:

```bash
ollama pull gemma3
ollama pull nomic-embed-text
```

## Configuration

```py
from genkit.plugins.ollama import Ollama, ModelDefinition, EmbeddingModelDefinition

ai = Genkit(
    plugins=[
        Ollama(
           models=[
               ModelDefinition(name='gemma3'),
               ModelDefinition(name='mistral-nemo'),
           ],
           embedders=[
               EmbeddingModelDefinition(
                   name='nomic-embed-text',
                   dimensions=512,
               )
           ],
        )
    ],
)
```

Then use Ollama models and embedders by specifying `ollama/` prefix:

```py
genereate_response = await ai.generate(
    prompt='...',
    model='ollama/gemma3',
)

embedding_response = await ai.embed(
    embedder='ollama/nomic-embed-text',
    documents=[Document.from_text('...')],
)
```

## API Reference

::: genkit.plugins.ollama.plugin_api
    options:
      inherited_members: false
