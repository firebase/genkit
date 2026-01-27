# Hello world

## Setup environment

### How to Get Your Gemini API Key

To use the Google GenAI plugin, you need a Gemini API key.

1.  **Visit AI Studio**: Go to [Google AI Studio](https://aistudio.google.com/).
2.  **Create API Key**: Click on "Get API key" and create a key in a new or existing Google Cloud project.

For more details, check out the [official documentation](https://ai.google.dev/gemini-api/docs/api-key).

Export the API key as env variable `GEMINI_API_KEY`:

```bash
export GEMINI_API_KEY=<Your api key>
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

```bash
uv venv
source .venv/bin/activate
```

## Run the sample

```bash
genkit start -- uv run src/main.py
```

## Testing This Demo

1. **Run the demo** (CLI-based):
   ```bash
   uv run python src/main.py
   ```

2. **Test the trivia game**:
   - [ ] The AI greets you and asks for a trivia theme
   - [ ] Type a theme (e.g., "science", "movies")
   - [ ] When questions appear, they're tool interrupts
   - [ ] Answer the questions and see AI reactions

3. **Test interrupt flow**:
   - [ ] Verify `present_questions` tool triggers interrupt
   - [ ] Check that game waits for your input
   - [ ] Confirm AI responds to your answers appropriately

4. **Expected behavior**:
   - AI acts as enthusiastic game host
   - Questions pause for user input (interrupt)
   - Answers are evaluated with dramatic responses
   - Game loop continues until you exit (Ctrl+C)
