# Genkit Chat - Demo Application

See [../GEMINI.md](../GEMINI.md) for shared development guidelines and component documentation.

## Quick Start

```bash
# Start backend
cd backend && uv run fastapi dev

# Start frontend (in another terminal)
cd frontend && pnpm start
```

## Directory Structure

```
genkit-chat/
├── frontend/              # Angular 21 application
│   ├── src/app/
│   │   ├── features/      # Feature modules
│   │   ├── core/          # Services, guards
│   │   └── shared/        # Local shared utilities
│   └── src/assets/i18n/   # Translation files
└── backend/               # Python FastAPI server
    ├── main.py            # Routes, SSE streaming
    └── genkit_setup.py    # Plugin configuration
```

## Plugin Configuration

The backend dynamically loads plugins based on available environment variables. Each plugin
requires specific dependencies in `backend/pyproject.toml`.

### Supported Plugins

| Plugin | Environment Variables | Import Path | Package |
|--------|----------------------|-------------|---------|
| Google AI | `GOOGLE_GENAI_API_KEY` | `genkit.plugins.google_genai.GoogleAI` | `genkit-plugin-google-genai` |
| Vertex AI | `GOOGLE_CLOUD_PROJECT` | `genkit.plugins.vertex_ai.ModelGardenPlugin` | `genkit-plugin-vertex-ai` |
| Anthropic | `ANTHROPIC_API_KEY` | `genkit.plugins.anthropic.Anthropic` | `genkit-plugin-anthropic` |
| OpenAI | `OPENAI_API_KEY` | `genkit.plugins.compat_oai.OpenAI` | `genkit-plugin-compat-oai` |
| Cloudflare AI | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | `genkit.plugins.cf_ai.CfAI` | `genkit-plugin-cf-ai` |
| Ollama | (always tries) | `genkit.plugins.ollama.Ollama` | `genkit-plugin-ollama` |

### Adding a New Plugin

When adding a new plugin to the backend:

1. **Add the dependency** to `backend/pyproject.toml`:
   ```toml
   [project]
   dependencies = [
     # ... existing deps
     "genkit-plugin-<name>",
   ]

   [tool.uv.sources]
   genkit-plugin-<name> = { path = "../../../plugins/<name>", editable = true }
   ```

2. **Add the import** in `genkit_setup.py`:
   ```python
   if os.getenv("REQUIRED_ENV_VAR"):
       try:
           from genkit.plugins.<module_name> import PluginClass
           plugins.append(PluginClass())
           logger.info("Loaded <plugin> plugin")
       except ImportError:
           logger.warning("<plugin> plugin not installed")
   ```

3. **Run `uv sync`** to install the new dependency.

### Common Issues

**"Failed to resolve model X"**

This error occurs when a model is requested but the corresponding plugin isn't loaded.

Causes:
- Missing environment variable for the plugin
- Plugin not in `pyproject.toml` dependencies
- Wrong import path in `genkit_setup.py`

Debugging:
1. Check backend logs for "Loaded X plugin" messages
2. Verify environment variables are set
3. Run `uv sync` to ensure dependencies are installed

**OpenAI Import Path**

The OpenAI plugin uses `genkit.plugins.compat_oai`, NOT `genkit.plugins.openai`:
```python
# CORRECT
from genkit.plugins.compat_oai import OpenAI

# WRONG - this module doesn't exist
from genkit.plugins.openai import OpenAI
```

## Using @aspect/genkit-ui Components

This demo uses the shared `@aspect/genkit-ui` library:

```typescript
import { ChatBoxComponent } from '@aspect/genkit-ui/chat';

@Component({
  imports: [ChatBoxComponent],
  template: `
    <genkit-chat-box
      [messages]="messages"
      [isLoading]="isLoading"
      (send)="onSend($event)" />
  `
})
```

See the library README at `../genkit-ui/README.md` for full documentation.

## Frontend Default Models

The frontend has a fallback list of default models in `models.service.ts` for when the backend
is unavailable. These models MUST match actual models supported by the corresponding plugins.

**Cloudflare AI Models** - Use models from `plugins/cf-ai/src/genkit/plugins/cf_ai/model_info.py`:
- `@cf/meta/llama-3.3-70b-instruct-fp8-fast`
- `@cf/meta/llama-3.1-8b-instruct`
- `@cf/google/gemma-3-12b-it` (vision)
- `@cf/mistral/mistral-small-3.1-24b-instruct` (vision)
- `@cf/deepseek-ai/deepseek-r1-distill-qwen-32b`
- `@cf/qwen/qwen2.5-coder-32b-instruct`

**Note**: Model names with `@hf/` prefix are Hugging Face hosted, while `@cf/` are Cloudflare hosted.
