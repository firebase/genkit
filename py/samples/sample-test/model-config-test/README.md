# Model Config Testing Tool

A tool to test model performance across different models and configuration variations.

## Setup

1.  Ensure you have `uv` installed.
2.  Set your API keys (e.g., `GOOGLE_GENAI_API_KEY`).

## Usage

Run the tool:

```bash
uv run test_model_performance.py --models googleai/gemini-2.0-flash
```

## Features

-   **Model Discovery**: Automatically finds registered models.
-   **Config Discovery**: Inspects model schema to find parameters.
-   **Variations**: Tests min, max, midpoint, and default values.
-   **Report**: Generates a Markdown report with pass/fail stats and detailed results.
