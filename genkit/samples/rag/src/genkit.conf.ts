import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';
import { googleAI } from '@google-genkit/providers/google-ai';
import { firebase } from '@google-genkit/providers/firebase';
import { pinecone } from '@google-genkit/providers/pinecone';
import { geminiPro, vertexAI } from '@google-genkit/plugin-vertex-ai';
import { chroma } from '@google-genkit/providers/chroma';
import { RagasMetric, ragas } from '@google-genkit/plugin-ragas';
import {
  googleVertexAI,
  textEmbeddingGecko001,
} from '@google-genkit/providers/google-vertexai';
import { naiveFilestore } from '@google-genkit/providers/naive-filestore';

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
    naiveFilestore([
      {
        indexName: 'spongebob-facts',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
      {
        indexName: 'pdfQA',
        embedder: textEmbeddingGecko001,
        embedderOptions: { temperature: 0 },
      },
    ]),
  ],
  flowStateStore: 'firebase',
  traceStore: 'firebase',
  enableTracingAndMetrics: true,
  logLevel: 'debug',
});
