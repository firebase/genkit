import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { openAI } from '@google-genkit/plugin-openai';
import { googleAI } from '@google-genkit/providers/google-ai';
import { firebase } from '@google-genkit/plugin-firebase';
import { chroma } from '@google-genkit/plugin-chroma';
import {
  googleVertexAI,
  textEmbeddingGecko001,
} from '@google-genkit/providers/google-vertexai';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleAI(),
    openAI(),
    googleVertexAI(),
    chroma({
      collectionName: 'spongebob_collection',
      embedder: textEmbeddingGecko001,
      embedderOptions: { topK: 7 },
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
