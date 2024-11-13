# Tool calling

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

Note the overlap with [retrieval augmented generation](rag) (RAG), which is also
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

## Before you begin {:#you-begin}

If you want to run the code examples on this page, first complete the steps in
the [Getting started](get-started) guide. All of the examples assume that you
have already set up a project with Genkit dependencies installed.

This page discusses one of the advanced features of Genkit model abstraction, so
before you dive too deeply, you should be familiar with the content on the
[Generating content with AI models](models) page. You should also be familiar
with Genkit's system for defining input and output schemas, which is discussed
on the [Flows](flows) page.

## Overview of tool calling {:#overview-tool}

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

## Tool calling with Genkit {:#tool-calling}

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

Use the Genkit instance's `defineTool()` function to write tool definitions:

```ts
import { genkit, z } from 'genkit';
import { googleAI, gemini15Flash } from '@genkit-ai/google-ai';

const ai = genkit({
  plugins: [googleAI()],
  model: gemini15Flash,
});

const getWeather = ai.defineTool(
  {
    name: 'getWeather',
    description: 'Gets the current weather in a given location',
    inputSchema: z.object({ 
      location: z.string().describe('The location to get the current weather for')
    }),
    outputSchema: z.string(),
  },
  async (input) => {
    // Here, we would typically make an API call or database query. For this
    // example, we just return a fixed value.
    return 'The current weather in ${input.location} is 63°F and sunny.';
  }
);
```

The syntax here looks just like the `defineFlow()` syntax; however, all four of
the `name`, `description`, `inputSchema`, and `outputSchema` parameters are
required. When writing a tool definition, take special care with the wording and
descriptiveness of these parameters, as they are vital for the LLM to
effectively make use of the available tools.

### Using tools

Include defined tools in your prompts to generate content.

*   {Generate}

    ```ts
    const response = await ai.generate({
      prompt: 'What is the weather in Baltimore?',
      tools: [getWeather],
    });
    ```

*   {definePrompt}

    ```ts
    const weatherPrompt = ai.definePrompt(
      {
        name: 'weatherPrompt',
        tools: [getWeather],
      },
      'What is the weather in {{location}}?'
    );

    const response = await weatherPrompt({ location: 'Baltimore' });
    ```

*   {Prompt file}

    ```none
    ---
    system: "Answer questions using the tools you have."
    tools: [getWeather]
    input:
      schema:
        location: string
    ---

    What is the weather in {{location}}?
    ```

    Then you can execute the prompt in your code as follows:

    ```ts
    // assuming prompt file is named weatherPrompt.prompt
    const weatherPrompt = ai.prompt('weatherPrompt');

    const response = await weatherPrompt({ location: 'Baltimore' });
    ```

*   {Chat}

    ```ts
    const chat = ai.chat({
      system: 'Answer questions using the tools you have.',
      tools: [getWeather],
    });

    const response = await chat.send('What is the weather in Baltimore?');

    // Or, specify tools that are message-specific 
    const response = await chat.send({
      prompt: 'What is the weather in Baltimore?',
      tools: [getWeather],
    });
    ```

Genkit will automatically handle the tool call if the LLM needs to use the
`getWeather` tool to answer the prompt.

### Explicitly handling tool calls

By default, Genkit repeatedly calls the LLM until every tool call has been
resolved. If you want more control over this tool calling loop, for example to
apply more complicated logic, set the `returnToolRequests` parameter to `true`.
Now it's your responsibility to ensure all of the tool requests are fulfilled:

```ts
const getWeather = ai.defineTool(
  {
    // ... tool definition ...
  },
  async ({ location }) => {
    // ... tool implementation ...
  },
);

const generateOptions: GenerateOptions = {
  prompt: "What's the weather like in Baltimore?",
  tools: [getWeather],
  returnToolRequests: true,
};

let llmResponse;
while (true) {
  llmResponse = await ai.generate(generateOptions);
  const toolRequests = llmResponse.toolRequests;
  if (toolRequests.length < 1) {
    break;
  }
  const toolResponses: ToolResponsePart[] = await Promise.all(
    toolRequests.map(async (part) => {
      switch (part.toolRequest.name) {
        case 'specialTool':
          return {
            toolResponse: {
              name: part.toolRequest.name,
              ref: part.toolRequest.ref,
              output: await getWeather(part.toolRequest.input),
            },
          };
        default:
          throw Error('Tool not found');
      }
    })
  );
  generateOptions.messages = llmResponse.messages;
  generateOptions.prompt = toolResponses;
}
```
