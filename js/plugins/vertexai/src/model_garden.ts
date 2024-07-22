/**
 * Copyright 2024 Google LLC
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

import { ModelAction, modelRef } from '@genkit-ai/ai/model';
import { GENKIT_CLIENT_HEADER } from '@genkit-ai/core';
import { GoogleAuth } from 'google-auth-library';
import OpenAI from 'openai';

import {
  openaiCompatibleModel,
  OpenAIConfigSchema,
} from './openai_compatibility.js';

const ACCESS_TOKEN_TTL = 50 * 60 * 1000; // cache access token for 50 minutes

export const llama3 = modelRef({
  name: 'vertexai/llama3-405b',
  info: {
    label: 'Llama 3.1 405b',
    supports: {
      multiturn: true,
      tools: true,
      media: false,
      systemRole: true,
      output: ['text'],
    },
    versions: ['meta/llama3-405b-instruct-maas'],
  },
  configSchema: OpenAIConfigSchema,
  version: 'meta/llama3-405b-instruct-maas',
});

export const SUPPORTED_OPENAI_FORMAT_MODELS = {
  'llama3-405b': llama3,
};

export function modelGardenOpenaiCompatibleModel(
  name: string,
  projectId: string,
  location: string,
  googleAuth: GoogleAuth
): ModelAction<typeof OpenAIConfigSchema> {
  const model = SUPPORTED_OPENAI_FORMAT_MODELS[name];
  if (!model) throw new Error(`Unsupported model: ${name}`);

  let accessToken: string | null | undefined;
  let accessTokenFetchTime = 0;
  var clientCache: OpenAI;
  const clientFactory = async () => {
    if (
      !clientCache ||
      !accessToken ||
      accessTokenFetchTime + ACCESS_TOKEN_TTL < Date.now()
    ) {
      accessToken = await googleAuth.getAccessToken();
      accessTokenFetchTime = Date.now();
      clientCache = new OpenAI({
        baseURL: `https://${location}-aiplatform.googleapis.com/v1beta1/projects/${projectId}/locations/${location}/endpoints/openapi`,
        apiKey: accessToken!,
        defaultHeaders: {
          'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
        },
      });
    }

    return clientCache;
  };
  return openaiCompatibleModel(model, clientFactory);
}
