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

import { Plugin, genkitPlugin } from '@genkit-ai/common/config';
import { imagen2, imagen2Model } from './imagen';
import {
  geminiModel,
  geminiPro,
  geminiProVision,
  SUPPORTED_GEMINI_MODELS,
} from './gemini';
import { VertexAI } from '@google-cloud/vertexai';
import { getProjectId, getLocation } from '@genkit-ai/common';
import { textEmbeddingGeckoEmbedder, textembeddingGecko } from './embedder';
import { GoogleAuth } from 'google-auth-library';

export { imagen2, geminiPro, geminiProVision, textembeddingGecko };

export interface PluginOptions {
  projectId?: string;
  location: string;
}

export const vertexAI: Plugin<[PluginOptions]> = genkitPlugin(
  'vertex-ai',
  async (options: PluginOptions) => {
    const authClient = new GoogleAuth();
    const project = options.projectId || getProjectId();
    const location = options.location || getLocation();

    const confError = (parameter: string, envVariableName: string) => {
      return new Error(
        `VertexAI Plugin is missing the '${parameter}' configuration. Please set the '${envVariableName}' environment variable or explicitly pass '${parameter}' into genkit config.`
      );
    };
    if (!location) {
      throw confError('location', 'GCLOUD_LOCATION');
    }
    if (!project) {
      throw confError('project', 'GCLOUD_PROJECT');
    }

    const vertexClient = new VertexAI({ project, location });
    return {
      models: [
        imagen2Model(authClient, options),
        ...Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
          geminiModel(name, vertexClient)
        ),
      ],
      embedders: [textEmbeddingGeckoEmbedder(authClient, options)],
    };
  }
);

export default vertexAI;
