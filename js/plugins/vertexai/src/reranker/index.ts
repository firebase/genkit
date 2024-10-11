// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { genkitPlugin, Plugin } from 'genkit';
import { authenticate } from '../common/auth.js';
import { confError, DEFAULT_LOCATION } from '../common/global.js';
import { BasePluginOptions } from '../common/types.js';
import { vertexAiRerankers, VertexRerankerConfig } from './reranker.js';

export interface PluginOptions extends BasePluginOptions {
  /** Configure reranker options */
  options: VertexRerankerConfig[];
}

/**
 *  Plugin for Vertex AI Reranker
 */
export const vertexAIReranker: Plugin<[PluginOptions]> = genkitPlugin(
  'vertexaiReranker',
  async (options: PluginOptions) => {
    // Authenticate with Google Cloud
    const authOptions = options?.googleAuth;
    const authClient = authenticate(authOptions);

    const projectId = options?.projectId || (await authClient.getProjectId());
    const location = options?.location || DEFAULT_LOCATION;

    if (!location) {
      throw confError('location', 'GCLOUD_LOCATION');
    }
    if (!projectId) {
      throw confError('project', 'GCLOUD_PROJECT');
    }

    const rerankOptions = {
        pluginOptions: options,
        authClient,
        projectId,
    };

    const rerankers = await vertexAiRerankers(rerankOptions);

    return {
      rerankers,
    };
  }
);

export default vertexAIReranker;