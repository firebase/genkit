# Testing

## Unit tests

```bash
just test             # Run all pytest tests
just test -- -k cache # Run only cache tests
```

## REST integration tests

With the server running:

```bash
./test_endpoints.sh
# Or: just test-endpoints
```

Test against a deployed instance:

```bash
BASE_URL=https://my-app.run.app ./test_endpoints.sh
```

### Example curl commands

=== "Joke (non-streaming)"

    ```bash
    curl -X POST http://localhost:8080/tell-joke \
      -H "Content-Type: application/json" \
      -d '{"name": "Banana"}'
    ```

=== "Joke (SSE streaming)"

    ```bash
    curl -N -X POST http://localhost:8080/tell-joke/stream \
      -H "Content-Type: application/json" \
      -d '{"name": "Python"}'
    ```

    !!! tip
        The `-N` flag disables curl's output buffering. Without it, curl
        buffers the entire response and dumps it all at once.

=== "Translation"

    ```bash
    curl -X POST http://localhost:8080/translate \
      -H "Content-Type: application/json" \
      -d '{"text": "Hello, how are you?", "target_language": "Japanese"}'
    ```

=== "Image description"

    ```bash
    curl -X POST http://localhost:8080/describe-image \
      -H "Content-Type: application/json" \
      -d '{"image_url": "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"}'
    ```

=== "Character generation"

    ```bash
    curl -X POST http://localhost:8080/generate-character \
      -H "Content-Type: application/json" \
      -d '{"name": "Luna"}'
    ```

=== "Pirate chat"

    ```bash
    curl -X POST http://localhost:8080/chat \
      -H "Content-Type: application/json" \
      -d '{"question": "What is the best programming language?"}'
    ```

=== "Code generation"

    ```bash
    curl -X POST http://localhost:8080/generate-code \
      -H "Content-Type: application/json" \
      -d '{"description": "a function that reverses a linked list", "language": "python"}'
    ```

=== "Code review"

    ```bash
    curl -X POST http://localhost:8080/review-code \
      -H "Content-Type: application/json" \
      -d '{"code": "def add(a, b):\n    return a + b", "language": "python"}'
    ```

=== "Health check"

    ```bash
    curl http://localhost:8080/health
    ```

## gRPC integration tests

Install `grpcurl` and `grpcui`:

```bash
# macOS
brew install grpcurl grpcui

# Linux (via Go)
go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest
go install github.com/fullstorydev/grpcui/cmd/grpcui@latest
```

Interactive web UI (like Swagger for gRPC):

```bash
just grpcui
```

CLI testing with `grpcurl`:

```bash
# List services
grpcurl -plaintext localhost:50051 list

# Describe the service
grpcurl -plaintext localhost:50051 describe genkit.sample.v1.GenkitService

# Call a unary RPC
grpcurl -plaintext -d '{"name": "Waffles"}' \
  localhost:50051 genkit.sample.v1.GenkitService/TellJoke

# Server-streaming RPC
grpcurl -plaintext -d '{"topic": "a robot learning to paint"}' \
  localhost:50051 genkit.sample.v1.GenkitService/TellStory
```

Run all gRPC tests (automated):

```bash
./test_grpc_endpoints.sh
# Or: just test-grpc-endpoints
```

## Run everything

```bash
just test-all    # REST + gRPC integration tests
```

## Lint and type check

```bash
just lint        # ruff + ty + pyrefly + pyright + shellcheck
just fmt         # Auto-format with ruff
just typecheck   # Type checkers only
```

## Security checks

```bash
just audit       # Scan for known CVEs
just licenses    # Verify license compliance
just security    # Both of the above
```
