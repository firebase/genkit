import { defineEmbedder, EmbedderReference } from '@genkit-ai/ai/embedder';
import { logger } from '@genkit-ai/core/logging';
import z from 'zod';
import { OllamaPluginParams } from './index.js';

// Define the schema for Ollama embedding configuration
export const OllamaEmbeddingConfigSchema = z.object({
  modelName: z.string(),
  serverAddress: z.string(),
});
export type OllamaEmbeddingConfig = z.infer<typeof OllamaEmbeddingConfigSchema>;

// Define the structure of the request and response for embedding
interface OllamaEmbeddingInstance {
  content: string;
}

interface OllamaEmbeddingPrediction {
  embedding: number[];
}

export function defineOllamaEmbedder(
  name: string,
  modelName: string,
  dimensions: number,
  options: OllamaPluginParams
): EmbedderReference<typeof OllamaEmbeddingConfigSchema> {
  return defineEmbedder(
    {
      name,
      configSchema: OllamaEmbeddingConfigSchema, // Use the Zod schema directly here
      info: {
        label: 'Embedding using Ollama',
        dimensions,
        supports: {
          //  TODO: do any ollama models support other modalities?
          input: ['text'],
        },
      },
    },
    async (input, _config) => {
      const serverAddress = options.serverAddress;

      const responses = await Promise.all(
        input.map(async (i) => {
          const requestPayload = {
            model: modelName,
            prompt: i.text(),
          };
          let res: Response;
          try {
            console.log('MODEL NAME: ', modelName);
            res = await fetch(`${serverAddress}/api/embeddings`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(requestPayload),
            });
          } catch (e) {
            logger.error('Failed to fetch Ollama embedding');
            throw new Error(`Error fetching embedding from Ollama: ${e}`);
          }

          if (!res.ok) {
            logger.error('Failed to fetch Ollama embedding');
            throw new Error(
              `Error fetching embedding from Ollama: ${res.statusText}`
            );
          }

          const responseData = (await res.json()) as OllamaEmbeddingPrediction;
          return responseData;
        })
      );

      return {
        embeddings: responses,
      };
    }
  );
}
