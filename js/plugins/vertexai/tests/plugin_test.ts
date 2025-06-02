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

import * as assert from 'assert';
import { genkit } from 'genkit';
import type { ModelInfo } from 'genkit/model';
import { describe, it } from 'node:test';
import { __setFakeDerivedParams } from '../src/common/index.js';
import { GENERIC_GEMINI_MODEL, gemini } from '../src/gemini.js';
import vertexAI, { gemini15Flash, gemini15Pro } from '../src/index.js';

describe('plugin', () => {
  __setFakeDerivedParams({
    projectId: 'test',
    location: 'us-central1',
  });

  it('should init the plugin without requiring the api key', async () => {
    const ai = genkit({
      plugins: [vertexAI()],
    });

    assert.ok(ai);
  });

  it('should pre-register a few flagship models', async () => {
    const ai = genkit({
      plugins: [vertexAI()],
    });

    assert.ok(await ai.registry.lookupAction(`/model/${gemini15Flash.name}`));
    assert.ok(await ai.registry.lookupAction(`/model/${gemini15Pro.name}`));
  });

  it('allow referencing models using `gemini` helper', async () => {
    const ai = genkit({
      plugins: [vertexAI()],
    });

    const pro = await ai.registry.lookupAction(
      `/model/${gemini('gemini-1.5-pro').name}`
    );
    assert.ok(pro);
    assert.strictEqual(pro.__action.name, 'vertexai/gemini-1.5-pro');
    const flash = await ai.registry.lookupAction(
      `/model/${gemini('gemini-1.5-flash').name}`
    );
    assert.ok(flash);
    assert.strictEqual(flash.__action.name, 'vertexai/gemini-1.5-flash');
  });

  it('references dynamic models', async () => {
    const ai = genkit({
      plugins: [vertexAI({ location: 'us-central1' })],
    });
    const giraffeRef = gemini('gemini-4.5-giraffe');
    assert.strictEqual(giraffeRef.name, 'vertexai/gemini-4.5-giraffe');
    const giraffe = await ai.registry.lookupAction(`/model/${giraffeRef.name}`);
    assert.ok(giraffe);
    assert.strictEqual(giraffe.__action.name, 'vertexai/gemini-4.5-giraffe');
    assertEqualModelInfo(
      giraffe.__action.metadata?.model,
      'Vertex AI - gemini-4.5-giraffe',
      GENERIC_GEMINI_MODEL.info! // <---- generic model fallback
    );
  });

  it('references pre-registered models', async () => {
    const flash002Ref = gemini('gemini-1.5-flash-002');
    const ai = genkit({
      plugins: [
        vertexAI({
          location: 'us-central1',
          models: ['gemini-1.5-pro-002', flash002Ref, 'gemini-4.0-banana'],
        }),
      ],
    });

    const pro002Ref = gemini('gemini-1.5-pro-002');
    assert.strictEqual(pro002Ref.name, 'vertexai/gemini-1.5-pro-002');
    assertEqualModelInfo(
      pro002Ref.info!,
      'Vertex AI - gemini-1.5-pro-002',
      gemini15Pro.info!
    );
    const pro002 = await ai.registry.lookupAction(`/model/${pro002Ref.name}`);
    assert.ok(pro002);
    assert.strictEqual(pro002.__action.name, 'vertexai/gemini-1.5-pro-002');
    assertEqualModelInfo(
      pro002.__action.metadata?.model,
      'Vertex AI - gemini-1.5-pro-002',
      gemini15Pro.info!
    );

    assert.strictEqual(flash002Ref.name, 'vertexai/gemini-1.5-flash-002');
    assertEqualModelInfo(
      flash002Ref.info!,
      'Vertex AI - gemini-1.5-flash-002',
      gemini15Flash.info!
    );
    const flash002 = await ai.registry.lookupAction(
      `/model/${flash002Ref.name}`
    );
    assert.ok(flash002);
    assert.strictEqual(flash002.__action.name, 'vertexai/gemini-1.5-flash-002');
    assertEqualModelInfo(
      flash002.__action.metadata?.model,
      'Vertex AI - gemini-1.5-flash-002',
      gemini15Flash.info!
    );

    const bananaRef = gemini('gemini-4.0-banana');
    assert.strictEqual(bananaRef.name, 'vertexai/gemini-4.0-banana');
    assertEqualModelInfo(
      bananaRef.info!,
      'Vertex AI - gemini-4.0-banana',
      GENERIC_GEMINI_MODEL.info! // <---- generic model fallback
    );
    const banana = await ai.registry.lookupAction(`/model/${bananaRef.name}`);
    assert.ok(banana);
    assert.strictEqual(banana.__action.name, 'vertexai/gemini-4.0-banana');
    assertEqualModelInfo(
      banana.__action.metadata?.model,
      'Vertex AI - gemini-4.0-banana',
      GENERIC_GEMINI_MODEL.info! // <---- generic model fallback
    );
  });
});

function assertEqualModelInfo(
  modelAction: ModelInfo,
  expectedLabel: string,
  expectedInfo: ModelInfo
) {
  assert.strictEqual(modelAction.label, expectedLabel);
  assert.deepStrictEqual(modelAction.supports, expectedInfo.supports);
  assert.deepStrictEqual(modelAction.versions, expectedInfo.versions);
}
