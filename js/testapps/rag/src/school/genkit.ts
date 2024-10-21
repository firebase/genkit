import devLocalVectorstore from '@genkit-ai/dev-local-vectorstore';
import { gemini15Flash, textEmbedding004, vertexAI } from '@genkit-ai/vertexai';
import { genkit } from 'genkit';
import { AgentStateSchema } from './types';

export const ai = genkit({
  plugins: [
    vertexAI({ projectId: 'bleigh-genkit-test', location: 'us-central1' }),
    devLocalVectorstore([
      { indexName: 'school-handbook', embedder: textEmbedding004 },
    ]),
  ],
  model: gemini15Flash,
});

export const env = ai.defineEnvironment({
  name: 'agentEnv',
  stateSchema: AgentStateSchema,
});

export { z } from 'genkit';
