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

import { ModelReference } from 'genkit/model';
import { genkitPlugin, Plugin } from 'genkit';
import {
    llama3,
    llama31,
    llama32,
    modelGardenOpenaiCompatibleModel,
    SUPPORTED_OPENAI_FORMAT_MODELS,
} from './model_garden.js';
import {
    anthropicModel,
    claude35Sonnet,
    claude3Haiku,
    claude3Opus,
    claude3Sonnet,
    SUPPORTED_ANTHROPIC_MODELS,
} from './anthropic.js';
import { authenticate } from '../common/auth.js';
import { BasePluginOptions } from '../common/types.js';
import { confError, DEFAULT_LOCATION } from '../common/global.js';

export {
    llama3,
    llama31,
    llama32,
    claude35Sonnet,
    claude3Haiku,
    claude3Opus,
    claude3Sonnet,
}

export interface PluginOptions extends BasePluginOptions {
    models: ModelReference<any>[];
    openAiBaseUrlTemplate?: string;
}

const PLUGIN_NAME = 'vertexAiModelGarden';

/**
 *  Plugin for Vertex AI Model Garden
 */
export const vertexAIModelGarden: Plugin<[PluginOptions] | []> = genkitPlugin(
    PLUGIN_NAME,
    async (options?: PluginOptions) => {
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

        const models: any = [];

        if (options?.models) {
            const mgModels = options?.models;
            mgModels!.forEach((m) => {
                const anthropicEntry = Object.entries(SUPPORTED_ANTHROPIC_MODELS).find(
                    ([_, value]) => value.name === m.name
                );

                if (anthropicEntry) {
                    models.push(anthropicModel(anthropicEntry[0], projectId, location));
                    return;
                }

                const openaiModel = Object.entries(SUPPORTED_OPENAI_FORMAT_MODELS).find(
                    ([_, value]) => value.name === m.name
                );

                if (openaiModel) {
                    models.push(
                        modelGardenOpenaiCompatibleModel(
                            openaiModel[0],
                            projectId,
                            location,
                            authClient,
                            options.openAiBaseUrlTemplate
                        )
                    );
                    return;
                }

                throw new Error(`Unsupported model garden model: ${m.name}`);
            });
        }

        return {
            models
        };
    }
);

export default vertexAIModelGarden;