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
  <td><strong>Structured generation</strong></td>
  <td>Generate or stream structured objects (like JSON) with built-in validation. Simplify integration with your app and convert unstructured data into a usable format.</td>
</tr>
<tr>
  <td><strong>Tool calling</strong></td>
  <td>Let AI models call your functions and APIs as tools to complete tasks. The model decides when and which tools to use.</td>
</tr>
<tr>
  <td><strong>Retrieval-augmented generation</strong></td>
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
  import { generate } from `@genkit/ai`;
  import { gemini15Flash, claude3Sonnet, llama31 } from '@genkit/vertexai';
  import { gpt4o } from 'genkitx-openai';

  // Use the same API to generate content from many models
  const result = await generate({
      model: gemini15Flash, // Or use claude3Sonnet, llama31, gpt4o
      prompt: 'What makes you the best LLM out there?',
  });
  ```

- {Structured generation}

  ```javascript
  import { generate } from `@genkit/ai`;
  import { gemini15Flash } from `@genkit/googleai`;
  import { z } from `zod`;

  const result = await generate({
      model: gemini15Flash,
      prompt: 'Create a brief profile for a character in a fantasy video game.',
      // Specify output structure using Zod schema
      output: {
          schema: z.object({
              name: z.string(),
              role: z.enum(['knight', 'mage', 'archer']),
              backstory: z.string(),
              attacks: z.array(z.object({
                name: z.string(),
                damage: z.number().describe('amount of damage, between 2 and 25'),
              })).describe('3 attacks the character can use')
          })
      }
  });
  ```

- {Tool calling}

  ```javascript
  import { generate, defineTool } from `@genkit/ai`;
  import { gemini15Flash } from `@genkit/googleai`;
  import { z } from `zod`;

  // Define tool to get weather data for a given location
  const lookupWeather = defineTool({
      name: 'lookupWeather',
      description: 'Get the current weather in a location.',
      // Define input and output schema so the model knows how to use the tool
      inputSchema: z.object({
          location: z.string().describe('The location to get the weather for.'),
      }),
      outputSchema: z.object({
          temperature: z.number().describe('The current temperature in Fahrenheit.'),
          condition: z.string().describe('A brief description of the weather conditions.'),
      }),
      async (input) => {
          // Insert weather lookup API code
      }
  });

  const result = await generate({
      model: gemini15Flash,
      tools: [lookupWeather], // Give the model a list of tools it can call
      prompt: 'What is the weather like in New York? ',
  });
  ```

- {Retrieval}

  ```javascript
  import { generate, retrieve } from `@genkit/ai`;
  import { devLocalRetrieverRef } from '@genkit/dev-local-vectorstore';
  import { gemini15Flash } from `@genkit/googleai`;

  // Sample assumes Genkit documentation has been chunked, stored, and indexed in 
  // local vectorstore in previous step.

  // Reference to a local vector database storing Genkit documentation
  const retriever = devLocalRetrieverRef('genkitQA');

  const query = 'How do I retrieve relevant documents in Genkit?'

  // Consistent API to retrieve most relevant documents based on semantic similarity to query
  const docs = await retrieve({
      retriever: retriever,
      query: query,
      options: { limit: 5 },
  });

  const result = await generate({
      model: gemini15Flash
      prompt: 'Use the provided context from the Genkit documentation to answer this query: ${query}',
      context: docs // Pass retrieved documents to the model
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
