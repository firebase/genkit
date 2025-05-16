# Tool (function) calling

_Tool calling_, also known as _function calling_, is a structured way to give
LLMs the ability to make requests back to the application that called it. You
define the tools you want to make available to the model, and the model will
make tool requests to your app as necessary to fulfill the prompts you give it.

The use cases of tool calling generally fall into a few themes:

**Giving an LLM access to information it wasn't trained with**

*   Frequently changing information, such as a stock price or the current
    weather.
*   Information specific to your app domain, such as product information or user
    profiles.

Note the overlap with retrieval augmented generation (RAG), which is also
a way to let an LLM integrate factual information into its generations. RAG is a
heavier solution that is most suited when you have a large amount of information
or the information that's most relevant to a prompt is ambiguous. On the other
hand, if retrieving the information the LLM needs is a simple function call or
database lookup, tool calling is more appropriate.

**Introducing a degree of determinism into an LLM workflow**

*   Performing calculations that the LLM cannot reliably complete itself.
*   Forcing an LLM to generate verbatim text under certain circumstances, such
    as when responding to a question about an app's terms of service.

**Performing an action when initiated by an LLM**

*   Turning on and off lights in an LLM-powered home assistant
*   Reserving table reservations in an LLM-powered restaurant agent

## Before you begin

If you want to run the code examples on this page, first complete the steps in
the [Getting started](../get-started.md) guide. All of the examples assume that you
have already set up a project with Genkit dependencies installed.

This page discusses one of the advanced features of Genkit model abstraction, so
before you dive too deeply, you should be familiar with the content on the
[Generating content with AI models](./models.md) page. You should also be familiar
with Genkit's system for defining input and output schemas, which is discussed
on the [Flows](./flows.md) page.

## Overview of tool calling

At a high level, this is what a typical tool-calling interaction with an LLM
looks like:

1. The calling application prompts the LLM with a request and also includes in
   the prompt a list of tools the LLM can use to generate a response.
2. The LLM either generates a complete response or generates a tool call request
   in a specific format.
3. If the caller receives a complete response, the request is fulfilled and the
   interaction ends; but if the caller receives a tool call, it performs
   whatever logic is appropriate and sends a new request to the LLM containing
   the original prompt or some variation of it as well as the result of the tool
   call.
4. The LLM handles the new prompt as in Step 2.

For this to work, several requirements must be met:

*   The model must be trained to make tool requests when it's needed to complete
    a prompt. Most of the larger models provided through web APIs, such as
    Gemini and Claude, can do this, but smaller and more specialized models
    often cannot. Genkit will throw an error if you try to provide tools to a
    model that doesn't support it.
*   The calling application must provide tool definitions to the model in the
    format it expects.
*   The calling application must prompt the model to generate tool calling
    requests in the format the application expects.

## Tool calling with Genkit

Genkit provides a single interface for tool calling with models that support it.
Each model plugin ensures that the last two of the above criteria are met, and
the Genkit instance's `generate()` function automatically carries out the tool
calling loop described earlier.

### Model support

Tool calling support depends on the model, the model API, and the Genkit plugin.
Consult the relevant documentation to determine if tool calling is likely to be
supported. In addition:

*   Genkit will throw an error if you try to provide tools to a model that
    doesn't support it.
*   If the plugin exports model references, the `info.supports.tools` property
    will indicate if it supports tool calling.

### Defining tools

Use the Genkit instance's `tool()` decorator to write tool definitions:

```py
from pydantic import BaseModel, Field
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleGenai

ai = Genkit(
    plugins=[GoogleGenai()],
    model='googleai/gemini-2.0-flash',
)

class WeatherInput(BaseModel):
    location: str = Field(description='The location to get the current weather for')


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Gets the current weather in a given location"""
    return f'The current weather in ${input.location} is 63°F and sunny.'
```

The syntax here looks just like the `flow()` syntax; however `description`
parameter is required. When writing a tool definition, take special care
with the wording and descriptiveness of these parameters. They are vital
for the LLM to make effective use of the available tools.

### Using tools

Include defined tools in your prompts to generate content.

```py
result = await ai.generate(
    prompt='What is the weather in Baltimore?',
    tools=['get_weather'],
)
```

Genkit will automatically handle the tool call if the LLM needs to use the
`get_weather` tool to answer the prompt.

### Pause the tool loop by using interrupts

By default, Genkit repeatedly calls the LLM until every tool call has been
resolved. You can conditionally pause execution in situations where you want
to, for example:

* Ask the user a question or display UI.
* Confirm a potentially risky action with the user.
* Request out-of-band approval for an action.

**Interrupts** are special tools that can halt the loop and return control
to your code so that you can handle more advanced scenarios. Visit the
[interrupts guide](./interrupts.md) to learn how to use them.

### Explicitly handling tool calls

If you want full control over this tool-calling loop, for example to
apply more complicated logic, set the `return_tool_requests` parameter to `True`.
Now it's your responsibility to ensure all of the tool requests are fulfilled:

```py
result = await ai.generate(
    prompt='What is the weather in Baltimore?',
    tools=['get_weather'],
    return_tool_requests=True,
)

tool_request_parts = llm_response.tool_requests

if len(tool_request_parts) == 0:
    print(llm_response.text)
else:
    for part in tool_request_parts:
        await handle_tool(part.name, part.input)
```
