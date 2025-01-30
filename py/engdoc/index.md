# Genkit

!!! note

    If you're a user of Firebase Genkit and landed here,
    this is engineering documentation that someone contributing
    to Genkit would use, not necessarily only use it.

    For more information about how to get started with using
    Firebase Genkit, please see: [User Guide](.)

## What is Genkit?

Genkit is a framework designed to help you build AI-powered applications and
features. It provides open source libraries and plus developer
tools for testing and debugging. The following language runtimes are supported:

| Language Runtime | Version | Support Tier |
|------------------|---------|--------------|
| Node.js          | 22.0+   | 1            |
| Go               | 1.22+   | 1            |
| Python           | 3.12+   | 1            |

It is designed to work with any generative AI model API or vector database.
While we offer integrations for Firebase and Google Cloud, you can use Genkit
independently of any Google services.

The framework provides an abstraction of components by wrapping them with
building blocks called actions, each of which is maintained in a registry. An
action can expose a component over HTTP as a cloud function or server endpoint
and is inspectable and discoverable via a reflection API. Flows are actions
defined by the user and plugins can be created by third parties to extend the
set of available actions.

## Key capabilities

| Feature                           | Description                                                                                                                                                                                  |
|-----------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Unified API for AI generation** | Use one API to generate or stream content from various AI models. Works with multimodal input/output and custom model settings.                                                              |
| **Structured output**             | Generate or stream structured objects (like JSON) with built-in validation. Simplify integration with your app and convert unstructured data into a usable format.                           |
| **Tool calling**                  | Let AI models call your functions and APIs as tools to complete tasks. The model decides when and which tools to use.                                                                        |
| **Chat**                          | Genkit offers a chat-specific API that facilitates multi-turn conversations with AI models, which can be stateful and persistent.                                                            |
| **Agents**                        | Create intelligent agents that use tools (including other agents) to help automate complex tasks and workflows.                                                                              |
| **Data retrieval**                | Improve the accuracy and relevance of generated output by integrating your data. Simple APIs help you embed, index, and retrieve information from various sources.                           |
| **Prompt templating**             | Create effective prompts that include rich text templating, model settings, multimodal support, and tool integration - all within a compact, runnable [prompt file](/docs/genkit/dotprompt). |

See the following code samples for a concrete idea of how to use these
capabilities in code:

### Feature Parity

| Feature           | Python | JavaScript | Go |
|-------------------|--------|------------|----|
| Agents            | ❌     | ✅         | ✅ |
| Chat              | ❌     | ✅         | ✅ |
| Data retrieval    | ❌     | ✅         | ✅ |
| Generation        | ❌     | ✅         | ✅ |
| Prompt templating | ❌     | ✅         | ✅ |
| Structured output | ❌     | ✅         | ✅ |
| Tool calling      | ❌     | ✅         | ✅ |

### Plugin Parity

| Plugins      | Python | JavaScript | Go |
|--------------|--------|------------|----|
| Chroma DB    | ❌     | ✅         | ✅ |
| Dotprompt    | ❌     | ✅         | ✅ |
| Firebase     | ❌     | ✅         | ✅ |
| Google AI    | ❌     | ✅         | ✅ |
| Google Cloud | ❌     | ✅         | ✅ |
| Ollama       | ❌     | ✅         | ✅ |
| Pinecone     | ❌     | ✅         | ✅ |
| Vertex AI    | ❌     | ✅         | ✅ |


## Examples

### Basic generation

=== "Python"

    ```python hl_lines="12 13 14 15 17 20 21 22" linenums="1"
    import asyncio
    import structlog

    from genkit.veneer import genkit
    from genkit.plugins.google_ai import googleAI
    from genkit.plugins.google_ai.models import gemini15Flash

    logger = structlog.get_logger()


    async def main() -> None:
        ai = genkit({        # (1)!
          plugins: [googleAI()],
          model: gemini15Flash,
        })

        response = await ai.generate('Why is AI awesome?')
        await logger.adebug(response.text)

        stream = await ai.generate_stream("Tell me a story")
        async for chunk in stream:
            await logger.adebug("Received chunk", text=chunk.text)
        await logger.adebug("Finished generating text stream")


    if __name__ == '__main__':
        asyncio.run(content_generation())
    ```

    1. :man_raising_hand: Basic example of annotation.

