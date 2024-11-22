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

import { Genkit, genkit } from 'genkit';
import { Registry } from '@genkit-ai/core/registry';
import fs from 'fs';
import { beforeEach, describe, it } from 'node:test';
import { strict as assert } from 'assert';

describe('e2e', () => {
  let ai: Genkit;
  let registry: Registry;

  beforeEach(() => {
    // Make sure directory exists
    if (!fs.existsSync(__dirname + '/prompts')) {
      fs.mkdirSync(__dirname + '/prompts');
    }

    registry = new Registry();

    ai = genkit({
      promptDir: './tests/prompts'
    });

    ai.defineModel(
      {
        name: 'echo',
      },
      async (request) => ({
        message: {
          role: 'model',
          content: [
            {
              text:
                request.messages
                  .map(
                    (m) =>
                      (m.role === 'user' || m.role === 'model'
                        ? ''
                        : `${m.role}: `) + m.content.map((c) => c.text).join()
                  )
                  .join(),
            }
          ],
        },
        finishReason: 'stop',
      })
    );
  });

  it('Should use cached prompt if GENKIT_ENV!="dev"', async () => {
    process.env.GENKIT_ENV = 'prod';

    const helloPrompt = "Say hello";
    const byePrompt = "Say bye";

    // Create prompt file
    fs.writeFileSync(__dirname + '/prompts/example.prompt', helloPrompt);

    let prompt = await ai.prompt('example');
    let result = await prompt(
      registry,
      {
        model: 'echo',
      }
    );
    assert.equal(result.text, helloPrompt);

    // Create new prompt file
    fs.writeFileSync(__dirname + '/prompts/example.prompt', byePrompt);

    prompt = await ai.prompt('example');
    result = await prompt(
      registry,
      {
        model: 'echo',
      }
    );
    assert.equal(result.text, helloPrompt);
  });

  it('Should reload prompt on every invocation if GENKIT_ENV="dev"', async () => {
    process.env.GENKIT_ENV = 'dev';

    const helloPrompt = "Say hello";
    const byePrompt = "Say bye";



    // Create prompt file
    fs.writeFileSync(__dirname + '/prompts/example.prompt', helloPrompt);

    let prompt = await ai.prompt('example');
    let result = await prompt(
      registry,
      {
        model: 'echo',
      }
    );
    assert.equal(result.text, helloPrompt);

    // Create new prompt file
    fs.writeFileSync(__dirname + '/prompts/example.prompt', byePrompt);

    prompt = await ai.prompt('example');
    result = await prompt(
      registry,
      {
        model: 'echo',
      }
    );
    assert.equal(result.text, byePrompt);

    // Test definePrompt
    prompt = ai.definePrompt({ name: 'hi' }, 'hi {{ name }}');
    result = await prompt(
      {
        name: 'hi'
      },
      {
        model: 'echo'
      }
    );
    assert.equal(result.text, 'hi hi');
  });
});
