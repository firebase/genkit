# Quick Start for New Engineers

Welcome to the Genkit Python SDK team! This guide will get you productive fast.

## Your First Day Checklist

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FIRST DAY CHECKLIST                                │
│                                                                             │
│   [ ] Read this document                                                    │
│   [ ] Set up your development environment (see below)                       │
│   [ ] Run the tests: uv run pytest .                                        │
│   [ ] Run the linter: ./bin/lint                                            │
│   [ ] Run a sample: cd samples/hello-world && ./run.sh                      │
│   [ ] Open the Dev UI: http://localhost:4000                                │
│   [ ] Read GEMINI.md for coding guidelines                                  │
│   [ ] Join the Discord: https://discord.gg/qXt5zzQKpc                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Setting Up Your Environment

### 1. Install Prerequisites

```bash
# macOS
brew install uv python@3.12

# Linux (Debian/Ubuntu)
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo apt install python3.12
```

### 2. Clone and Setup

```bash
# Clone the repo
git clone https://github.com/firebase/genkit.git
cd genkit

# Run the setup script
py/bin/setup

# Verify everything works
cd py
uv run pytest packages/genkit/tests -v --tb=short
```

### 3. Run Your First Sample

```bash
# Set your API key
export GEMINI_API_KEY="your-key-here"

# Run the hello-world sample
cd py/samples/hello-world
./run.sh

# Open the Dev UI in your browser
# http://localhost:4000
```

## Understanding the Codebase

### Where Things Live

```
py/
├── packages/genkit/          # The core framework
│   └── src/genkit/
│       ├── __init__.py       # START HERE - main exports
│       ├── ai/               # User-facing API (Genkit class)
│       ├── blocks/           # AI building blocks
│       ├── core/             # Foundation (actions, registry)
│       └── web/              # Dev server
│
├── plugins/                  # Provider implementations
│   ├── google-genai/         # Google AI / Vertex AI
│   ├── ollama/               # Local models
│   └── ...
│
├── samples/                  # Example applications
│   ├── hello-world/          # Start here!
│   ├── rag/                  # RAG example
│   └── ...
│
├── engdoc/                   # Engineering docs (you are here)
│
├── GEMINI.md                 # ⚠️ IMPORTANT: Coding guidelines
│
└── bin/                      # Development scripts
    ├── lint                  # Run before committing
    └── setup                 # Initial setup
```

### The 5 Files You Should Read First

1. **`py/GEMINI.md`** - Coding guidelines, MUST read before writing code
2. **`packages/genkit/src/genkit/__init__.py`** - What's exported to users
3. **`packages/genkit/src/genkit/ai/_base_async.py`** - The Genkit class
4. **`packages/genkit/src/genkit/core/action/_action.py`** - The Action class
5. **`packages/genkit/src/genkit/core/registry.py`** - The Registry

## How to Make Your First Change

### Example: Adding a Helper Function

Let's add a simple utility function. This shows the typical workflow:

```bash
# 1. Create a new branch
git checkout -b add-my-helper

# 2. Make your change (edit files)
# ...

# 3. Run linting (REQUIRED before committing)
./bin/lint

# 4. Run tests
uv run pytest packages/genkit/tests -v

# 5. Commit your change
git add .
git commit -m "Add my_helper function for XYZ"

# 6. Push and create PR
git push -u origin add-my-helper
gh pr create
```

### Key Rules to Remember

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RULES YOU MUST FOLLOW                                │
│                                                                             │
│   1. ALWAYS run ./bin/lint before committing                                │
│      - Lint failures = PR rejection                                         │
│                                                                             │
│   2. NEVER edit core/typing.py                                              │
│      - It's auto-generated from the JS SDK                                  │
│                                                                             │
│   3. ALWAYS add tests for new code                                          │
│      - No tests = no merge                                                  │
│                                                                             │
│   4. Use async/await properly                                               │
│      - Use httpx.AsyncClient, not requests                                  │
│      - Use aiofiles for file I/O in async code                              │
│                                                                             │
│   5. Type everything                                                        │
│      - All functions need type hints                                        │
│      - Avoid Any unless absolutely necessary                                │
│                                                                             │
│   6. Follow the docstring format in GEMINI.md                               │
│      - Google-style docstrings                                              │
│      - Include ELI5 explanations for complex modules                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Common Tasks

### Running Tests

```bash
# All tests
uv run pytest .

# Specific test file
uv run pytest packages/genkit/tests/genkit/blocks/middleware_test.py -v

# Tests matching a pattern
uv run pytest -k "test_retry" -v

# With coverage
uv run pytest --cov=genkit packages/genkit/tests
```

### Debugging

```bash
# Run a sample with debug logging
GENKIT_LOG_LEVEL=debug ./run.sh

# Run Python with debugger
uv run python -m pdb src/main.py

# Check what actions are registered
uv run python -c "
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI
ai = Genkit(plugins=[GoogleAI()])
# Actions are registered lazily, so generate first
"
```

### Adding a New Plugin

See `plugins/google-genai/` as an example:

1. Create directory structure:
   ```
   plugins/my-plugin/
   ├── pyproject.toml
   ├── src/genkit/plugins/my_plugin/
   │   ├── __init__.py
   │   ├── plugin.py       # Plugin class
   │   └── models/         # Model implementations
   └── tests/
   ```

2. Add to workspace in `py/pyproject.toml`

3. Implement the Plugin interface:
   ```python
   from genkit.core.plugin import Plugin

   class MyPlugin(Plugin):
       name = "my-plugin"

       async def init(self, registry: Registry) -> None:
           # Register your actions here
           pass

       async def resolve(self, kind: ActionKind, name: str) -> Action | None:
           # Create actions on-demand
           pass
   ```

## Debugging Tips

### "My action isn't being found"

```python
# Check if it's registered
action = await ai.registry.lookup_action("/model/my-model")
if action is None:
    print("Not registered!")

# List all registered actions
for key in ai.registry._actions.keys():
    print(key)
```

### "My middleware isn't running"

```python
# Middleware runs in order - first wraps last
response = await ai.generate(
    model='...',
    prompt='...',
    use=[
        first_middleware(),   # Runs first (outermost)
        second_middleware(),  # Runs second
    ],
)
```

### "Tests are failing with type errors"

```bash
# Run type checkers separately
uv run ty check
uv run pyrefly check
uv run pyright
```

## Getting Help

1. **Check the docs**: Start with `GEMINI.md` and this engdoc folder
2. **Search the codebase**: `rg "what you're looking for"`
3. **Ask on Discord**: https://discord.gg/qXt5zzQKpc
4. **Check existing PRs**: Look for similar changes

## Next Steps

After you're comfortable:

1. Pick up a "good first issue" from GitHub
2. Read the [Architecture Guide](./README.md) for deeper understanding
3. Explore the [Glossary](../extending/glossary.md) for terminology
4. Review the [Feature Parity Analysis](../parity-analysis/feature_parity_analysis.md)
