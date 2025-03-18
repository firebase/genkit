# OpenAI Plugin

This plugin provides a simple interface for using OpenAI's services.

## Prerequisites

- Go installed on your system
- An OpenAI API key

## Running the Tests

1. Set your OpenAI API key as an environment variable and run the tests:

```bash
export OPENAI_API_KEY=<your-api-key>
go test .
```

2. Run the tests with the `-key` flag:

```bash
go test . -key=<your-api-key>
```
