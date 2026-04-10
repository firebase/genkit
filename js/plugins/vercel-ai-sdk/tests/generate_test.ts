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
import { toFlowOutput, toStreamChunks } from '../src/generate.js';

function fakeChunk({
  text = '',
  reasoning = '',
  content = [] as any[],
  toolRequests = [] as any[],
} = {}) {
  return { text, reasoning, content, toolRequests } as any;
}

function fakeResponse(opts: { finishReason?: string; usage?: any } = {}) {
  return { finishReason: opts.finishReason, usage: opts.usage ?? {} } as any;
}

describe('toStreamChunks', () => {
  it('returns empty array for empty chunk', () => {
    assert.deepEqual(toStreamChunks(fakeChunk()), []);
  });

  it('maps media parts to file chunks', () => {
    const result = toStreamChunks(
      fakeChunk({
        content: [
          {
            media: {
              url: 'data:image/png;base64,abc',
              contentType: 'image/png',
            },
          },
        ],
      })
    );
    assert.deepEqual(result, [
      {
        type: 'file',
        url: 'data:image/png;base64,abc',
        mediaType: 'image/png',
      },
    ]);
  });

  it('uses application/octet-stream when contentType is missing', () => {
    const result = toStreamChunks(
      fakeChunk({ content: [{ media: { url: 'data:image/png;base64,abc' } }] })
    );
    assert.equal((result[0] as any).mediaType, 'application/octet-stream');
  });

  it('maps multiple media parts', () => {
    const result = toStreamChunks(
      fakeChunk({
        content: [
          { media: { url: 'u1', contentType: 'image/png' } },
          { media: { url: 'u2', contentType: 'image/jpeg' } },
        ],
      })
    );
    assert.equal(result.length, 2);
    assert.equal((result[0] as any).url, 'u1');
    assert.equal((result[1] as any).url, 'u2');
  });

  it('ignores non-media content parts', () => {
    const result = toStreamChunks(
      fakeChunk({ content: [{ text: 'hi' }, { data: {} }], text: 'hi' })
    );
    assert.equal(result.filter((c) => c.type === 'file').length, 0);
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
          {
            toolRequest: {
              ref: 'call-1',
              name: 'search',
              input: { q: 'genkit' },
            },
          },
        ],
      })
    );
    assert.deepEqual(result, [
      {
        type: 'tool-request',
        toolCallId: 'call-1',
        toolName: 'search',
        input: { q: 'genkit' },
      },
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

  it('emits media before tool requests', () => {
    const result = toStreamChunks(
      fakeChunk({
        content: [{ media: { url: 'u1', contentType: 'image/png' } }],
        toolRequests: [{ toolRequest: { ref: 'c1', name: 'a', input: {} } }],
      })
    );
    assert.equal(result[0].type, 'file');
    assert.equal(result[1].type, 'tool-request');
  });
});

describe('toFlowOutput', () => {
  it('extracts finishReason and usage', () => {
    const result = toFlowOutput(
      fakeResponse({ finishReason: 'stop', usage: { inputTokens: 5 } })
    );
    assert.equal(result.finishReason, 'stop');
    assert.deepEqual(result.usage, { inputTokens: 5 });
  });

  it('handles undefined finishReason', () => {
    const result = toFlowOutput(fakeResponse({ finishReason: undefined }));
    assert.equal(result.finishReason, undefined);
  });

  it('returns empty usage object when usage is empty', () => {
    const result = toFlowOutput(fakeResponse({ usage: {} }));
    assert.deepEqual(result.usage, {});
  });
});
