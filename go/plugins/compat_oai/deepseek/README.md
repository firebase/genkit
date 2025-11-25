# DeepSeek Plugin

This plugin provides a simple interface for using DeepSeek's services.

## Prerequisites

- Go installed on your system
- A DeepSeek API key

## Usage

Here's a simple example of how to use the DeepSeek plugin:

```go
import (
  // ignoring Genkit imports
  deepseek "github.com/firebase/genkit/go/plugins/compat_oai/deepseek"
  "github.com/openai/openai-go"
)
// Initialize the DeepSeek plugin with your API key
oai := &deepseek.DeepSeek{Opts: []option.RequestOption{option.WithAPIKey(apiKey)}}

// Initialize Genkit with the DeepSeek plugin
g, err := genkit.Init(ctx,
    genkit.WithDefaultModel("deepseek/deepseek-chat"),
    genkit.WithPlugins(oai),
)
if err != nil {
    // handle errors
}

config := &openai.ChatCompletionNewParams{
    // define optional config fields
}

resp, err = genkit.Generate(ctx, g,
    ai.WithPromptText("Write a short sentence about artificial intelligence."),
    ai.WithConfig(config),
)
```

## Running Tests

First, set your DeepSeek API key as an environment variable:

```bash
export DEEPSEEK_API_KEY=<your-api-key>
```

By default, `baseURL` is set to "<https://api.deepseek.com/v1>". However, if you
want to use a custom value, you can set `DEEPSEEK_BASE_URL` environment variable:

```bash
export DEEPSEEK_BASE_URL=<your-custom-base-url>
```

### Running All Tests

To run all tests in the directory:

```bash
go test -v .
```

### Running Tests from Specific Files

To run tests from a specific file:

```bash
# Run only generate_live_test.go tests
go test -run "^TestGenerator"

# Run only deepseek_live_test.go tests
go test -run "^TestPlugin"
```

### Running Individual Tests

To run a specific test case:

```bash
# Run only the streaming test from deepseek_live_test.go
go test -run "TestPlugin/streaming"

# Run only the Complete test from generate_live_test.go
go test -run "TestGenerator_Complete"

# Run only the Stream test from generate_live_test.go
go test -run "TestGenerator_Stream"
```

### Test Output Verbosity

Add the `-v` flag for verbose output:

```bash
go test -v -run "TestPlugin/streaming"
```

Note: All live tests require the DEEPSEEK_API_KEY environment variable to be set. Tests will be skipped if the API key is not provided.
