import { PredictionServiceClient, helpers } from '@google-cloud/aiplatform';
import { defineEmbedder, embedderRef } from '@google-genkit/ai/embedders';
import { getProjectId } from '@google-genkit/common';
import { Plugin, genkitPlugin } from '@google-genkit/common/config';
import * as z from 'zod';

export interface PluginOptions {
  projectId?: string;
  location?: string;
  publisher?: string;
}

const VertexEmbedderrOptionsSchema = z.object({
  temperature: z.number().optional(),
  maxOutputTokens: z.number().optional(),
  topP: z.number().optional(),
  topK: z.number().optional(),
});

export const textEmbeddingGecko001 = embedderRef({
  name: 'google-vertexai/textembedding-gecko@001',
  info: {
    label: 'Google Vertex AI - Text Embedding Gecko',
    names: ['textembedding-gecko@001'],
    supports: {
      input: ['text'],
      multilingual: false,
    },
    dimension: 768,
  },
  configSchema: VertexEmbedderrOptionsSchema.optional(),
});

const SUPPORTED_TEXT_EMBEDDERS = {
  'textembedding-gecko@001': textEmbeddingGecko001,
};

export const googleVertexAI: Plugin<[PluginOptions] | []> = genkitPlugin(
  'google-vertexai',
  async (params?: PluginOptions) => ({
    embedders: Object.keys(SUPPORTED_TEXT_EMBEDDERS).map((name) =>
      googleVertexAiTextEmbedder(name, params)
    ),
  })
);

/**
 * Configures a Vertex embedder model.
 */
export function googleVertexAiTextEmbedder(
  id: string,
  params?: {
    projectId?: string;
    location?: string;
    publisher?: string;
  }
) {
  if (!SUPPORTED_TEXT_EMBEDDERS[id])
    throw new Error(`Unsupported text embedding model: ${id}`);
  const name = SUPPORTED_TEXT_EMBEDDERS[id].name;
  const projectId = params?.projectId || getProjectId();
  const location = params?.location || 'us-central1';
  const publisher = params?.publisher || 'google';
  const clientOptions = {
    apiEndpoint: location + '-aiplatform.googleapis.com',
  };
  const predictionServiceClient = new PredictionServiceClient(clientOptions);
  return defineEmbedder(
    {
      provider: publisher,
      embedderId: name,
      inputType: z.string(),
      info: SUPPORTED_TEXT_EMBEDDERS[id].info,
      customOptionsType: VertexEmbedderrOptionsSchema,
    },
    async (input, options) => {
      const endpoint =
        `projects/${projectId}/locations/${location}/` +
        `publishers/${publisher}/models/${id}`;
      const instance = {
        content: input,
      };
      const instanceValue = helpers.toValue(instance);
      const instances = [instanceValue] as protobuf.common.IValue[];

      const parameters = options ? helpers.toValue(options) : undefined;

      const request = {
        endpoint,
        instances,
        parameters,
      };

      const [response] = await predictionServiceClient.predict(request);
      const prediction = response?.predictions?.[0];
      if (!prediction) {
        return [];
      }
      const parsedPrediction = helpers.fromValue(
        prediction as protobuf.common.IValue
      );
      const values = parsedPrediction
        ? parsedPrediction['embeddings']['values']
        : [];
      return values;
    }
  );
}
