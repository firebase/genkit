/**
 * Copyright 2024 The Fire Company
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
/* eslint-disable  @typescript-eslint/no-explicit-any */

import { embedderRef as createEmbedderRef } from 'genkit';

import {
  BedrockRuntimeClient,
  InvokeModelCommand,
  InvokeModelCommandInput,
  InvokeModelCommandOutput,
} from '@aws-sdk/client-bedrock-runtime';
import { z } from 'genkit';
import { embedder } from 'genkit/plugin';

export const TextEmbeddingConfigSchema = z.object({
  dimensions: z.number().optional(),
});

export type TextEmbeddingGeckoConfig = z.infer<
  typeof TextEmbeddingConfigSchema
>;

export const TextEmbeddingInputSchema = z.string();

export const amazonTitanEmbedTextV2 = createEmbedderRef({
  name: 'aws-bedrock/amazon.titan-embed-text-v2:0',
  configSchema: TextEmbeddingConfigSchema,
  info: {
    dimensions: 1024,
    label: 'Amazon - titan-embed-text-v2:0',
    supports: {
      input: ['text'],
    },
  },
});

export const amazonTitanEmbedMultimodalV2 = createEmbedderRef({
  name: 'aws-bedrock/amazon.titan-embed-image-v1',
  configSchema: TextEmbeddingConfigSchema,
  info: {
    dimensions: 1024,
    label: 'Amazon - titan-embed-multimodal-v2:0',
    supports: {
      input: ['text', 'image'],
    },
  },
});

export const amazonTitanEmbedTextG1V1 = createEmbedderRef({
  name: 'aws-bedrock/amazon.titan-embed-text-v1',
  configSchema: TextEmbeddingConfigSchema,
  info: {
    dimensions: 1536,
    label: 'Amazon - titan-embed-text-v1',
    supports: {
      input: ['text'],
    },
  },
});

export const cohereEmbedEnglishV3 = createEmbedderRef({
  name: 'aws-bedrock/cohere.embed-english-v3',
  configSchema: TextEmbeddingConfigSchema,
  info: {
    dimensions: 1024,
    label: 'Cohere - embed-english-v3',
    supports: {
      input: ['text'],
    },
  },
});

export const cohereEmbedMultilingualV3 = createEmbedderRef({
  name: 'aws-bedrock/cohere.embed-multilingual-v3',
  configSchema: TextEmbeddingConfigSchema,
  info: {
    dimensions: 1024,
    label: 'Cohere - embed-multilingual-v3',
    supports: {
      input: ['text'],
    },
  },
});

export const SUPPORTED_EMBEDDING_MODELS: Record<string, any> = {
  'amazon.titan-embed-text-v2:0': amazonTitanEmbedTextV2,
  'amazon.titan-embed-image-v1': amazonTitanEmbedMultimodalV2,
  'amazon.titan-embed-text-v1': amazonTitanEmbedTextG1V1,
  'cohere.embed-english-v3': cohereEmbedEnglishV3,
  'cohere.embed-multilingual-v3': cohereEmbedMultilingualV3,
};

export function awsBedrockEmbedder(name: string, client: BedrockRuntimeClient) {
  const modelRef = SUPPORTED_EMBEDDING_MODELS[name];
  if (!modelRef) throw new Error(`Unsupported model: ${name}`);

  return embedder(
    {
      info: modelRef.info!,
      configSchema: TextEmbeddingConfigSchema,
      name: modelRef.name,
    },
    async (request) => {
      const { input, options } = request;
      const body: InvokeModelCommandInput = {
        modelId: name,
        contentType: 'application/json',
        body: JSON.stringify({
          inputText: input.map((d: any) => d.text).join(','),
          dimensions: options?.dimensions,
        }),
      };

      const command = new InvokeModelCommand(body);

      const response = (await client.send(command)) as InvokeModelCommandOutput;
      const embeddings = new TextDecoder().decode(response.body)
        ? JSON.parse(new TextDecoder().decode(response.body))
        : [];
      return {
        embeddings: [
          {
            embedding: embeddings.embedding as number[],
          },
        ],
      };
    }
  );
}
