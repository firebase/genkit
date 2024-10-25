// [START mini]
import { genkit } from 'genkit';

// Import the model plugins you want to use.
import { googleAI } from '@genkit-ai/googleai';

const ai = genkit({
  // Initialize and configure the model plugins.
  plugins: [
    googleAI({
      apiKey: 'your-api-key', // Or (preferred): export GOOGLE_GENAI_API_KEY=...
    }),
  ],
});
// [END mini]