=== "JavaScript"

    ```javascript
    import { genkit } from 'genkit';
    import { googleAI, gemini15Flash } from '@genkit-ai/googleai';

    const ai = genkit({
      plugins: [googleAI()],
      model: gemini15Flash,  // Set default model
    });

    // Simple generation
    const { text } = await ai.generate('Why is AI awesome?');
    console.log(text);

    // Streamed generation
    const { stream } = await ai.generateStream('Tell me a story');
    for await (const chunk of stream) {
      console.log(chunk.text);
    }
    ```

=== "Go"

    ```go
    import "fmt"

    func main() {
      fmt.Println("Hello")
    }
    ```


### Structured output

=== "Python"

    ```python
    import asyncio
    import logging
    import structlog

    from genkit.veneer import genkit
    from genkit.plugins.google_ai import googleAI
    from genkit.plugins.google_ai.models import gemini15Flash

    logger = structlog.get_logger()

    from pydantic import BaseModel, Field, validator
    from enum import Enum

    class Role(str, Enum):
        KNIGHT = "knight"
        MAGE = "mage"
        ARCHER = "archer"

    class CharacterProfile(BaseModel):
        name: str
        role: Role
        backstory: str

    async def main() -> None:
        ai = genkit({
          plugins: [googleAI()],
          model: gemini15Flash,
        })

        await logger.adebug("Generating structured output", prompt="Create a brief profile for a character in a fantasy video game.")
        response = await ai.generate(
            prompt="Create a brief profile for a character in a fantasy video game.",
            output={
                "format": "json",
                "schema": CharacterProfile,
            },
        )
        await logger.ainfo("Generated output", output=response.output)


    if __name__ == "__main__":
        asyncio.run(main())
    ```

=== "JavaScript"

    ```javascript
    import { genkit, z } from 'genkit';
    import { googleAI, gemini15Flash } from '@genkit-ai/googleai';

    const ai = genkit({
      plugins: [googleAI()],
      model: gemini15Flash,
    });

    const { output } = await ai.generate({
      prompt: 'Create a brief profile for a character in a fantasy video game.',
      // Specify output structure using Zod schema
      output: {
        format: 'json',
        schema: z.object({
          name: z.string(),
          role: z.enum(['knight', 'mage', 'archer']),
          backstory: z.string(),
        }),
      },

    });

    console.log(output);
    ```

### Function calling

=== "Python"

    ```python
    import asyncio
    import logging
    import structlog

    from genkit.veneer import genkit
    from genkit.plugins.google_ai import googleAI
    from genkit.plugins.google_ai.models import gemini15Flash
    from pydantic import BaseModel, Field

    logger = structlog.get_logger()


    class GetWeatherInput(BaseModel):
        location: str = Field(description="The location to get the current weather for")


    class GetWeatherOutput(BaseModel):
        weather: str


    async def get_weather(input: GetWeatherInput) -> GetWeatherOutput:
        await logger.adebug("Calling get_weather tool", location=input.location)
        # Replace this with an actual API call to a weather service
        weather_info = f"The current weather in {input.location} is 63°F and sunny."
        return GetWeatherOutput(weather=weather_info)


    async def main() -> None:
        ai = genkit({
          plugins: [googleAI()],
          model: gemini15Flash,
        })

        get_weather_tool = ai.define_tool(
            name="getWeather",
            description="Gets the current weather in a given location",
            input_schema=GetWeatherInput,
            output_schema=GetWeatherOutput,
            func=get_weather,
        )

        await logger.adebug("Generating text with tool", prompt="What is the weather like in New York?")
        response = await ai.generate(
            prompt="What is the weather like in New York?",
            tools=[get_weather_tool],
        )
        await logger.ainfo("Generated text", text=response.text)


    if __name__ == "__main__":
        asyncio.run(main())
    ```

