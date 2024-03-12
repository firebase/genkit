import { getProjectId } from '@genkit-ai/common';
import { configureGenkit } from '@genkit-ai/common/config';

// plugins
import { googleGenAI, geminiPro } from '@genkit-ai/plugin-google-genai';
import { openAI } from '@genkit-ai/plugin-openai';
import { ragas, RagasMetric } from '@genkit-ai/plugin-ragas';
import { vertexAI, textembeddingGecko } from '@genkit-ai/plugin-vertex-ai';

// providers - will be moved to plugins eventually
import { chroma } from '@genkit-ai/plugin-chroma';
import { firebase } from '@genkit-ai/plugin-firebase';
import { devLocalVectorstore } from '@genkit-ai/plugin-dev-local-vectorstore';
import { ollama } from '@genkit-ai/plugin-ollama';
import { pinecone } from '@genkit-ai/plugin-pinecone';

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
