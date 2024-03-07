import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { openAI } from '@google-genkit/plugin-openai';
import { googleGenAI } from '@google-genkit/plugin-google-genai';
import { firebase } from '@google-genkit/plugin-firebase';
import { chroma } from '@google-genkit/plugin-chroma';
import {
  googleVertexAI,
  textEmbeddingGecko001,
} from '@google-genkit/providers/google-vertexai';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleGenAI(),
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