=== "JavaScript"

    ```javascript
    import { genkit, z } from 'genkit';
    import { googleAI, gemini15Flash } from '@genkit-ai/googleai';

    const ai = genkit({
      plugins: [googleAI()],
      model: gemini15Flash,
    });

    // Define tool to get current weather for a given location
    const getWeather = ai.defineTool(
      {
        name: "getWeather",
        description: "Gets the current weather in a given location",
        inputSchema: z.object({
          location: z.string().describe('The location to get the current weather for')
        }),
        outputSchema: z.string(),
      },
      async (input) => {
        // Here, we would typically make an API call or database query. For this
        // example, we just return a fixed value.
        return `The current weather in ${input.location} is 63°F and sunny.`;
      }
    );

    const { text } = await ai.generate({
        tools: [getWeather], // Give the model a list of tools it can call
        prompt: 'What is the weather like in New York? ',
    });

    console.log(text);
    ```

### Chat

=== "Python"

    ```python
    import asyncio
    import logging
    import structlog

    from genkit.veneer import genkit
    from genkit.plugins.google_ai import googleAI
    from genkit.plugins.google_ai.models import gemini15Flash
    from pydantic import BaseModel, Field

    logger = structlog.get_logger()


    class ChatResponse(BaseModel):
        text: str


    async def chat(input: str) -> ChatResponse:
        await logger.adebug("Calling chat tool", input=input)
        # Replace this with an actual API call to a language model,
        # providing the user query and the conversation history.
        response_text = "Ahoy there! Your name is Pavel, you scurvy dog!"
        return ChatResponse(text=response_text)


    async def main() -> None:
        ai = genkit({
          plugins: [googleAI()],
          model: gemini15Flash,
        })

        chat_tool = ai.chat({system: 'Talk like a pirate'})

        await logger.adebug("Calling chat tool", input="Hi, my name is Pavel")
        response = await chat_tool.send("Hi, my name is Pavel")

        await logger.adebug("Calling chat tool", input="What is my name?")
        response = await chat_tool.send("What is my name?")

        await logger.ainfo("Chat response", text=response.text)


    if __name__ == "__main__":
        asyncio.run(main())
    ```

=== "JavaScript"

    ```javascript
    import { genkit, z } from 'genkit';
    import { googleAI, gemini15Flash } from '@genkit-ai/googleai';

    const ai = genkit({
      plugins: [googleAI()],
      model: gemini15Flash,
    });

    const chat = ai.chat({ system: 'Talk like a pirate' });

    let response = await chat.send('Hi, my name is Pavel');

    response = await chat.send('What is my name?');
    console.log(response.text);
    // Ahoy there! Your name is Pavel, you scurvy dog
    ```
### Agents

=== "Python"

    ```python

    ```

=== "JavaScript"

    ```javascript
    import { genkit, z } from 'genkit';
    import { googleAI, gemini15Flash } from '@genkit-ai/googleai';

    const ai = genkit({
      plugins: [googleAI()],
      model: gemini15Flash,
    });

    // Define prompts that represent specialist agents
    const reservationAgent = ai.definePrompt(
      {
        name: 'reservationAgent',
        description: 'Reservation Agent can help manage guest reservations',
        tools: [reservationTool, reservationCancelationTool, reservationListTool],

      },
      `{% verbatim %}{{role "system"}}{% endverbatim %} Help guests make and manage reservations`
    );

    const menuInfoAgent = ...
    const complaintAgent = ...

    // Define a triage agent that routes to the proper specialist agent
    const triageAgent = ai.definePrompt(
      {
        name: 'triageAgent',
        description: 'Triage Agent',
        tools: [reservationAgent, menuInfoAgent, complaintAgent],
      },
      `{% verbatim %}{{role "system"}}{% endverbatim %} You are an AI customer service agent for Pavel's Cafe.
      Greet the user and ask them how you can help. If appropriate, transfer to an
      agent that can better handle the request. If you cannot help the customer
      with the available tools, politely explain so.`
    );

    // Create a chat to enable multi-turn agent interactions
    const chat = ai.chat(triageAgent);

    chat.send('I want a reservation at Pavel\'s Cafe for noon on Tuesday.' );
    ```

