import { getProjectId } from '@google-genkit/common';
import { configureGenkit } from '@google-genkit/common/config';

// plugins
import { googleGenAI, geminiPro } from '@google-genkit/plugin-google-genai';
import { openAI } from '@google-genkit/plugin-openai';
import { ragas, RagasMetric } from '@google-genkit/plugin-ragas';
import { vertexAI, textembeddingGecko } from '@google-genkit/plugin-vertex-ai';

// providers - will be moved to plugins eventually
import { chroma } from '@google-genkit/plugin-chroma';
import { firebase } from '@google-genkit/plugin-firebase';
import { devLocalVectorstore } from '@google-genkit/plugin-dev-local-vectorstore';
import { ollama } from '@google-genkit/plugin-ollama';
import { pinecone } from '@google-genkit/plugin-pinecone';

// Not all plugins configured below are used by the flow, but we load
// "everything" for UI development and testing.
export default configureGenkit({
  plugins: [
    // plugins
    googleGenAI(),
    openAI(),
    vertexAI({ projectId: getProjectId(), location: 'us-central1' }),
    ragas({ judge: geminiPro, metrics: [RagasMetric.CONTEXT_PRECISION] }),

    // providers - will be moved to plugins eventually
    chroma({
      collectionName: 'chroma-collection',
      embedder: textembeddingGecko,
      embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
    }),
    firebase({ projectId: getProjectId() }),
    devLocalVectorstore([
      {
        indexName: 'naive-index',
        embedder: textembeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
    ollama({
      models: [{ name: 'llama2' }],
      serverAddress: 'http://127.0.0.1:11434', // default local port
      pullModel: false,
    }),
    pinecone([
      {
        indexId: 'pinecone-index',
        embedder: textembeddingGecko,
        embedderOptions: { taskType: 'RETRIEVAL_DOCUMENT' },
      },
    ]),
  ],
  enableTracingAndMetrics: true,
  flowStateStore: 'firebase',
  logLevel: 'debug',
  traceStore: 'firebase',
});
