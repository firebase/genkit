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

import { z } from '@genkit-ai/core';
import { Registry } from '@genkit-ai/core/registry';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { configureFormats, resolveFormat } from '../../src/formats/index.js';

describe('formats', () => {
  let registry: Registry;

  beforeEach(() => {
    registry = new Registry();
    configureFormats(registry);
  });

  it('defaults to json when there is a schema present', async () => {
    assert.deepEqual(
      (await resolveFormat(registry, { schema: z.object({}) }))?.config,
      {
        constrained: true,
        contentType: 'application/json',
        defaultInstructions: false,
        format: 'json',
      }
    );
  });

  it('defaults to json when there is a jsonSchema present', async () => {
    assert.deepEqual(
      (await resolveFormat(registry, { jsonSchema: {} }))?.config,
      {
        constrained: true,
        contentType: 'application/json',
        defaultInstructions: false,
        format: 'json',
      }
    );
  });
});
