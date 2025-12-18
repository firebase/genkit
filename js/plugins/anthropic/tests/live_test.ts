/**
 * Copyright 2025 Google LLC
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

/**
 * Live integration tests that call the real Anthropic API.
 * Only runs when ANTHROPIC_API_KEY environment variable is set.
 *
 * Run with: ANTHROPIC_API_KEY=your-key pnpm test:live
 */

import * as assert from 'assert';
import { genkit } from 'genkit';
import { describe, it } from 'node:test';
import { anthropic } from '../src/index.js';

const API_KEY = process.env.ANTHROPIC_API_KEY;

describe('Live Anthropic API Tests', { skip: !API_KEY }, () => {
  it('should work with short model name claude-3-5-haiku', async () => {
    const ai = genkit({
      plugins: [anthropic({ apiKey: API_KEY })],
    });

    const result = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      prompt: 'Say "hello" and nothing else.',
    });

    assert.ok(result.text.toLowerCase().includes('hello'));
  });

  it('should work with short model name claude-3-haiku', async () => {
    const ai = genkit({
      plugins: [anthropic({ apiKey: API_KEY })],
    });

    const result = await ai.generate({
      model: 'anthropic/claude-3-haiku',
      prompt: 'Say "hello" and nothing else.',
    });

    assert.ok(result.text.toLowerCase().includes('hello'));
  });

  it('should work with full versioned model name', async () => {
    const ai = genkit({
      plugins: [anthropic({ apiKey: API_KEY })],
    });

    const result = await ai.generate({
      model: 'anthropic/claude-3-5-haiku-20241022',
      prompt: 'Say "hello" and nothing else.',
    });

    assert.ok(result.text.toLowerCase().includes('hello'));
  });

  it('should work with anthropic.model() helper', async () => {
    const ai = genkit({
      plugins: [anthropic({ apiKey: API_KEY })],
    });

    const result = await ai.generate({
      model: anthropic.model('claude-3-5-haiku'),
      prompt: 'Say "hello" and nothing else.',
    });

    assert.ok(result.text.toLowerCase().includes('hello'));
  });
});
