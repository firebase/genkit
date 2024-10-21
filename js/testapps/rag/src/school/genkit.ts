import devLocalVectorstore from '@genkit-ai/dev-local-vectorstore';
import { textEmbedding004, vertexAI, gemini15Flash } from '@genkit-ai/vertexai';
import { genkit } from 'genkit';

export const ai = genkit({
  plugins: [
    vertexAI({ projectId: 'bleigh-genkit-test', location: 'us-central1' }),
    devLocalVectorstore([
      { indexName: 'school-handbook', embedder: textEmbedding004 },
    ]),
  ],
  model: gemini15Flash
});

export { z } from 'genkit';
