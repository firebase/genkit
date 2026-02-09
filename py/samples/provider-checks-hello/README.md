# checks-safety-hello

Demonstrates the Google Checks AI Safety plugin for Genkit. This sample
shows how to use both **evaluators** (for scoring content safety) and
**middleware** (for blocking unsafe input/output in real-time).

## Prerequisites

1. A Google Cloud project with the Checks API enabled
2. Google Cloud Application Default Credentials configured:
   ```bash
   gcloud auth application-default login
   ```
3. A Google GenAI API key (for the Gemini model)

## Setup

```bash
export GCLOUD_PROJECT=my-gcp-project
export GEMINI_API_KEY=your-api-key
```

## Running

```bash
./run.sh
```

The script will prompt for any required environment variables not yet set.

## What this sample demonstrates

### 1. Safety Evaluators

Registers Checks evaluators that can be used in the Genkit Dev UI to
evaluate model outputs against safety policies like `DANGEROUS_CONTENT`,
`HARASSMENT`, and `HATE_SPEECH`.

### 2. Safety Middleware

Wraps a Gemini model call with `checks_middleware` so that both input
and output are automatically classified. If either violates a policy,
the middleware returns a `blocked` response instead of the model output.

## Testing

1. Start the sample with `./run.sh`
2. Open the Genkit Dev UI (printed in the terminal)
3. Test the `safe_generate` flow with safe prompts — you should get normal responses
4. Test with unsafe prompts — the middleware should block and return a `blocked` finish reason
5. Check the evaluators tab to see registered Checks evaluators

## See Also

- [Google Checks AI Safety](https://checks.google.com/ai-safety)
- [Genkit Documentation](https://genkit.dev/)
