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

import { defineModel } from '@genkit-ai/ai/model';
import { configureGenkit } from '@genkit-ai/core';
import { strict as assert } from 'assert';
import fs from 'fs';
import { beforeEach, describe, it, mock } from 'node:test';
import { z } from 'zod';
import { dotprompt, promptRef } from '../src/index';
defineModel({ name: 'echo', supports: { tools: true } }, async (input) => ({
  candidates: [{ index: 0, message: input.messages[0], finishReason: 'stop' }],
}));
const numberOfFixturePromptFiles = 3;
describe('e2e', () => {
  let numberOfCalls = 0;

  beforeEach(() => {
    numberOfCalls = 0;
    // Reinitialize the mock for each test
    readFileSyncMock = mock.method(fs, 'readFileSync', () => {
      numberOfCalls++;
      return 'mocked file content';
    });
  });

  it('Should use cached prompt if GENKIT_ENV!="dev"', async () => {
    assert.equal(numberOfCalls, 0);
    process.env.GENKIT_ENV = 'prod';

    configureGenkit({
      plugins: [
        dotprompt({
          dir: __dirname + '/fixtures',
        }),
      ],
    });

    assert.equal(numberOfCalls, 0);

    const ref = promptRef('example', { dir: __dirname + '/fixtures' });

    assert.equal(numberOfCalls, 0);

    const MySchema = z.object({
      subject: z.string(),
    });

    const result = await ref.generate<typeof MySchema>({
      input: { subject: 'test' },
      model: 'echo',
    });
    assert.equal(numberOfCalls, numberOfFixturePromptFiles);
  });

  it('Should reload prompt on every invocation if GENKIT_ENV="dev"', async () => {
    assert.equal(numberOfCalls, 0);
    process.env.GENKIT_ENV = 'dev';

    configureGenkit({
      plugins: [
        dotprompt({
          dir: __dirname + '/fixtures',
        }),
      ],
    });

    assert.equal(numberOfCalls, 0);

    const ref = promptRef('example', { dir: __dirname + '/fixtures' });

    assert.equal(numberOfCalls, 0);

    const MySchema = z.object({
      subject: z.string(),
    });

    const result = await ref.generate<typeof MySchema>({
      input: { subject: 'test' },
      model: 'echo',
    });
    assert.equal(numberOfCalls, numberOfFixturePromptFiles + 1);
  });

  it('Should reload prompt on every invocation if GENKIT_ENV="dev"', async () => {
    assert.equal(numberOfCalls, 0);
    process.env.GENKIT_ENV = 'dev';

    configureGenkit({
      plugins: [
        dotprompt({
          dir: __dirname + '/fixtures',
        }),
      ],
    });

    assert.equal(numberOfCalls, 0);

    const ref = promptRef('example', { dir: __dirname + '/fixtures' });
    const ref2 = promptRef('example2', { dir: __dirname + '/fixtures' });

    assert.equal(numberOfCalls, 0);

    const MySchema = z.object({
      subject: z.string(),
    });

    await ref.generate<typeof MySchema>({
      input: { subject: 'test' },
      model: 'echo',
    });

    await ref2.generate<typeof MySchema>({
      input: { subject: 'test' },
      model: 'echo',
    });

    assert.equal(numberOfCalls, numberOfFixturePromptFiles + 2);
  });

  it('Should reload prompt on every invocation if GENKIT_ENV="dev"', async () => {
    assert.equal(numberOfCalls, 0);
    process.env.GENKIT_ENV = 'dev';

    configureGenkit({
      plugins: [
        dotprompt({
          dir: __dirname + '/fixtures',
        }),
      ],
    });

    assert.equal(numberOfCalls, 0);

    const ref = promptRef('example', { dir: __dirname + '/fixtures' });
    const refToSamePrompt = promptRef('example', {
      dir: __dirname + '/fixtures',
    });

    assert.equal(numberOfCalls, 0);

    const MySchema = z.object({
      subject: z.string(),
    });

    await ref.generate<typeof MySchema>({
      input: { subject: 'test' },
      model: 'echo',
    });

    await refToSamePrompt.generate<typeof MySchema>({
      input: { subject: 'test' },
      model: 'echo',
    });

    assert.equal(numberOfCalls, numberOfFixturePromptFiles + 2);
  });
});
