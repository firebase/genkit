# Ollama Integration Tests

This directory contains integration tests for the Ollama plugin's structured output feature. These tests require a running Ollama instance and are tagged with `integration` to separate them from unit tests.

## Prerequisites

1. **Ollama must be running**: Install and start Ollama from https://ollama.com
2. **Models must be available**: Pull at least one model that supports structured output

### Recommended Models

For best results, use models that support structured output:
- `llama3.2` (default for both chat and generate)
- `llama3.1`
- `qwen2.5`
- `mistral`

Pull a model:
```bash
ollama pull llama3.2
```

## Running Integration Tests

### Run all integration tests:
```bash
go test -tags=integration -v ./go/plugins/ollama/...
```

### Run specific integration test:
```bash
go test -tags=integration -v -run TestIntegration_ChatModelWithSchema ./go/plugins/ollama/
```

### Run with custom configuration:
```bash
# Use custom Ollama server address
OLLAMA_SERVER_ADDRESS=http://localhost:11434 go test -tags=integration -v ./go/plugins/ollama/

# Use specific models
OLLAMA_CHAT_MODEL=llama3.1 OLLAMA_GENERATE_MODEL=llama3.1 go test -tags=integration -v ./go/plugins/ollama/
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_SERVER_ADDRESS` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_CHAT_MODEL` | Model to use for chat tests | `llama3.2` |
| `OLLAMA_GENERATE_MODEL` | Model to use for generate tests | `llama3.2` |

## Test Coverage

The integration tests validate:

### 8.1 Chat Model with Schema (TestIntegration_ChatModelWithSchema)
- Makes actual API call to Ollama chat endpoint with schema
- Verifies response conforms to schema
- **Validates Requirements**: 1.1, 1.2, 1.3, 4.1, 4.2

### 8.2 Generate Model with Schema (TestIntegration_GenerateModelWithSchema)
- Makes actual API call to Ollama generate endpoint with schema
- Verifies response conforms to schema
- **Validates Requirements**: 1.1, 1.2, 1.4, 4.1, 4.2

### 8.3 Schema-less JSON Mode (TestIntegration_SchemalessJSONMode)
- Makes API calls with format: "json" and no schema
- Verifies responses are valid JSON
- **Validates Requirements**: 2.1, 2.2

### 8.4 Streaming with Schemas (TestIntegration_StreamingWithSchema)
- Makes streaming API calls with schemas
- Verifies chunks are parsed correctly
- Verifies final merged output is complete
- **Validates Requirements**: 5.1, 5.2, 5.3, 5.4

### 8.5 Error Scenarios (TestIntegration_ErrorScenarios)
- Tests Ollama API error responses
- Tests invalid model names
- Verifies error messages are properly propagated
- **Validates Requirements**: 6.1, 6.4

## Troubleshooting

### Tests are skipped
If tests are skipped with messages like "Ollama not available", ensure:
1. Ollama is running: `ollama serve`
2. The server address is correct
3. The firewall allows connections to Ollama

### Model not found
If tests are skipped with "Model not available":
1. Pull the required model: `ollama pull llama3.2`
2. Or specify a different model using environment variables

### Tests timeout
If tests timeout:
1. Ensure your machine has sufficient resources
2. Try using a smaller/faster model
3. Increase the timeout in the test code if needed

### Connection refused
If you see "connection refused" errors:
1. Check Ollama is running: `curl http://localhost:11434/api/tags`
2. Verify the server address matches your Ollama configuration
3. Check for firewall or network issues

## CI/CD Integration

To run integration tests in CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Start Ollama
  run: |
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &
    sleep 5
    ollama pull llama3.2

- name: Run Integration Tests
  run: go test -tags=integration -v ./go/plugins/ollama/...
```

## Notes

- Integration tests make real API calls and may take several seconds to complete
- Tests require network access to the Ollama server
- Some tests may produce different outputs depending on the model used
- The tests validate structure and format, not specific content
