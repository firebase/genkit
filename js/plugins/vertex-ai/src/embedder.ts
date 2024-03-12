import { defineEmbedder, embedderRef } from '@genkit-ai/ai/embedders';
import { GoogleAuth } from 'google-auth-library';
import { z } from 'zod';
import { PluginOptions } from '.';
import { predictModel } from './predict';

export const TaskTypeSchema = z.enum([
  'RETRIEVAL_DOCUMENT',
  'RETRIEVAL_QUERY',
  'SEMANTIC_SIMILARITY',
  'CLASSIFICATION',
  'CLUSTERING',
]);
export type TaskType = z.infer<typeof TaskTypeSchema>;

export const TextEmbeddingGeckoConfigSchema = z.object({
  /**
   * The `task_type` parameter is defined as the intended downstream application to help the model
   * produce better quality embeddings.
   **/
  taskType: TaskTypeSchema,
});
export type TextEmbeddingGeckoConfig = z.infer<
  typeof TextEmbeddingGeckoConfigSchema
>;

const TextEmbeddingGeckoInputSchema = z.union([
  z.string(),
  z.object({ title: z.string().optional(), content: z.string() }),
]);

export const textembeddingGecko = embedderRef({
  name: 'vertex-ai/textembedding-gecko',
  configSchema: TextEmbeddingGeckoConfigSchema,
  info: {
    dimension: 768,
    label: 'Vertex AI - Text Embedding Gecko',
    names: [
      'vertex-ai/textembedding-gecko-002',
      'vertex-ai/textembedding-gecko-003',
      'vertex-ai/textembedding-gecko-multilingual',
      'vertex-ai/textembedding-gecko-multilingual-001',
    ],
    supports: {
      input: ['text'],
    },
  },
});

interface EmbeddingInstance {
  task_type?: TaskType;
  content: string;
  title?: string;
}
interface EmbeddingPrediction {
  embeddings: {
    statistics: {
      truncated: boolean;
      token_count: number;
    };
    values: number[];
  };
}

export function textEmbeddingGeckoEmbedder(
  client: GoogleAuth,
  options: PluginOptions
) {
  // TODO: Figure out how to allow different versions while still sharing a single implementation.
  const predict = predictModel<EmbeddingInstance, EmbeddingPrediction>(
    client,
    options,
    'textembedding-gecko@003'
  );
  return defineEmbedder(
    {
      info: textembeddingGecko.info!,
      customOptionsType: TextEmbeddingGeckoConfigSchema,
      inputType: TextEmbeddingGeckoInputSchema,
      embedderId: textembeddingGecko.name,
      provider: 'vertex-ai',
    },
    async (input, options) => {
      const instance: EmbeddingInstance =
        typeof input === 'string' ? { content: input } : input;
      if (options?.taskType) {
        instance.task_type = options.taskType;
      }

      const response = await predict([instance]);
      return response.predictions[0].embeddings.values;
    }
  );
}
