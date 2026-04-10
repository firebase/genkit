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
import {
  AiSdkChunkSchema,
  ChatFlowOutputSchema,
  MessagesSchema,
} from '../src/schema.js';

// ---------------------------------------------------------------------------
// MessagesSchema
// ---------------------------------------------------------------------------

describe('MessagesSchema', () => {
  it('accepts text parts (Genkit-native format)', () => {
    assert.ok(
      MessagesSchema.safeParse({
        messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
      }).success
    );
  });

  it('accepts array of text parts for multiple messages', () => {
    assert.ok(
      MessagesSchema.safeParse({
        messages: [
          { role: 'user', content: [{ text: 'Hi' }] },
          { role: 'model', content: [{ text: 'Hello!' }] },
        ],
      }).success
    );
  });

  it('accepts media parts', () => {
    assert.ok(
      MessagesSchema.safeParse({
        messages: [
          {
            role: 'user',
            content: [
              { text: 'What is this?' },
              {
                media: {
                  url: 'data:image/png;base64,abc',
                  contentType: 'image/png',
                },
              },
            ],
          },
        ],
      }).success
    );
  });

  it('accepts toolRequest and toolResponse parts', () => {
    assert.ok(
      MessagesSchema.safeParse({
        messages: [
          {
            role: 'model',
            content: [
              {
                toolRequest: { name: 'search', ref: 'tc1', input: { q: 'hi' } },
              },
            ],
          },
          {
            role: 'tool',
            content: [
              {
                toolResponse: {
                  name: 'search',
                  ref: 'tc1',
                  output: { result: 'ok' },
                },
              },
            ],
          },
        ],
      }).success
    );
  });

  it('accepts all four roles', () => {
    assert.ok(
      MessagesSchema.safeParse({
        messages: [
          { role: 'system', content: [{ text: 'sys' }] },
          { role: 'user', content: [{ text: 'hi' }] },
          { role: 'model', content: [{ text: 'hello' }] },
          {
            role: 'tool',
            content: [{ toolResponse: { name: 'f', ref: 'x', output: {} } }],
          },
        ],
      }).success
    );
  });

  it('accepts optional body field with arbitrary fields', () => {
    const r = MessagesSchema.safeParse({
      messages: [{ role: 'user', content: [{ text: 'hi' }] }],
      body: { sessionId: 'abc', persona: 'helpful', count: 3 },
    });
    assert.ok(r.success);
    assert.deepEqual(r.data!.body, {
      sessionId: 'abc',
      persona: 'helpful',
      count: 3,
    });
  });

  it('body field is optional', () => {
    assert.ok(
      MessagesSchema.safeParse({
        messages: [{ role: 'user', content: [{ text: 'hi' }] }],
      }).success
    );
  });

  it('rejects unknown roles', () => {
    assert.ok(
      !MessagesSchema.safeParse({
        messages: [{ role: 'assistant', content: [{ text: 'hi' }] }],
      }).success
    );
  });
});

// ---------------------------------------------------------------------------
// AiSdkChunkSchema
// ---------------------------------------------------------------------------

describe('AiSdkChunkSchema', () => {
  it('accepts text chunk', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({ type: 'text', delta: 'Hello' }).success
    );
  });

  it('accepts reasoning chunk', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({ type: 'reasoning', delta: 'I think...' })
        .success
    );
  });

  it('accepts tool-request with inputDelta', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'tool-request',
        toolCallId: 'tc1',
        toolName: 'search',
        inputDelta: '{"q":',
      }).success
    );
  });

  it('accepts tool-request with full input', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'tool-request',
        toolCallId: 'tc1',
        toolName: 'search',
        input: { q: 'genkit' },
      }).success
    );
  });

  it('accepts tool-result', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'tool-result',
        toolCallId: 'tc1',
        output: { answer: 42 },
      }).success
    );
  });

  it('accepts file chunk', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'file',
        url: 'data:image/png;base64,abc',
        mediaType: 'image/png',
      }).success
    );
  });

  it('accepts file chunk with filename', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'file',
        url: 'https://example.com/img.png',
        mediaType: 'image/png',
        filename: 'img.png',
      }).success
    );
  });

  it('accepts source-url chunk', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'source-url',
        sourceId: 's1',
        url: 'https://example.com',
      }).success
    );
  });

  it('accepts source-url with title', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'source-url',
        sourceId: 's1',
        url: 'https://example.com',
        title: 'Example',
      }).success
    );
  });

  it('accepts source-document chunk', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'source-document',
        sourceId: 's2',
        mediaType: 'application/pdf',
        title: 'Report',
      }).success
    );
  });

  it('accepts source-document with filename', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'source-document',
        sourceId: 's2',
        mediaType: 'application/pdf',
        title: 'Report',
        filename: 'report.pdf',
      }).success
    );
  });

  it('accepts data chunk', () => {
    assert.ok(
      AiSdkChunkSchema.safeParse({
        type: 'data',
        id: 'usage',
        value: { inputTokens: 10 },
      }).success
    );
  });

  it('accepts step-start and step-end', () => {
    assert.ok(AiSdkChunkSchema.safeParse({ type: 'step-start' }).success);
    assert.ok(AiSdkChunkSchema.safeParse({ type: 'step-end' }).success);
  });

  it('rejects unknown type', () => {
    assert.ok(
      !AiSdkChunkSchema.safeParse({ type: 'unknown-future-type' }).success
    );
  });
});

// ---------------------------------------------------------------------------
// ChatFlowOutputSchema
// ---------------------------------------------------------------------------

describe('ChatFlowOutputSchema', () => {
  it('accepts finishReason and usage', () => {
    const r = ChatFlowOutputSchema.safeParse({
      finishReason: 'stop',
      usage: { inputTokens: 10, outputTokens: 20 },
    });
    assert.ok(r.success);
    assert.equal(r.data!.finishReason, 'stop');
    assert.deepEqual(r.data!.usage, { inputTokens: 10, outputTokens: 20 });
  });

  it('accepts partial output (only finishReason)', () => {
    assert.ok(
      ChatFlowOutputSchema.safeParse({ finishReason: 'length' }).success
    );
  });

  it('accepts empty object', () => {
    assert.ok(ChatFlowOutputSchema.safeParse({}).success);
  });

  it('rejects non-object output (plain string)', () => {
    assert.ok(!ChatFlowOutputSchema.safeParse('done').success);
  });
});
