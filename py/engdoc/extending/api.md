# API

Genkit is a framework for building AI-powered applications using generative
models. It provides a streamlined way to work with AI models, tools, prompts,
embeddings, and other AI-related functionality.

The API is structured to make it easy to:

* Define prompts that can be reused across your application.
* Create tools that AI models can call.
* Work with different AI models through a consistent interface.
* Build complex AI workflows through "flows".
* Store and retrieve data through embeddings and vector search.

## Design principles

Genkit is designed with several principles in mind:

* **Async-first**: Most communication among us and future interactive agents
  appear to be largely naturally asynchronous.
* **Type Safety**: Uses build-time and runtime-type information for strong
  typing.
* **Modularity**: Components can be mixed and matched.
* **Extensibility**: Plugin system allows adding new features.
* **Developer Experience**: Development tools like Reflection Server help debug
  applications.

## Veneer

The veneer refers to the user-facing API and exludes the internals of the
library.

### The `Genkit` Class

The `Genkit` class is the central part of the framework that:

* Manages a registry of AI-related components (models, tools, flows, etc.).
* Provides an API for working with AI models and flows.
* Handles configuration and initialization.
* Sets up development tools like the reflection server.

#### Key features

| Feature                 | Description                                                                   |
|-------------------------|-------------------------------------------------------------------------------|
| **Registry Management** | It maintains a registry to keep track of all components in a Genkit instance. |
| **Plugin System**       | Supports loading plugins to extend functionality.                             |
| **Prompt Management**   | Allows defining and using prompts both programmatically and from files.       |
| **Model Integration**   | Provides methods to work with generative AI models.                           |

#### Core Functionality

`Genkit` defines methods for the following:

| Category               | Function            | Description                                   |
|------------------------|---------------------|-----------------------------------------------|
| **Text Generation**    | `generate()`        | Generates text using AI models                |
|                        | `generate_stream()` | Streaming version for real-time results       |
| **Embedding**          | `embed()`           | Creates vector embeddings of content          |
|                        | `embed_many()`      | Batch embedding generation                    |
| **Retrieval & Search** | `retrieve()`        | Fetches documents based on queries            |
|                        | `index()`           | Indexes documents for fast retrieval          |
|                        | `rerank()`          | Re-orders retrieved documents by relevance    |
| **Tools & Functions**  | `define_tool()`     | Creates tools that models can use             |
|                        | `define_flow()`     | Creates workflows that combine multiple steps |
| **Evaluation**         | `evaluate()`        | Evaluates AI model outputs                    |

#### Helper Functions

The veneer Genkit module may also include:

* `genkit()`: A factory function to create new Genkit instances
* `shutdown()`: Handles clean shutdown of Genkit servers
* Event handlers for process termination signals

## Endpoints

### Telemetry Server

| Endpoint               | HTTP Method | Purpose                   | Request Body                               | Response                               | Content Type       |
|------------------------|-------------|---------------------------|--------------------------------------------|----------------------------------------|--------------------|
| `/api/__health`        | GET         | Health check              | -                                          | "OK" (200)                             | `text/plain`       |
| `/api/traces/:traceId` | GET         | Retrieve a specific trace | -                                          | Trace data JSON                        | `application/json` |
| `/api/traces`          | POST        | Save a new trace          | `TraceData` object                         | "OK" (200)                             | `text/plain`       |
| `/api/traces`          | GET         | List traces               | Query params: `limit`, `continuationToken` | List of traces with continuation token | `application/json` |

### Flow Server

| Endpoint                              | HTTP Method | Purpose                       | Request Body        | Response                                                                       | Content Type           |
|---------------------------------------|-------------|-------------------------------|---------------------|--------------------------------------------------------------------------------|------------------------|
| `/<pathPrefix><flowName>`             | POST        | Execute a flow                | `{ data: <input> }` | `{ result: <output> }` (200) or error (4xx/5xx)                                | `application/json`     |
| `/<pathPrefix><flowName>?stream=true` | POST        | Execute a flow with streaming | `{ data: <input> }` | `data: {"message": <chunk>}` (stream) and `data: {"result": <result>}` (final) | `text/plain` (chunked) |

### Reflection Server

TODO: Ideally, these should behave the same, but we're making a note of
differences here for now.

=== "TypeScript"

    | Endpoint                     | HTTP Method | Purpose                     | Request Body                                       | Response                             | Content Type           |
    |------------------------------|-------------|-----------------------------|----------------------------------------------------|--------------------------------------|------------------------|
    | `/api/__health`              | GET         | Health check                | -                                                  | "OK" (200)                           | `text/plain`           |
    | `/api/__quitquitquit`        | GET         | Terminate server            | -                                                  | "OK" (200) and server stops          | `text/plain`           |
    | `/api/actions`               | GET         | List registered actions     | -                                                  | Action metadata with schemas         | `application/json`     |
    | `/api/runAction`             | POST        | Run an action               | `{ key, input, context, telemetryLabels }`         | `{ result, telemetry: { traceId } }` | `application/json`     |
    | `/api/runAction?stream=true` | POST        | Run action with streaming   | `{ key, input, context, telemetryLabels }`         | Stream of chunks and final result    | `text/plain` (chunked) |
    | `/api/envs`                  | GET         | Get configured environments | -                                                  | List of environment names            | `application/json`     |
    | `/api/notify`                | POST        | Notify of telemetry server  | `{ telemetryServerUrl, reflectionApiSpecVersion }` | "OK" (200)                           | `text/plain`           |

=== "Go"

    | Endpoint         | HTTP Method | Purpose                    | Request Body                                       | Response                             | Content Type       |
    |------------------|-------------|----------------------------|----------------------------------------------------|--------------------------------------|--------------------|
    | `/api/__health`  | GET         | Health check               | -                                                  | 200 OK status                        | -                  |
    | `/api/actions`   | GET         | List registered actions    | -                                                  | Action metadata with schemas         | `application/json` |
    | `/api/runAction` | POST        | Run an action              | `{ key, input, context }`                          | `{ result, telemetry: { traceId } }` | `application/json` |
    | `/api/notify`    | POST        | Notify of telemetry server | `{ telemetryServerUrl, reflectionApiSpecVersion }` | OK response                          | `application/json` |

=== "Python"

    | Endpoint         | HTTP Method | Purpose                 | Request Body | Response                     | Content Type       |
    |------------------|-------------|-------------------------|--------------|------------------------------|--------------------|
    | `/api/__health`  | GET         | Health check            | -            | 200 OK status                | -                  |
    | `/api/actions`   | GET         | List registered actions | -            | Action metadata with schemas | `application/json` |
    | `/api/runAction` | POST        | Run an action           | Action input | Action output with traceId   | `application/json` |

## Common Patterns

* **Health check endpoints** (`/api/__health`): All servers implement a simple
  health check endpoint.
* **Action/flow execution**: All servers provide endpoints to execute
  actions/flows.
* **Streaming support**: JavaScript-based servers support streaming responses.
* **Telemetry integration**: All execution endpoints include telemetry data
  (trace IDs) in responses.
* **Error handling**: Standardized error formats with status codes and stack
  traces.
* **Content negotiation**: Different response formats based on accept headers or
  query parameters.
