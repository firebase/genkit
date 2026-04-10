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
import { toGenkitMessages, type UIMessage } from '../src/convert.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function msg(
  role: UIMessage['role'],
  parts: UIMessage['parts'],
  content?: string
): UIMessage {
  return { id: 'x', role, parts, content };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('toGenkitMessages', () => {
  it('converts plain text user message', () => {
    const result = toGenkitMessages([
      msg('user', [{ type: 'text', text: 'Hello' }]),
    ]);
    assert.equal(result.length, 1);
    assert.equal(result[0].role, 'user');
    assert.deepEqual(result[0].content, [{ text: 'Hello' }]);
  });

  it('falls back to legacy content string', () => {
    const result = toGenkitMessages([msg('user', [], 'Fallback')]);
    assert.equal(result[0].role, 'user');
    assert.deepEqual(result[0].content, [{ text: 'Fallback' }]);
  });

  it('converts assistant text → model role', () => {
    const result = toGenkitMessages([
      msg('assistant', [{ type: 'text', text: 'Hi there' }]),
    ]);
    assert.equal(result[0].role, 'model');
    assert.deepEqual(result[0].content, [{ text: 'Hi there' }]);
  });

  it('converts file attachment → media part', () => {
    const result = toGenkitMessages([
      msg('user', [
        { type: 'text', text: 'What is this?' },
        {
          type: 'file',
          url: 'data:image/png;base64,abc',
          mediaType: 'image/png',
        } as any,
      ]),
    ]);
    assert.deepEqual(result[0].content, [
      { text: 'What is this?' },
      { media: { url: 'data:image/png;base64,abc', contentType: 'image/png' } },
    ]);
  });

  it('converts tool-invocation (state: call) → toolRequest only', () => {
    const result = toGenkitMessages([
      msg('assistant', [
        {
          type: 'tool-invocation',
          toolInvocation: {
            toolCallId: 'tc1',
            toolName: 'search',
            state: 'call',
            args: { q: 'genkit' },
          },
        } as any,
      ]),
    ]);
    assert.equal(result.length, 1);
    assert.equal(result[0].role, 'model');
    assert.deepEqual(result[0].content, [
      { toolRequest: { ref: 'tc1', name: 'search', input: { q: 'genkit' } } },
    ]);
  });

  it('converts tool-invocation (state: result) → model + tool messages', () => {
    const result = toGenkitMessages([
      msg('assistant', [
        {
          type: 'tool-invocation',
          toolInvocation: {
            toolCallId: 'tc1',
            toolName: 'search',
            state: 'result',
            args: { q: 'genkit' },
            result: { hits: 5 },
          },
        } as any,
      ]),
    ]);
    assert.equal(result.length, 2);
    assert.equal(result[0].role, 'model');
    assert.deepEqual(result[0].content, [
      { toolRequest: { ref: 'tc1', name: 'search', input: { q: 'genkit' } } },
    ]);
    assert.equal(result[1].role, 'tool');
    assert.deepEqual(result[1].content, [
      { toolResponse: { ref: 'tc1', name: 'search', output: { hits: 5 } } },
    ]);
  });

  it('passes system messages through', () => {
    const result = toGenkitMessages([
      msg('system', [{ type: 'text', text: 'Be helpful.' }]),
    ]);
    assert.equal(result[0].role, 'system');
    assert.deepEqual(result[0].content, [{ text: 'Be helpful.' }]);
  });

  it('preserves message order across mixed conversation', () => {
    const result = toGenkitMessages([
      msg('system', [{ type: 'text', text: 'sys' }]),
      msg('user', [{ type: 'text', text: 'Q' }]),
      msg('assistant', [{ type: 'text', text: 'A' }]),
    ]);
    assert.deepEqual(
      result.map((m) => m.role),
      ['system', 'user', 'model']
    );
  });

  it('throws on legacy tool role', () => {
    assert.throws(
      () => toGenkitMessages([msg('tool', [])]),
      /UIMessage with role 'tool' is not supported/
    );
  });

  it('handles assistant with text + tool-invocation result → 3 messages', () => {
    const result = toGenkitMessages([
      msg('assistant', [
        { type: 'text', text: 'Let me check...' },
        {
          type: 'tool-invocation',
          toolInvocation: {
            toolCallId: 'tc2',
            toolName: 'calc',
            state: 'result',
            args: { expr: '2+2' },
            result: 4,
          },
        } as any,
      ]),
    ]);
    // model message (text + toolRequest) + tool message (toolResponse)
    assert.equal(result.length, 2);
    assert.equal(result[0].role, 'model');
    assert.equal(result[0].content.length, 2);
    assert.equal(result[1].role, 'tool');
  });
});
