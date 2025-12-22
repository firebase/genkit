# Genkit Java Middleware Sample

This sample demonstrates how to use middleware in Genkit Java to implement cross-cutting concerns like logging, metrics, caching, rate limiting, and error handling.

## Prerequisites

- Java 17+
- Maven 3.6+
- OpenAI API key

## Running the Sample

### Option 1: Direct Run

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/middleware

# Run the sample
./run.sh
# Or: mvn compile exec:java
```

### Option 2: With Genkit Dev UI (Recommended)

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key-here

# Navigate to the sample directory
cd java/samples/middleware

# Run with Genkit CLI
genkit start -- ./run.sh
```

The Dev UI will be available at http://localhost:4000

## Features Demonstrated

### 1. Logging Middleware
Simple request/response logging using `CommonMiddleware.logging()`.

### 2. Custom Metrics Middleware
Custom middleware that tracks request counts and response times.

### 3. Request/Response Transformation
Using `CommonMiddleware.transformRequest()` and `CommonMiddleware.transformResponse()` to sanitize input and format output.

### 4. Validation Middleware
Using `CommonMiddleware.validate()` to validate input before processing.

### 5. Retry Middleware
Using `CommonMiddleware.retry()` for automatic retry with exponential backoff.

### 6. Caching Middleware
Using `CommonMiddleware.cache()` with `SimpleCache` for caching expensive operations.

### 7. Rate Limiting Middleware
Using `CommonMiddleware.rateLimit()` to limit request frequency.

### 8. Conditional Middleware
Using `CommonMiddleware.conditional()` to apply middleware only when a condition is met.

### 9. Before/After Hooks
Using `CommonMiddleware.beforeAfter()` for setup and cleanup operations.

### 10. Error Handling Middleware
Using `CommonMiddleware.errorHandler()` to gracefully handle errors.

## Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `/greeting` | Simple greeting with logging middleware |
| `/chat` | AI chat with multiple middleware |
| `/fact` | AI facts with caching |
| `/joke` | AI jokes with rate limiting |
| `/echo` | Echo with conditional logging |
| `/analyze` | Analysis with timing hooks |
| `/safe` | Demonstrates error handling |
| `/metrics` | View collected metrics |

## Example Requests

```bash
# Greeting flow
curl -X POST http://localhost:8080/greeting \
  -H 'Content-Type: application/json' \
  -d '"World"'

# Chat flow
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '"What is the capital of France?"'

# Fact flow (try twice to see caching)
curl -X POST http://localhost:8080/fact \
  -H 'Content-Type: application/json' \
  -d '"penguins"'

# Joke flow
curl -X POST http://localhost:8080/joke \
  -H 'Content-Type: application/json' \
  -d '"programming"'

# Echo flow (with debug logging)
curl -X POST http://localhost:8080/echo \
  -H 'Content-Type: application/json' \
  -d '"debug: test message"'

# Safe flow (test error handling)
curl -X POST http://localhost:8080/safe \
  -H 'Content-Type: application/json' \
  -d '"error"'

# View metrics
curl -X POST http://localhost:8080/metrics \
  -H 'Content-Type: application/json' \
  -d 'null'
```

## Creating Custom Middleware

You can create custom middleware by implementing the `Middleware<I, O>` interface:

```java
import com.google.genkit.core.middleware.Middleware;

// Custom middleware that adds a prefix to all requests
Middleware<String, String> prefixMiddleware = (request, context, next) -> {
    String modifiedRequest = "PREFIX: " + request;
    return next.apply(modifiedRequest, context);
};

// Use it in a flow
List<Middleware<String, String>> middleware = List.of(prefixMiddleware);
Flow<String, String, Void> myFlow = genkit.defineFlow(
    "myFlow", String.class, String.class,
    (ctx, input) -> "Result: " + input,
    middleware
);
```

## Architecture

The middleware system follows the chain of responsibility pattern:

1. Middleware are executed in order (first added, first executed)
2. Each middleware can:
   - Modify the request before passing it to the next middleware
   - Modify the response after receiving it from the next middleware
   - Short-circuit the chain by not calling `next`
   - Handle errors from downstream middleware

```
Request -> [MW1] -> [MW2] -> [MW3] -> Action
                                        |
Response <- [MW1] <- [MW2] <- [MW3] <----
```

## See Also

- [Genkit Documentation](https://github.com/firebase/genkit)
- [JavaScript Middleware Documentation](../../../js/ai/src/model/middleware.ts)
