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

import { LLMResult } from '@langchain/core/outputs';
import { generate } from 'genkit';
import { logger } from 'genkit/logging';
import { ModelAction, ModelArgument } from 'genkit/model';
import { CallbackManagerForLLMRun } from 'langchain/callbacks';
import { BaseLLM } from 'langchain/llms/base';

export function genkitModel(model: ModelArgument, config?: any): BaseLLM {
  return new ModelAdapter(model, config);
}

class ModelAdapter extends BaseLLM {
  resolvedModel?: ModelAction;

  constructor(
    private model: ModelArgument,
    private config?: any
  ) {
    super({});
  }

  async _generate(
    prompts: string[],
    options: this['ParsedCallOptions'],
    runManager?: CallbackManagerForLLMRun | undefined
  ): Promise<LLMResult> {
    logger.debug(
      'ModelAdapter._generate',
      JSON.stringify(arguments, undefined, '  ')
    );
    //options
    const ress = await Promise.all(
      prompts.map((p) =>
        generate({
          model: this.model,
          prompt: p,
          config: this.config,
        })
      )
    );

    return {
      generations: ress.map((r) => [{ text: r.text() }]),
    };
  }

  _llmType() {
    return 'genkit';
  }
}
