import * as z from 'zod';

// Import the Genkit core libraries and plugins.
import { vertexAI, claude35Sonnet, gemini15Flash } from '@genkit-ai/vertexai';
import { generate, genkit } from 'genkit';

const ai = genkit({
  plugins: [
    vertexAI({
      location: 'europe-west1',
      modelGarden: {
        models: [claude35Sonnet]
      }
    }),
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
      model: claude35Sonnet
    });


    return { output: llmResponse.text()}

    const output = llmResponse.output();

    if (output === null) {
      console.error(output);
      throw new Error('Failed to generate menu suggestion');
    }

    // Handle the response from the model API. In this sample, we just convert
    // it to a string, but more complicated flows might coerce the response into
    // structured output or chain the response into another LLM call, etc.
    return llmResponse.output()!;
  }
);
