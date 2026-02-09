# Menu Sample

### How to Get Your Gemini API Key

To use the Google GenAI plugin, you need a Gemini API key.

1.  **Visit AI Studio**: Go to [Google AI Studio](https://aistudio.google.com/).
2.  **Create API Key**: Click on "Get API key" and create a key in a new or existing Google Cloud project.

For more details, check out the [official documentation](https://ai.google.dev/gemini-api/docs/api-key).

### Monitoring and Running

For an enhanced development experience, use the provided `run.sh` script to start the sample with automatic reloading:

```bash
./run.sh
```

This script uses `watchmedo` to monitor changes in:
- `src/` (Python logic)
- `../../packages` (Genkit core)
- `../../plugins` (Genkit plugins)
- File patterns: `*.py`, `*.prompt`, `*.json`

Changes will automatically trigger a restart of the sample. You can also pass command-line arguments directly to the script, e.g., `./run.sh --some-flag`.

## Setup environment

```bash
export GEMINI_API_KEY=<Your api key>
```

## Run the sample

```bash
genkit start -- uv run python -m src.main
```

## Testing This Demo

1. **Open DevUI** at http://localhost:4000

2. **Test the different cases**:
   - [ ] Case 01: Basic menu prompts
   - [ ] Case 02: Menu analysis with tools
   - [ ] Case 03: Menu recommendations flow
   - [ ] Case 04: Dietary restrictions handling
   - [ ] Case 05: Multi-language menu support

3. **Expected behavior**:
   - All prompts/flows appear in DevUI
   - Menu items are analyzed correctly
   - Tools provide realistic restaurant data
