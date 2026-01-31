An example demonstrating how to manage prompts using Genkit's prompt loading system.

## Setup environment

## Setup environment

### How to Get Your Gemini API Key

To use the Google GenAI plugin, you need a Gemini API key.

1.  **Visit AI Studio**: Go to [Google AI Studio](https://aistudio.google.com/).
2.  **Create API Key**: Click on "Get API key" and create a key in a new or existing Google Cloud project.

For more details, check out the [official documentation](https://ai.google.dev/gemini-api/docs/api-key).

Export the API key as env variable `GEMINI_API_KEY` in your shell configuration.

```bash
export GEMINI_API_KEY='<Your api key>'
```

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

## Run the sample

```bash
genkit start -- uv run src/main.py
```

## Prompt Structure

- `prompts/`: Contains `.prompt` files (using [Dotprompt](https://genkit.dev/docs/dotprompt)).
- `prompts/_shared_partial.prompt`: A partial that can be included in other prompts.
- `prompts/nested/nested_hello.prompt`: A prompt demonstrating nested structure and partial inclusion.

## Testing This Demo

1. **Prerequisites**:
   ```bash
   export GEMINI_API_KEY=your_api_key
   ```
   Or the demo will prompt for the key interactively.

2. **Run the demo**:
   ```bash
   cd py/samples/prompt-demo
   ./run.sh
   ```

3. **Open DevUI** at http://localhost:4000

4. **Test the following flows**:
   - [ ] `chef_flow` - Generate a recipe (uses recipe.prompt)
   - [ ] `tell_story` - Generate a story with streaming
   - [ ] `robot_chef_flow` - Test prompt variants
   - [ ] Check that .prompt files in `prompts/` are loaded

5. **Test with file changes**:
   - Edit a .prompt file and verify hot reload works
   - Try different input parameters in DevUI

6. **Expected behavior**:
   - Prompts load from the `prompts/` directory
   - Output matches the schema defined in .prompt files
   - Streaming shows incremental text generation
