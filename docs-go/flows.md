# Flows

Flows are functions with some additional characteristics: they are strongly
typed, streamable, locally and remotely callable, and fully observable.
Firebase Genkit provides CLI and developer UI tooling for working with flows
(running, debugging).

## Defining flows

A flow wraps a function:

- {Go}

  ```go
  menuSuggestionFlow := genkit.DefineFlow(
    "menuSuggestionFlow",
    func(ctx context.Context, restaurantTheme string, _ genkit.NoStream) (string, error) {
      suggestion := makeMenuItemSuggestion(restaurantTheme)
      return suggestion, nil
    },
  )
  ```

You can define input and output schemas for a flow, which is useful when you
want type-safe structured output.

- {Go}

  Genkit converts Go types into JSON Schema using
  [`invopop/jsonschema`](https://pkg.go.dev/github.com/invopop/jsonschema):

  ```go
  type MenuSuggestion struct {
    ItemName    string `json:"item_name"`
    Description string `json:"description"`
    Calories    int    `json:"calories"`
  }
  ```

  ```go
  menuSuggestionFlow := genkit.DefineFlow(
    "menuSuggestionFlow",
    func(ctx context.Context, restaurantTheme string, _ genkit.NoStream) (MenuSuggestion, error) {
      suggestion := makeStructuredMenuItemSuggestion(restaurantTheme)
      return suggestion, nil
    },
  )
  ```

## Running flows

- {Go}

  ```go
  suggestion, err := genkit.RunFlow(context.Background(), menuSuggestionFlow, "French")
  ```

You can use the CLI to run flows as well:

```posix-terminal
genkit flow:run menuSuggestionFlow '"French"'
```

### Streamed

Here's a simple example of a flow that can stream values:

- {Go}

  ```go
  // Types for illustrative purposes.
  type inputType string
  type outputType string
  type streamType string

  menuSuggestionFlow := genkit.DefineFlow(
    "menuSuggestionFlow",
    func(
      ctx context.Context,
      restaurantTheme inputType,
      callback func(context.Context, streamType) error,
    ) (outputType, error) {
      var menu outputType = ""
      menuChunks := make(chan streamType)
      go makeFullMenuSuggestion(restaurantTheme, menuChunks)
      for {
        chunk, more := <-menuChunks
        if !more {
          break
        }
        if callback != nil {
          callback(context.Background(), chunk)
        }
        menu += outputType(chunk)
      }
      return menu, nil
    },
  )
  ```

Note that the streaming callback can be undefined. It's only defined if the
invoking client is requesting streamed response.

To invoke a flow in streaming mode:

- {Go}

  ```go
  genkit.StreamFlow(
    context.Background(),
    menuSuggestionFlow,
    "French",
  )(func(sfv *genkit.StreamFlowValue[outputType, streamType], err error) bool {
    if !sfv.Done {
      fmt.Print(sfv.Output)
      return true
    } else {
      return false
    }
  })
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

- {Go}

  To deploy flows using Cloud Run and similar services, define your flows, and
  then call `StartFlowServer()`:

  ```go
  func main() {
    genkit.DefineFlow(
      "menuSuggestionFlow",
      func(ctx context.Context, restaurantTheme string, _ genkit.NoStream) (string, error) {
        // ...
      },
    )
    genkit.StartFlowServer(":1234")
  }
  ```

  `StartFlowsServer` starts a `net/http` server that exposes each of the flows
  you defined as HTTP endpoints
  (for example, `http://localhost:3400/menuSuggestionFlow`).
  You can optionally specify the address and port to listen on. If you don't,
  the server listens on any address and the port specified by the PORT
  environment variable; if that is empty, it uses the default of port 3400.

  If you want to serve flows on the same host and port as other endpoints, you
  can call `NewFlowServeMux()` to get a handler for your Genkit flows, which you
  can multiplex with your other route handlers:

  ```go
  mainMux := http.NewServeMux()
  mainMux.Handle("POST /flow/", http.StripPrefix("/flow/", genkit.NewFlowServeMux()))
  ```

## Flow observability

Sometimes when using 3rd party SDKs that are not instrumented for observability,
you might want to see them as a separate trace step in the Developer UI. All you
need to do is wrap the code in the `run` function.

```go
genkit.DefineFlow(
  "menuSuggestionFlow",
  func(ctx context.Context, restaurantTheme string, _ genkit.NoStream) (string, error) {
    themes, err := genkit.Run(ctx, "find-similar-themes", func() (string, error) {
      // ...
    })

    // ...
  },
)
```
