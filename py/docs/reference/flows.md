# Defining AI workflows

The core of your app's AI features are generative model requests, but it's rare
that you can simply take user input, pass it to the model, and display the model
output back to the user. Usually, there are pre- and post-processing steps that
must accompany the model call. For example:

*   Retrieving contextual information to send with the model call
*   Retrieving the history of the user's current session, for example in a chat
    app
*   Using one model to reformat the user input in a way that's suitable to pass
    to another model
*   Evaluating the "safety" of a model's output before presenting it to the user
*   Combining the output of several models

Every step of this workflow must work together for any AI-related task to
succeed.

In Genkit, you represent this tightly-linked logic using a construction called a
flow. Flows are written just like functions, using ordinary Python code, but
they add additional capabilities intended to ease the development of AI
features:

*   **Type safety**: Input and output schemas defined using
    [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/), which
    provides both static and runtime type checking
*   **Streaming**: Flows support streaming of data, such as parital LLM responses,
    or any custom serializable objects.
*   **Integration with developer UI**: Debug flows independently of your
    application code using the developer UI. In the developer UI, you can run
    flows and view traces for each step of the flow.
*   **Simplified deployment**: Deploy flows directly as web API endpoints, using
    Cloud Run or any platform that can host a web app.

Unlike similar features in other frameworks, Genkit's flows are lightweight and
unobtrusive, and don't force your app to conform to any specific abstraction.
All of the flow's logic is written in standard Python, and code inside a
flow doesn't need to be flow-aware.

## Defining and calling flows

In its simplest form, a flow just wraps a function. The following example wraps
a function that calls `generate()`:

```py
@ai.flow()
async def menu_suggestion_flow(theme: str):
    response = await ai.generate(
      prompt=f'Invent a menu item for a {theme} themed restaurant.',
    )
    return response.text
```

Just by wrapping your `generate()` calls like this, you add some functionality:
doing so lets you run the flow from the Genkit CLI and from the developer UI,
and is a requirement for several of Genkit's features, including deployment and
observability (later sections discuss these topics).

### Input and output schemas

One of the most important advantages Genkit flows have over directly calling a
model API is type safety of both inputs and outputs. When defining flows, you
can define schemas for them using Pydantic.

Here's a refinement of the last example, which defines a flow that takes a
string as input and outputs an object:

```py
from pydantic import BaseModel

class MenuItemSchema(BaseModel):
    dishname: str
    description: str

@ai.flow()
async def menu_suggestion_flow(theme: str) -> MenuItemSchema:
    response = await ai.generate(
      prompt=f'Invent a menu item for a {theme} themed restaurant.',
      output_schema=MenuItemSchema,
    )
    return response.output
```

Note that the schema of a flow does not necessarily have to line up with the
schema of the `generate()` calls within the flow (in fact, a flow might not even
contain `generate()` calls). Here's a variation of the example that passes a
schema to `generate()`, but uses the structured output to format a simple
string, which the flow returns.

```py
@ai.flow()
async def menu_suggestion_flow(theme: str) => MenuItemSchema:
    response = await ai.generate(
      prompt=f'Invent a menu item for a {theme} themed restaurant.',
      output_schema=MenuItemSchema,
    )
    output: MenuItemSchema = response.output
    return f'**{output.dishname}**: {output.description}'
```

### Calling flows

Once you've defined a flow, you can call it from your Python code as a regular function. The argument to the flow must conform to the input schema, if you defined one.

```py
response = await menu_suggestion_flow('bistory')
```

If you defined an output schema, the flow response will conform to it. For
example, if you set the output schema to `MenuItemSchema`, the flow output will
contain its properties.

## Streaming flows

Flows support streaming using an interface similar to `generate_stream()`'s streaming
interface. Streaming is useful when your flow generates a large amount of
output, because you can present the output to the user as it's being generated,
which improves the perceived responsiveness of your app. As a familiar example,
chat-based LLM interfaces often stream their responses to the user as they are
generated.

Here's an example of a flow that supports streaming:

```py
@ai.flow()
async def menu_suggestion_flow(theme: str, ctx):
    stream, response = ai.generate_stream(
      prompt=f'Invent a menu item for a {theme} themed restaurant.',
    )

    async for chunk in stream:
        ctx.send_chunk(chunk.text)

    return {
      'theme': theme,
      'menu_item': (await response).text,
    }

```

The second parameter to your flow definition is called "side channel". It
provides features such as request context and the `send_chunk` callback.
The `send_chunk` callback takes a single parameter. Whenever data becomes
available within your flow, send the data to the output stream by calling
this function.

In the above example, the values streamed by the flow are directly coupled to
the values streamed by the `generate_stream()` call inside the flow. Although this is
often the case, it doesn't have to be: you can output values to the stream using
the callback as often as is useful for your flow.

### Calling streaming flows

Streaming flows are also callable, but they immediately return a response object
rather than a promise. Flow's `stream` method returns the stream async iterable,
which you can iterate over the streaming output of the flow as it's generated.


```py
stream, response = menu_suggestion_flow.stream('bistro')
async for chunk in stream:
    print(chunk)
```

You can also get the complete output of the flow, as you can with a
non-streaming flow. The final response is a future that you can `await` on.

```py
print(await response)
```

Note that the streaming output of a flow might not be the same type as the
complete output.

## Debugging flows

One of the advantages of encapsulating AI logic within a flow is that you can
test and debug the flow independently from your app using the Genkit developer
UI.

To start the developer UI, run the following commands from your project
directory:

```posix-terminal
genkit start -- python app.py
```

Update `python app.py` to match the way you normally run your app.

From the **Run** tab of developer UI, you can run any of the flows defined in
your project:

After you've run a flow, you can inspect a trace of the flow invocation by
either clicking **View trace** or looking on the **Inspect** tab.

In the trace viewer, you can see details about the execution of the entire flow,
as well as details for each of the individual steps within the flow.

## Deploying flows

You can deploy your flows directly as web API endpoints, ready for you to call
from your app clients. Deployment is discussed in detail on several other pages,
but this section gives brief overviews of your deployment options.

For information on deploying to specific platforms, see
[Deploy with Cloud Run](../cloud-run.md) and
[Build a Flask app](../flask.md) and
