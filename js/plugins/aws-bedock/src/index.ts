/**
 * Copyright 2026 Google LLC
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

import {
  BedrockRuntimeClient,
  BedrockRuntimeClientConfig,
} from '@aws-sdk/client-bedrock-runtime';
import { GenerationCommonConfigSchema } from 'genkit';
import { ModelAction } from 'genkit/model';
import { genkitPluginV2, type ResolvableAction } from 'genkit/plugin';

import {
  SUPPORTED_EMBEDDING_MODELS,
  amazonTitanEmbedMultimodalV2,
  amazonTitanEmbedTextG1V1,
  amazonTitanEmbedTextV2,
  awsBedrockEmbedder,
  cohereEmbedEnglishV3,
  cohereEmbedMultilingualV3,
} from './aws_bedrock_embedders.js';
import {
  SUPPORTED_AWS_BEDROCK_MODELS,
  ai21Jamba15LargeV1,
  ai21Jamba15MiniV1,
  ai21JambaInstructV1,
  ai21Jurassic2MidV1,
  ai21Jurassic2UltraV1,
  amazonNovaLiteV1,
  amazonNovaMicroV1,
  amazonNovaProV1,
  amazonTitanTextG1ExpressV1,
  amazonTitanTextG1LiteV1,
  amazonTitanTextG1PremierV1,
  anthropicClaude21V1,
  anthropicClaude2V1,
  anthropicClaude35HaikuV1,
  anthropicClaude35SonnetV2,
  anthropicClaude37SonnetV1,
  anthropicClaude3HaikuV1,
  anthropicClaude3OpusV1,
  anthropicClaude3SonnetV1,
  anthropicClaudeInstantV1,
  awsBedrockModel,
  cohereCommandLightV14,
  cohereCommandRPlusV1,
  cohereCommandRV1,
  cohereCommandV14,
  metaLlama3170BInstruct,
  metaLlama318BInstruct,
  metaLlama3211BInstruct,
  metaLlama321BInstruct,
  metaLlama323BInstruct,
  metaLlama3290BInstruct,
  metaLlama3370BInstruct,
  metaLlama370BInstruct,
  metaLlama38BInstruct,
  mistral7BInstructV02,
  mistral8x7BInstructV01,
  mistralLarge2402V1,
  mistralSmall2402V1,
} from './aws_bedrock_llms.js';

export {
  ai21Jamba15LargeV1,
  ai21Jamba15MiniV1,
  ai21JambaInstructV1,
  ai21Jurassic2MidV1,
  ai21Jurassic2UltraV1,
  amazonNovaLiteV1,
  amazonNovaMicroV1,
  amazonNovaProV1,
  amazonTitanTextG1ExpressV1,
  amazonTitanTextG1LiteV1,
  amazonTitanTextG1PremierV1,
  anthropicClaude21V1,
  anthropicClaude2V1,
  anthropicClaude35HaikuV1,
  anthropicClaude35SonnetV2,
  anthropicClaude37SonnetV1,
  anthropicClaude3HaikuV1,
  anthropicClaude3OpusV1,
  anthropicClaude3SonnetV1,
  anthropicClaudeInstantV1,
  cohereCommandLightV14,
  cohereCommandRPlusV1,
  cohereCommandRV1,
  cohereCommandV14,
  metaLlama3170BInstruct,
  metaLlama318BInstruct,
  metaLlama3211BInstruct,
  metaLlama321BInstruct,
  metaLlama323BInstruct,
  metaLlama3290BInstruct,
  metaLlama3370BInstruct,
  metaLlama370BInstruct,
  metaLlama38BInstruct,
  mistral7BInstructV02,
  mistral8x7BInstructV01,
  mistralLarge2402V1,
  mistralSmall2402V1,
};

export {
  amazonTitanEmbedMultimodalV2,
  amazonTitanEmbedTextG1V1,
  amazonTitanEmbedTextV2,
  cohereEmbedEnglishV3,
  cohereEmbedMultilingualV3,
};

export interface PluginOptions extends BedrockRuntimeClientConfig {
  /**
   * Additional model names to register that are not in the predefined list.
   * These models will be available using the 'aws-bedrock/model-name' format.
   * @example ['custom.my-custom-model-v1:0']
   */
  customModels?: string[];
}

/**
 * Defines a custom AWS Bedrock model that is not exported by the plugin
 * @param name - The name of the model (e.g., "custom.my-model-v1:0")
 * @param options - Plugin options including AWS credentials and region
 * @returns A ModelAction that can be used with Genkit
 *
 * @example
 * ```typescript
 * import { defineAwsBedrockModel } from '@genkit-ai/aws-bedrock';
 *
 * const customModel = defineAwsBedrockModel('custom.my-model-v1:0', {
 *   region: 'us-east-1'
 * });
 *
 * const response = await ai.generate({
 *   model: customModel,
 *   prompt: 'Hello!'
 * });
 * ```
 */
export function defineAwsBedrockModel(
  name: string,
  options?: PluginOptions
): ModelAction<typeof GenerationCommonConfigSchema> {
  const client = new BedrockRuntimeClient(options || {});

  const region =
    typeof options?.region === 'string' ? options.region : undefined;
  let inferenceRegion = '';
  if (!region) {
    inferenceRegion = 'us'; // default to us
  } else if (region.includes('us-gov')) {
    inferenceRegion = 'us-gov';
  } else if (region.includes('us')) {
    inferenceRegion = 'us';
  } else if (region.includes('eu-')) {
    inferenceRegion = 'eu';
  } else if (region.includes('ap-')) {
    inferenceRegion = 'apac';
  }

  return awsBedrockModel(name, client, inferenceRegion);
}

export function awsBedrock(options?: PluginOptions) {
  const client = new BedrockRuntimeClient(options || {});

  const region =
    typeof options?.region === 'string' ? options.region : undefined;
  let inferenceRegion = '';
  if (!region) {
    inferenceRegion = 'us'; // default to us
  } else if (region.includes('us-gov')) {
    inferenceRegion = 'us-gov';
  } else if (region.includes('us')) {
    inferenceRegion = 'us';
  } else if (region.includes('eu-')) {
    inferenceRegion = 'eu';
  } else if (region.includes('ap-')) {
    inferenceRegion = 'apac';
  }

  return genkitPluginV2({
    name: 'aws-bedrock',
    init: async () => {
      const actions: ResolvableAction[] = [];

      // Register models
      for (const name of Object.keys(
        SUPPORTED_AWS_BEDROCK_MODELS(inferenceRegion)
      )) {
        actions.push(awsBedrockModel(name, client, inferenceRegion));
      }

      // Register custom models if provided
      if (options?.customModels) {
        for (const name of options.customModels) {
          actions.push(awsBedrockModel(name, client, inferenceRegion));
        }
      }

      // Register embedders
      for (const name of Object.keys(SUPPORTED_EMBEDDING_MODELS)) {
        actions.push(awsBedrockEmbedder(name, client));
      }

      return actions;
    },
  });
}

export default awsBedrock;
