# OpenAI Plugin

This plugin provides a simple interface for using OpenAI's services.

## Prerequisites

- Go installed on your system
- An OpenAI API key

## Usage

Here's a simple example of how to use the OpenAI plugin:

```go
// import "github.com/firebase/genkit/go/plugins/compat_oai/openai"
// Initialize the OpenAI plugin with your API key
oai := openai.NewPlugin(apiKey)

// Initialize Genkit with the OpenAI plugin
g, err := genkit.Init(ctx,
    genkit.WithDefaultModel("openai/gpt-4o-mini"),
    genkit.WithPlugins(oai),
)
if err != nil {
    // handle errors
}

config := &ai.GenerationCommonConfig{
    // define optional config fields
}

resp, err = genkit.Generate(ctx, g,
    ai.WithPromptText("Write a short sentence about artificial intelligence."),
    ai.WithConfig(config),
)
```

## Running Tests

First, set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY=<your-api-key>
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

# Run only openai_live_test.go tests
go test -run "^TestPlugin"
```

### Running Individual Tests
To run a specific test case:
```bash
# Run only the streaming test from openai_live_test.go
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

Note: All live tests require the OPENAI_API_KEY environment variable to be set. Tests will be skipped if the API key is not provided.
