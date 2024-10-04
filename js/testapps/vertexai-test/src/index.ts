import * as z from 'zod';

// Import the Genkit core libraries and plugins.
import { claude35Sonnet, vertexAI } from '@genkit-ai/vertexai';
// TODO: make this work
// import { vertexAIModelGarden } from '@genkit-ai/vertexai/modelgarden';
import { generate, genkit } from 'genkit';
// TODO: make this work

const ai = genkit({
  plugins: [
    vertexAI({ location: 'us-central1' }),
    // TODO: make this work
    // vertexAIModelGarden({
    // some params here
    // }),
  ],
});

// Define a simple flow that prompts an LLM to generate menu suggestions.
export const menuSuggestionFlow = ai.defineFlow(
  {
    name: 'menuSuggestionFlow',
    inputSchema: z.object({ subject: z.string() }),
    outputSchema: z.object({ output: z.string() }),
  },
  async ({ subject }) => {
    // Construct a request and send it to the model API.
    const llmResponse = await generate({
      prompt: `Suggest an item for the menu of a ${subject} themed restaurant`,
      model: claude35Sonnet,
      output: {
        format: 'json',
        schema: z.object({
          output: z.string(),
        }),
      },
      config: {
        temperature: 1,
      },
    });

    const output = llmResponse.output();

    if (output === null) {
      throw new Error('Failed to generate menu suggestion');
    }

    // Handle the response from the model API. In this sample, we just convert
    // it to a string, but more complicated flows might coerce the response into
    // structured output or chain the response into another LLM call, etc.
    return llmResponse.output()!;
  }
);
