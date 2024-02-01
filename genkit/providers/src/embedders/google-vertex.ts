import { embedderFactory } from '@google-genkit/ai/embedders';
import { PredictionServiceClient, helpers } from '@google-cloud/aiplatform';
import { getProjectId } from '@google-genkit/common';
import * as z from 'zod';

const VertexEmbedderrOptionsSchema = z.object({
  temperature: z.number().optional(),
  maxOutputTokens: z.number().optional(),
  topP: z.number().optional(),
  topK: z.number().optional(),
});

/**
 * Configures a Vertex embedder model.
 */
export function configureVertexTextEmbedder(params: {
  projectId?: string;
  location?: string;
  publisher?: string;
  modelName: string;
}) {
  const projectId = params.projectId || getProjectId();
  const location = params.location || 'us-central1';
  const publisher = params.publisher || 'google';
  const modelName = params.modelName;
  const clientOptions = {
    apiEndpoint: location + '-aiplatform.googleapis.com',
  };
  const predictionServiceClient = new PredictionServiceClient(clientOptions);
  return embedderFactory(
    publisher,
    'vertexai',
    z.string(),
    VertexEmbedderrOptionsSchema,
    async (input, options) => {
      const endpoint =
        `projects/${projectId}/locations/${location}/` +
        `publishers/${publisher}/models/${modelName}`;
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
