import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { vertexAI } from '@google-genkit/plugin-vertex-ai';
import { chroma } from '@google-genkit/providers/chroma';
import { firebase } from '@google-genkit/providers/firebase';
import { geminiPro, googleAI } from '@google-genkit/providers/google-ai';
import { RagasMetric, ragas } from '@google-genkit/plugin-ragas';
import {
  googleVertexAI,
  textEmbeddingGecko001,
} from '@google-genkit/providers/google-vertexai';
import { naiveFilestore } from '@google-genkit/providers/naive-filestore';
import { pinecone } from '@google-genkit/providers/pinecone';

export default configureGenkit({
  plugins: [
    firebase({ projectId: getProjectId() }),
    googleAI(),
    googleVertexAI(),
    ragas({ judge: geminiPro, metrics: [RagasMetric.CONTEXT_PRECISION] }),
    vertexAI({ projectId: getProjectId(), location: 'us-central1' }),
    pinecone([
      {
        indexId: 'tom-and-jerry',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
      {
        indexId: 'pdf-chat',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
    ]),
    chroma({
      collectionName: 'spongebob_collection',
      embedder: textEmbeddingGecko001,
      embedderOptions: { temperature: 0 },
    }),
    naiveFilestore({
      embedder: textEmbeddingGecko001,
      embedderOptions: { temperature: 0 },
    }),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
