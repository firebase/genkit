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

import { Plugin, genkitPlugin } from '@genkit-ai/core';
import { VertexAI } from '@google-cloud/vertexai';
import { GoogleAuth, GoogleAuthOptions } from 'google-auth-library';
import {
  SUPPORTED_EMBEDDER_MODELS,
  textEmbeddingGecko,
  textEmbeddingGeckoEmbedder,
} from './embedder.js';
import {
  SUPPORTED_GEMINI_MODELS,
  gemini15ProPreview,
  geminiModel,
  geminiPro,
  geminiProVision,
} from './gemini.js';
import { imagen2, imagen2Model } from './imagen.js';

export {
  gemini15ProPreview,
  geminiPro,
  geminiProVision,
  imagen2,
  textEmbeddingGecko,
};

export interface PluginOptions {
  /** The Google Cloud project id to call. */
  projectId?: string;
  /** The Google Cloud region to call. */
  location: string;
  /** Provide custom authentication configuration for connecting to Vertex AI. */
  googleAuth?: GoogleAuthOptions;
}

/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
export const vertexAI: Plugin<[PluginOptions] | []> = genkitPlugin(
  'vertexai',
  async (options?: PluginOptions) => {
    const authClient = new GoogleAuth(options?.googleAuth);
    const projectId = options?.projectId || (await authClient.getProjectId());
    const location = options?.location || 'us-central1';

    const confError = (parameter: string, envVariableName: string) => {
      return new Error(
        `VertexAI Plugin is missing the '${parameter}' configuration. Please set the '${envVariableName}' environment variable or explicitly pass '${parameter}' into genkit config.`
      );
    };
    if (!location) {
      throw confError('location', 'GCLOUD_LOCATION');
    }
    if (!projectId) {
      throw confError('project', 'GCLOUD_PROJECT');
    }

    const vertexClient = new VertexAI({
      project: projectId,
      location,
      googleAuthOptions: options?.googleAuth,
    });
    return {
      models: [
        imagen2Model(authClient, { projectId, location }),
        ...Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
          geminiModel(name, vertexClient)
        ),
      ],
      embedders: [
        ...Object.keys(SUPPORTED_EMBEDDER_MODELS).map((name) =>
          textEmbeddingGeckoEmbedder(name, authClient, { projectId, location })
        ),
      ],
    };
  }
);

export default vertexAI;
