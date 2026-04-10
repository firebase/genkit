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

import assert from 'node:assert';
import { describe, it } from 'node:test';
import { toStreamChunks } from '../src/generate.js';

function fakeChunk({
  text = '',
  reasoning = '',
  toolRequests = [] as any[],
} = {}) {
  return {
    text,
    reasoning,
    toolRequests,
  } as any;
}

describe('toStreamChunks', () => {
  it('returns empty array for empty chunk', () => {
    assert.deepEqual(toStreamChunks(fakeChunk()), []);
  });

  it('maps text to a text chunk', () => {
    const result = toStreamChunks(fakeChunk({ text: 'hello' }));
    assert.deepEqual(result, [{ type: 'text', delta: 'hello' }]);
  });

  it('maps reasoning before text', () => {
    const result = toStreamChunks(fakeChunk({ reasoning: 'hmm', text: 'ok' }));
    assert.equal(result[0].type, 'reasoning');
    assert.equal(result[1].type, 'text');
  });

  it('maps tool requests using ref as toolCallId', () => {
    const result = toStreamChunks(
      fakeChunk({
        toolRequests: [
          { toolRequest: { ref: 'call-1', name: 'search', input: { q: 'genkit' } } },
        ],
      })
    );
    assert.deepEqual(result, [
      { type: 'tool-request', toolCallId: 'call-1', toolName: 'search', input: { q: 'genkit' } },
    ]);
  });

  it('falls back to name when ref is missing', () => {
    const result = toStreamChunks(
      fakeChunk({
        toolRequests: [{ toolRequest: { name: 'search', input: {} } }],
      })
    );
    assert.equal((result[0] as any).toolCallId, 'search');
  });

  it('handles multiple tool requests', () => {
    const result = toStreamChunks(
      fakeChunk({
        toolRequests: [
          { toolRequest: { ref: 'c1', name: 'a', input: {} } },
          { toolRequest: { ref: 'c2', name: 'b', input: {} } },
        ],
      })
    );
    assert.equal(result.length, 2);
    assert.equal((result[0] as any).toolCallId, 'c1');
    assert.equal((result[1] as any).toolCallId, 'c2');
  });
});
