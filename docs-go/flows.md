# Flows

Flows are wrapped functions with some additional characteristics over direct
calls: they are strongly typed, streamable, locally and remotely callable, and
fully observable.
Genkit provides CLI and developer UI tooling for running and debugging flows.

## Defining flows

In its simplest form, a flow just wraps a function:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="flow1" adjust_indentation="auto" %}
```

Doing so lets you run the function from the Genkit CLI and developer UI, and is
a requirement for many of Genkit's features, including deployment and
observability.

An important advantage Genkit flows have over directly calling a model API is
type safety of both inputs and outputs.
The argument and result types of a flow can be simple or structured values.
Genkit will produce JSON schemas for these values using
[`invopop/jsonschema`](https://pkg.go.dev/github.com/invopop/jsonschema).

The following flow takes a `string` as input and outputs a `struct`:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="msug" adjust_indentation="auto" %}
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="flow2" adjust_indentation="auto" %}
```

## Running flows

To run a flow in your code:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="run1" adjust_indentation="auto" %}
```

You can use the CLI to run flows as well:

```posix-terminal
genkit flow:run menuSuggestionFlow '"French"'
```

### Streamed

Here's a simple example of a flow that can stream values:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="streaming-types" adjust_indentation="auto" %}
```

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="streaming" adjust_indentation="auto" %}
```

Note that the streaming callback can be undefined. It's only defined if the
invoking client is requesting streamed response.

To invoke a flow in streaming mode:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="invoke-streaming" adjust_indentation="auto" %}
```

If the flow doesn't implement streaming, `StreamFlow()` behaves identically to
`RunFlow()`.

You can use the CLI to stream flows as well:

```posix-terminal
genkit flow:run menuSuggestionFlow '"French"' -s
```

## Deploying flows

If you want to be able to access your flow over HTTP you will need to deploy it
first.
To deploy flows using Cloud Run and similar services, define your flows, and
then call `Init()`:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="main" adjust_indentation="auto" %}
```

`Init` starts a `net/http` server that exposes your flows as HTTP
endpoints (for example, `http://localhost:3400/menuSuggestionFlow`).

The second parameter is an optional `Options` that specifies the following:

- `FlowAddr`: Address and port to listen on. If not specified,
  the server listens on the port specified by the PORT environment variable;
  if that is empty, it uses the default of port 3400.
- `Flows`: Which flows to serve. If not specified, `Init` serves all of
  your defined flows.

If you want to serve flows on the same host and port as other endpoints, you
can set `FlowAddr` to `-` and instead call `NewFlowServeMux()` to get a handler
for your Genkit flows, which you can multiplex with your other route handlers:

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="mux" adjust_indentation="auto" %}
```

## Flow observability

Sometimes when using 3rd party SDKs that are not instrumented for observability,
you might want to see them as a separate trace step in the Developer UI. All you
need to do is wrap the code in the `run` function.

```golang
{% includecode github_path="firebase/genkit/go/internal/doc-snippets/flows.go" region_tag="run" adjust_indentation="auto" %}
```
