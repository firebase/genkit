# Format Demo

This sample demonstrates the different output formats supported by Genkit Python.

## Formats Demonstrated

1.  **Text (`text`)**: Raw text output.
2.  **JSON (`json`)**: Structured JSON object output.
3.  **Array (`array`)**: JSON array of items.
4.  **Enum (`enum`)**: Single value from a predefined list.
5.  **JSONL (`jsonl`)**: Newline-delimited JSON objects (great for streaming).

## Running

1.  Set your `GEMINI_API_KEY` environment variable.
2.  Run the sample:

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
export GEMINI_API_KEY=your-key
./run.sh
```

Then use the Genkit Developer UI to test the flows.
