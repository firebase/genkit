# Genkit Microsoft Foundry Plugin

`genkit-plugin-msfoundry` is a plugin for using Microsoft Foundry models with [Genkit](https://github.com/firebase/genkit).

Microsoft Foundry (formerly Azure AI Foundry) provides access to 11,000+ AI models from multiple providers including OpenAI, Anthropic, DeepSeek, xAI, Meta, Mistral, Cohere, and more.

## Documentation Links

- **Microsoft Foundry Portal**: https://ai.azure.com/
- **Model Catalog**: https://ai.azure.com/catalog/models
- **SDK Overview**: https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview
- **Models Documentation**: https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models
- **Deployment Types**: https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types
- **Python SDK**: https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme

## Installation

```bash
pip install genkit-plugin-msfoundry
```

## Setup

You'll need a Microsoft Foundry resource deployed. You can deploy one on the [Azure Portal](https://portal.azure.com/) or via [Microsoft Foundry Portal](https://ai.azure.com/).

Once you have your instance running, get the endpoint and key from the Azure Portal under "Keys and Endpoint".

### Environment Variables

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_API_KEY="your-api-key"
export OPENAI_API_VERSION="2024-10-21"
```

### Direct Configuration

```python
from genkit import Genkit
from genkit.plugins.msfoundry import MSFoundry, gpt4o

ai = Genkit(
    plugins=[
        MSFoundry(
            api_key="your-key",
            endpoint="https://your-resource.openai.azure.com/",
            deployment="your-deployment-name",
            api_version="2024-10-21",
        )
    ],
    model=gpt4o,
)
```

### Azure Managed Identity (Azure AD / Entra ID)

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from genkit import Genkit
from genkit.plugins.msfoundry import MSFoundry, gpt4o

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    credential, "https://cognitiveservices.azure.com/.default"
)

ai = Genkit(
    plugins=[
        MSFoundry(
            azure_ad_token_provider=token_provider,
            endpoint="https://your-resource.openai.azure.com/",
            deployment="your-deployment-name",
            api_version="2024-10-21",
        )
    ],
    model=gpt4o,
)
```

## Basic Examples

### Text Generation

```python
response = await ai.generate(prompt="Tell me a joke.")
print(response.text)
```

### Multimodal (Vision)

```python
from genkit.types import Media, MediaPart, Part, TextPart
from genkit.plugins.msfoundry import MSFoundryConfig

response = await ai.generate(
    model=gpt4o,
    prompt=[
        Part(root=TextPart(text="What animal is in the photo?")),
        Part(root=MediaPart(media=Media(url=image_url))),
    ],
    config=MSFoundryConfig(
        visual_detail_level="low",  # Reduces token usage
    ),
)
print(response.text)
```

### Embeddings

```python
from genkit.blocks.document import Document

response = await ai.embed(
    embedder="msfoundry/text-embedding-3-small",
    input=[Document(content="Hello, world!")],
)
print(response.embeddings[0].embedding)
```

## Supported Models

Microsoft Foundry provides access to 11,000+ models. Below are some key models supported by this plugin with pre-defined references:

### OpenAI GPT Models

- `gpt-4o`, `gpt-4o-mini`
- `gpt-4`, `gpt-4.5`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`
- `gpt-3.5-turbo`
- `gpt-5`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-chat`, `gpt-5-codex`, `gpt-5-pro`
- `gpt-5.1`, `gpt-5.1-chat`, `gpt-5.1-codex`, `gpt-5.1-codex-mini`, `gpt-5.1-codex-max`
- `gpt-5.2`, `gpt-5.2-chat`, `gpt-5.2-codex`
- `gpt-oss-120B`

### OpenAI O-Series (Reasoning Models)

- `o1`, `o1-mini`, `o1-preview`
- `o3`, `o3-mini`, `o3-pro`
- `o4-mini`, `codex-mini`

### Anthropic Claude Models

- `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`
- `claude-opus-4-1`

### DeepSeek Models

- `DeepSeek-V3.2`, `DeepSeek-V3.2-Speciale`, `DeepSeek-V3.1`
- `DeepSeek-R1-0528`, `DeepSeek-V3-0324`
- `MAI-DS-R1`

### xAI Grok Models

- `grok-4`, `grok-4-fast-reasoning`, `grok-4-fast-non-reasoning`
- `grok-3`, `grok-3-mini`
- `grok-code-fast-1`

### Meta Llama Models

- `Llama-4-Maverick-17B-128E-Instruct-FP8`

### Mistral Models

- `Mistral-Large-3`
- `mistral-document-ai-2505`

### Other Models

- `Kimi-K2-Thinking` (Moonshot AI)
- `model-router` (Microsoft)

### Embedding Models

- `text-embedding-3-small` (1536 dimensions)
- `text-embedding-3-large` (3072 dimensions)
- `text-embedding-ada-002` (1536 dimensions)
- `embed-v-4-0` (Cohere - 1536 dimensions, text and image)

### Using Any Model Dynamically

You can use any model from the catalog by specifying the model name:

```python
from genkit.plugins.msfoundry import msfoundry_model

# Use any model from the 11,000+ catalog
model_ref = msfoundry_model("DeepSeek-V3.2")
response = await ai.generate(model=model_ref, prompt="...")
```

### Dynamic Model Discovery

The plugin can automatically discover models from your Azure OpenAI resource:

```python
from genkit import Genkit
from genkit.plugins.msfoundry import MSFoundry

ai = Genkit(
    plugins=[
        MSFoundry(
            api_key="your-key",
            endpoint="https://your-resource.openai.azure.com/",
            discover_models=True,  # Fetches models from Azure API
        )
    ],
)

# All models deployed to your resource are now available
# including fine-tuned models and any base models
```

When `discover_models=True`, the plugin calls the `/openai/models` API endpoint to list:
- Base models available in your region
- Fine-tuned models you've created
- Model capabilities (chat, completion, embeddings)
- Lifecycle status (preview, generally-available)

This is useful for:
- Discovering what models are available in your Azure resource
- Using fine-tuned models without manual configuration
- Keeping the Dev UI in sync with your actual deployments

See: [Models - List API](https://learn.microsoft.com/en-us/rest/api/azureopenai/models/list)

## Configuration

The plugin supports all standard OpenAI parameters:

```python
from genkit.plugins.msfoundry import MSFoundryConfig

config = MSFoundryConfig(
    temperature=0.7,
    max_tokens=1000,
    top_p=0.9,
    frequency_penalty=0.5,
    presence_penalty=0.5,
    stop=["END"],
    seed=42,
    visual_detail_level="high",  # For vision models: "auto", "low", "high"
)

response = await ai.generate(prompt="...", config=config)
```

## References

### Microsoft Foundry Documentation

- [Microsoft Foundry Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- [What is Microsoft Foundry?](https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-foundry)
- [Model Catalog Overview](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/model-catalog-overview)
- [Foundry Models Sold Directly by Azure](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models)
- [SDK Overview](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/sdk-overview)
- [Quickstart Guide](https://learn.microsoft.com/en-us/azure/ai-foundry/quickstarts/get-started-code)

### Model-Specific Documentation

- [OpenAI Models](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/models)
- [DeepSeek Models](https://ai.azure.com/explore/models?selectedCollection=DeepSeek)
- [Anthropic Claude](https://ai.azure.com/explore/models?selectedCollection=Anthropic)
- [xAI Grok](https://ai.azure.com/explore/models?selectedCollection=xAI)
- [Meta Llama](https://ai.azure.com/explore/models?selectedCollection=Meta)
- [Mistral AI](https://ai.azure.com/explore/models?selectedCollection=Mistral+AI)
- [Cohere](https://ai.azure.com/explore/models?selectedCollection=Cohere)

### API References

- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat/create)
- [Azure OpenAI REST API](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference)

## Disclaimer

This is a community plugin and is not officially supported or endorsed by Microsoft Corporation.

"Microsoft", "Azure", "Azure OpenAI", "Microsoft Foundry", and "Azure AI Foundry" are
trademarks of Microsoft Corporation. This plugin is developed independently and is not
affiliated with, endorsed by, or sponsored by Microsoft.

The use of Microsoft's APIs is subject to Microsoft's terms of service. Users are
responsible for ensuring their usage complies with Microsoft's API terms and any
applicable rate limits or usage policies.

## License

Apache 2.0