### Data retrieval

=== "Python"

    ```python
    import asyncio
    import logging
    import structlog

    from genkit.veneer import genkit
    from genkit.plugins.google_ai import googleAI
    from genkit.plugins.google_ai.models import gemini15Flash, textEmbedding004
    from genkit.plugins.dev_local_vectorstore import devLocalVectorstore, devLocalRetrieverRef

    logger = structlog.get_logger()


    async def main() -> None:
        ai = genkit(
            plugins=[
                googleAI(),
                devLocalVectorstore(
                    [
                        {
                            "index_name": "BobFacts",
                            "embedder": textEmbedding004,
                        }
                    ]
                ),
            ],
            model=gemini15Flash,
        )

        retriever = devLocalRetrieverRef("BobFacts")

        query = "How old is Bob?"

        await logger.adebug("Retrieving documents", query=query)
        docs = await ai.retrieve(retriever=retriever, query=query)

        await logger.adebug("Generating answer", query=query)
        response = await ai.generate(
            prompt=f"Use the provided context from the BobFacts database to answer this query: {query}",
            docs=docs,
        )

        await logger.ainfo("Generated answer", answer=response.text)

    if __name__ == "__main__":
        asyncio.run(main())
    ```

=== "JavaScript"

    ```javascript
    import { genkit } from 'genkit';
    import { googleAI, gemini15Flash, textEmbedding004 } from '@genkit-ai/googleai';
    import { devLocalRetrieverRef } from '@genkit-ai/dev-local-vectorstore';

    const ai = genkit({
      plugins: [
        googleAI()
        devLocalVectorstore([
          {
            indexName: 'BobFacts',
            embedder: textEmbedding004,
          },
        ]),
      ],
      model: gemini15Flash,
    });

    // Reference to a local vector database storing Genkit documentation
    const retriever = devLocalRetrieverRef('BobFacts');

    // Consistent API to retrieve most relevant documents based on semantic similarity to query
    const docs = await ai.retrieve(
      retriever: retriever,
      query: 'How old is bob?',
    );

    const result = await ai.generate({
        prompt: `Use the provided context from the Genkit documentation to answer this query: ${query}`,
        docs // Pass retrieved documents to the model
    });
    ```

### Prompt template

=== "YAML"

    ```yaml
    ---
    model: vertexai/gemini-1.5-flash
    config:
      temperature: 0.9
    input:
      schema:
        properties:
          location: {type: string}
          style: {type: string}
          name: {type: string}
        required: [location]
      default:
        location: a restaurant
    ---

    You are the most welcoming AI assistant and are currently working at {%
    verbatim %}{{location}}{% endverbatim %}.

    Greet a guest{% verbatim %}{{#if name}}{% endverbatim %} named {% verbatim %}{{name}}{% endverbatim %}{% verbatim %}{{/if}}{% endverbatim %}{% verbatim %}{{#if style}}{% endverbatim %} in the style of {% verbatim %}{{style}}{% endverbatim %}{% verbatim %}{{/if}}{% endverbatim %}.
    ```

## Development tools

Genkit provides a command-line interface (CLI) and a local Developer UI to make
building AI applications easier. These tools help you:

* **Experiment:** Test and refine your AI functions, prompts, and queries.
* **Debug:** Find and fix issues with detailed execution traces.
* **Evaluate:** Assess generated results across multiple test cases.

## Connect with us

* **Join the community:** Stay updated, ask questions,
  and share your work on our [Discord server](https://discord.gg/qXt5zzQKpc).
* **Provide feedback:** Report issues or suggest new features
  using our GitHub [issue tracker](https://github.com/firebase/genkit/issues).

## Next steps

Learn how to build your first AI application with Genkit in our [Get
started](/docs/get_started.md) guide.
