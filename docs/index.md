{% extends "_internal/templates/intro.html" %}
{% block variables %}
  {% setvar pageTitle %}{{firebase_genkit}}{% endsetvar %}
  {% setvar custom_project %}/docs/genkit/_project.yaml{% endsetvar %}
  {% setvar supportsNode %}true{% endsetvar %}
  {% setvar supportsGolang %}true{% endsetvar %}
  {% setvar youtubeID %}M8rfDySBBvM{% endsetvar %}
{% endblock variables %}

{% block extraMeta %}
<meta name="page_type" value="Product" />
<meta name="keywords" value="docType:Product" />
{% endblock %}

{% block intro %}

Genkit is a framework designed to help you build AI-powered applications and features. It provides open source libraries for Node.js and Go, plus developer tools for testing and debugging.

This documentation covers Genkit for Node.js. If you're a Go developer, see the [Genkit Go documentation](/docs/genkit-go/get-started-go).

You can deploy and run Genkit libraries anywhere Node.js is supported. It's designed to work with any generative AI model API or vector database. While we offer integrations for Firebase and Google Cloud, you can use Genkit independently of any Google services.

[Get started](/docs/genkit/get-started){: .button}

{% endblock intro %}

{% block body %}

## Key capabilities

<table class="responsive key-functions">
<tr>
  <td><strong>Unified API for AI generation</strong></td>
  <td>Use one API to generate or stream content from various AI models. Works with multimodal input/output and custom model settings.</td>
</tr>
<tr>
  <td><strong>Structured output</strong></td>
  <td>Generate or stream structured objects (like JSON) with built-in validation. Simplify integration with your app and convert unstructured data into a usable format.</td>
</tr>
<tr>
  <td><strong>Tool calling</strong></td>
  <td>Let AI models call your functions and APIs as tools to complete tasks. The model decides when and which tools to use.</td>
</tr>
<tr>
  <td><strong>Chat</strong></td>
  <td>Genkit offers a chat-specific API that facilitates multi-turn conversations with AI models, which can be stateful and persistent.</td>
</tr>
<tr>
  <td><strong>Agents</strong></td>
  <td>Create intelligent agents that use tools (including other agents) to help automate complex tasks and workflows.</td>
</tr>
<tr>
  <td><strong>Data retrieval</strong></td>
  <td>Improve the accuracy and relevance of generated output by integrating your data. Simple APIs help you embed, index, and retrieve information from various sources.</td>
</tr>
<tr>
  <td><strong>Prompt templating</strong></td>
  <td>Create effective prompts that include rich text templating, model settings, multimodal support, and tool integration - all within a compact, runnable <a href="/docs/genkit/dotprompt">prompt file</a>.</td>
</tr>
</table>

See the following code samples for a concrete idea of how to use these capabilities in code:

- {Basic generation}

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

- {Structured output}

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

- {Function calling}

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

- {Chat}

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

- {Agents}

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
    agent that can better handle the request. If you cannot help the customer with
    the available tools, politely explain so.`
  );

  // Create a chat to enable multi-turn agent interactions
  const chat = ai.chat(triageAgent);

  chat.send('I want a reservation at Pavel\'s Cafe for noon on Tuesday.' );
  ```

- {Data retrieval}

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

- {Prompt template}

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

  You are the most welcoming AI assistant and are currently working at {% verbatim %}{{location}}{% endverbatim %}.

  Greet a guest{% verbatim %}{{#if name}}{% endverbatim %} named {% verbatim %}{{name}}{% endverbatim %}{% verbatim %}{{/if}}{% endverbatim %}{% verbatim %}{{#if style}}{% endverbatim %} in the style of {% verbatim %}{{style}}{% endverbatim %}{% verbatim %}{{/if}}{% endverbatim %}.
  ```

## Development tools

Genkit provides a command-line interface (CLI) and a local Developer UI to make building AI applications easier. These tools help you:

- **Experiment:** Test and refine your AI functions, prompts, and queries.
- **Debug:** Find and fix issues with detailed execution traces.
- **Evaluate:** Assess generated results across multiple test cases.

<div>
  <devsite-carousel data-items-per-slide="auto">
    <ul>
      <li><img src="/docs/genkit/resources/devui-run.png" width="800px" alt=""></li>
      <li><img src="/docs/genkit/resources/devui-inspect.png" width="800px" alt=""></li>
      <li><img src="/docs/genkit/resources/devui-evals.png" width="800px" alt=""></li>
    </ul>
  </devsite-carousel>
</div>

## Connect with us

- **Join the community:** Stay updated, ask questions, and share your work on our [Discord server](https://discord.gg/qXt5zzQKpc).
- **Provide feedback:** Report issues or suggest new features using our GitHub [issue tracker](https://github.com/firebase/genkit/issues).

## Next steps

Learn how to build your first AI application with Genkit in our [Get started](/docs/genkit/get-started) guide.

{% endblock %}
