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

import { Registry } from '@genkit-ai/core/registry';
import { strict as assert } from 'assert';
import fs from 'fs';
import { Genkit, genkit } from 'genkit';
import { afterEach, beforeEach, describe, it } from 'node:test';

describe('e2e', () => {
  let ai: Genkit;
  let registry: Registry;

  afterEach(async () => {
    await ai.stopServers();
    const promptFile = __dirname + '/prompts/example.prompt';
    if (fs.existsSync(promptFile)) {
      fs.unlinkSync(promptFile);
    }
  });

  beforeEach(() => {
    // Make sure directory exists
    if (!fs.existsSync(__dirname + '/prompts')) {
      fs.mkdirSync(__dirname + '/prompts');
    }

    registry = new Registry();

    ai = genkit({
      promptDir: './tests/prompts',
    });

    ai.defineModel(
      {
        name: 'echo',
      },
      async (request) => {
        return new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              message: {
                role: 'model',
                content: [
                  {
                    text: request.messages
                      .map(
                        (m) =>
                          (m.role === 'user' || m.role === 'model'
                            ? ''
                            : `${m.role}: `) +
                          m.content.map((c) => c.text).join()
                      )
                      .join(),
                  },
                ],
              },
              finishReason: 'stop',
            });
          }, 100); // For some reason the test hangs without this
        });
      }
    );
  });

  it('Should use cached prompt if GENKIT_ENV!="dev"', async () => {
    process.env.GENKIT_ENV = 'prod';

    const helloPrompt = 'Say hello';
    const byePrompt = 'Say bye';

    // Create prompt file
    fs.writeFileSync(__dirname + '/prompts/example.prompt', helloPrompt);

    let prompt = ai.prompt('example');
    let result = await prompt(registry, {
      model: 'echo',
    });
    assert.equal(result.text, helloPrompt);

    // Create new prompt file
    fs.writeFileSync(__dirname + '/prompts/example.prompt', byePrompt);

    prompt = ai.prompt('example');
    result = await prompt(registry, {
      model: 'echo',
    });
    assert.equal(result.text, helloPrompt);
  });

  it('Should reload prompt on every invocation if GENKIT_ENV="dev"', async () => {
    process.env.GENKIT_ENV = 'dev';

    const helloPrompt = 'Say hello';
    const byePrompt = 'Say bye';

    // Create prompt file
    fs.writeFileSync(__dirname + '/prompts/example.prompt', helloPrompt);

    let prompt = ai.prompt('example');
    let result = await prompt(registry, {
      model: 'echo',
    });
    assert.equal(result.text, helloPrompt);

    // Create new prompt file
    fs.writeFileSync(__dirname + '/prompts/example.prompt', byePrompt);

    prompt = ai.prompt('example');
    result = await prompt(registry, {
      model: 'echo',
    });
    assert.equal(result.text, byePrompt);

    // Test definePrompt
    prompt = ai.definePrompt({ name: 'hi' }, 'hi {{ name }}');
    result = await prompt(
      {
        name: 'hi',
      },
      {
        model: 'echo',
      }
    );
    assert.equal(result.text, 'hi hi');
  });

  it('Should be able to pick up prompt defined in code in dev mode', async () => {
    process.env.GENKIT_ENV = 'dev';

    ai.definePrompt({ name: 'hi' }, 'hi {{ name }}');
    const result = ai.prompt('hi');

    const response = await result(
      {
        name: 'hi',
      },
      {
        model: 'echo',
      }
    );

    assert.equal(response.text, 'hi hi');
  });

  it('Should be able to pick up a (functional) prompt defined in code in prod mode', async () => {
    process.env.GENKIT_ENV = 'prod';

    ai.definePrompt({ name: 'hi' }, 'hi {{ name }}');
    const result = ai.prompt('hi');

    const response = await result(
      {
        name: 'hi',
      },
      {
        model: 'echo',
      }
    );

    assert.equal(response.text, 'hi hi');
  });
});
