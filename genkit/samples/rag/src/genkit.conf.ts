import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { googleAI } from '@google-genkit/providers/google-ai';
import { firebase } from '@google-genkit/providers/firebase';
import { googleVertexAI } from '@google-genkit/providers/google-vertexai';
import { pinecone } from '@google-genkit/providers/pinecone';
import { vertexAI } from '@google-genkit/plugin-vertex-ai';
import { chroma } from '@google-genkit/providers/chroma';
import { textEmbeddingGecko001 } from '@google-genkit/providers/google-vertexai';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleAI(),
    googleVertexAI(),
    vertexAI({ projectId: 'fb-access-demo', location: 'us-central1' }),
    pinecone({
      indexId: 'tom-and-jerry',
      embedder: textEmbeddingGecko001,
      embedderOptions: { temperature: 0 },
    }),
    chroma({
      collectionName: 'spongebob_collection',
      embedder: textEmbeddingGecko001,
      embedderOptions: { temperature: 0 },
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
