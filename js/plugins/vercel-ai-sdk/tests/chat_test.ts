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
import { chatHandler } from '../src/chat.js';
import { type UIMessage } from '../src/convert.js';
import { type StreamChunk } from '../src/schema.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fakeFlow(chunks: (string | StreamChunk)[], finalOutput?: unknown) {
  return {
    stream(_input: unknown, _opts?: unknown) {
      return {
        stream: (async function* () {
          for (const c of chunks) yield c;
        })(),
        output: Promise.resolve(finalOutput ?? ''),
      };
    },
  } as any;
}

async function parseSSE(res: Response): Promise<Array<object | string>> {
  const text = await res.text();
  return text
    .split('\n')
    .filter((l) => l.startsWith('data: '))
    .map((l) => {
      const payload = l.slice('data: '.length);
      return payload === '[DONE]' ? '[DONE]' : JSON.parse(payload);
    });
}

function eventsOfType(events: Array<object | string>, type: string) {
  return events.filter(
    (e) => typeof e === 'object' && (e as any).type === type
  );
}

const userMsg: UIMessage = {
  id: '1',
  role: 'user',
  parts: [{ type: 'text', text: 'Hi' }],
};

function makeRequest(
  messages: UIMessage[],
  extra: Record<string, unknown> = {}
) {
  return new Request('http://localhost/api/chat', {
    method: 'POST',
    body: JSON.stringify({ messages, ...extra }),
  });
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

describe('chatHandler — lifecycle events', () => {
  it('starts with a start event and ends with [DONE]', async () => {
    const events = await parseSSE(
      await chatHandler(fakeFlow(['hi']))(makeRequest([userMsg]))
    );
    assert.equal((events[0] as any).type, 'start');
    assert.equal(events[events.length - 1], '[DONE]');
  });

  it('returns 200 with correct headers', async () => {
    const res = await chatHandler(fakeFlow([]))(makeRequest([userMsg]));
    assert.equal(res.status, 200);
    assert.equal(res.headers.get('Content-Type'), 'text/event-stream');
    assert.equal(res.headers.get('X-Vercel-AI-UI-Message-Stream'), 'v1');
    assert.equal(res.headers.get('X-Accel-Buffering'), 'no');
  });
});

// ---------------------------------------------------------------------------
// Text streaming
// ---------------------------------------------------------------------------

describe('chatHandler — text streaming', () => {
  it('handles {type:text} chunks', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          { type: 'text', delta: 'Hi' } as StreamChunk,
          { type: 'text', delta: '!' } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    assert.equal(eventsOfType(events, 'text-start').length, 1);
    assert.equal(eventsOfType(events, 'text-delta').length, 2);
    assert.equal(eventsOfType(events, 'text-end').length, 1);
  });

  it('skips empty text delta chunks', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          { type: 'text', delta: '' } as StreamChunk,
          { type: 'text', delta: 'hi' } as StreamChunk,
          { type: 'text', delta: '' } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    assert.equal((eventsOfType(events, 'text-delta') as any[]).length, 1);
  });
});

// ---------------------------------------------------------------------------
// Reasoning
// ---------------------------------------------------------------------------

describe('chatHandler — reasoning chunks', () => {
  it('emits reasoning-start / reasoning-delta / reasoning-end', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          { type: 'reasoning', delta: 'hmm...' } as StreamChunk,
          { type: 'text', delta: 'Answer' } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    assert.equal(eventsOfType(events, 'reasoning-start').length, 1);
    assert.equal(eventsOfType(events, 'reasoning-delta').length, 1);
    assert.equal(eventsOfType(events, 'reasoning-end').length, 1);
    assert.equal(eventsOfType(events, 'text-start').length, 1);
  });
});

// ---------------------------------------------------------------------------
// Tool chunks
// ---------------------------------------------------------------------------

describe('chatHandler — tool chunks', () => {
  it('emits tool-input-start + tool-input-delta', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'tool-request',
            toolCallId: 'tc1',
            toolName: 'search',
            inputDelta: '{"q":',
          } as StreamChunk,
          {
            type: 'tool-request',
            toolCallId: 'tc1',
            toolName: 'search',
            inputDelta: '"hi"}',
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    assert.equal(eventsOfType(events, 'tool-input-start').length, 1);
    assert.equal(eventsOfType(events, 'tool-input-delta').length, 2);
  });

  it('emits tool-input-available for full input', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'tool-request',
            toolCallId: 'tc1',
            toolName: 'search',
            input: { q: 'genkit' },
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    assert.equal(eventsOfType(events, 'tool-input-available').length, 1);
    assert.deepEqual(
      (eventsOfType(events, 'tool-input-available')[0] as any).input,
      { q: 'genkit' }
    );
  });

  it('emits tool-output-available for tool-result', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'tool-result',
            toolCallId: 'tc1',
            output: { hits: 3 },
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    assert.deepEqual(
      (eventsOfType(events, 'tool-output-available')[0] as any).output,
      { hits: 3 }
    );
  });
});

// ---------------------------------------------------------------------------
// Tool errors and approval
// ---------------------------------------------------------------------------

describe('chatHandler — tool errors and approval', () => {
  it('emits tool-input-error with errorText', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'tool-input-error',
            toolCallId: 'tc1',
            toolName: 'search',
            input: '{"bad',
            errorText: 'Invalid JSON',
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    // Should emit tool-input-start then tool-input-error
    assert.equal(eventsOfType(events, 'tool-input-start').length, 1);
    const e = eventsOfType(events, 'tool-input-error')[0] as any;
    assert.ok(e);
    assert.equal(e.toolCallId, 'tc1');
    assert.equal(e.toolName, 'search');
    assert.equal(e.errorText, 'Invalid JSON');
  });

  it('emits tool-output-error with errorText', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'tool-output-error',
            toolCallId: 'tc1',
            errorText: 'Tool execution failed',
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    const e = eventsOfType(events, 'tool-output-error')[0] as any;
    assert.ok(e);
    assert.equal(e.toolCallId, 'tc1');
    assert.equal(e.errorText, 'Tool execution failed');
  });

  it('emits tool-output-denied', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'tool-output-denied',
            toolCallId: 'tc1',
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    const e = eventsOfType(events, 'tool-output-denied')[0] as any;
    assert.ok(e);
    assert.equal(e.toolCallId, 'tc1');
  });

  it('emits tool-approval-request', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'tool-approval-request',
            approvalId: 'a1',
            toolCallId: 'tc1',
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    const e = eventsOfType(events, 'tool-approval-request')[0] as any;
    assert.ok(e);
    assert.equal(e.approvalId, 'a1');
    assert.equal(e.toolCallId, 'tc1');
  });
});

// ---------------------------------------------------------------------------
// File output
// ---------------------------------------------------------------------------

describe('chatHandler — file output', () => {
  it('emits file events with url and mediaType', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'file',
            url: 'data:image/png;base64,abc',
            mediaType: 'image/png',
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    const f = eventsOfType(events, 'file')[0] as any;
    assert.equal(f.url, 'data:image/png;base64,abc');
    assert.equal(f.mediaType, 'image/png');
    // filename is not part of the AI SDK wire format (strictObject schema)
    assert.ok(!('filename' in f));
  });
});

// ---------------------------------------------------------------------------
// Source citations
// ---------------------------------------------------------------------------

describe('chatHandler — source citations', () => {
  it('emits source-url event', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'source-url',
            sourceId: 's1',
            url: 'https://genkit.dev',
            title: 'Genkit Docs',
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    const e = eventsOfType(events, 'source-url')[0] as any;
    assert.equal(e.sourceId, 's1');
    assert.equal(e.url, 'https://genkit.dev');
    assert.equal(e.title, 'Genkit Docs');
  });

  it('emits source-document event', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'source-document',
            sourceId: 's2',
            mediaType: 'application/pdf',
            title: 'Report',
            filename: 'report.pdf',
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    const e = eventsOfType(events, 'source-document')[0] as any;
    assert.equal(e.sourceId, 's2');
    assert.equal(e.mediaType, 'application/pdf');
    assert.equal(e.filename, 'report.pdf');
  });
});

// ---------------------------------------------------------------------------
// Custom data
// ---------------------------------------------------------------------------

describe('chatHandler — custom data', () => {
  it('emits data-* events', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          {
            type: 'data',
            id: 'usage',
            value: { inputTokens: 10 },
          } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    const e = events.find(
      (e) => typeof e === 'object' && (e as any).type === 'data-usage'
    ) as any;
    assert.ok(e);
    assert.deepEqual(e.data, { inputTokens: 10 });
  });
});

// ---------------------------------------------------------------------------
// Step markers
// ---------------------------------------------------------------------------

describe('chatHandler — step markers', () => {
  it('emits start-step and finish-step', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          { type: 'step-start' } as StreamChunk,
          { type: 'text', delta: 'hi' } as StreamChunk,
          { type: 'step-end' } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    assert.equal(eventsOfType(events, 'start-step').length, 1);
    assert.equal(eventsOfType(events, 'finish-step').length, 1);
  });

  it('closes open text block at step-end', async () => {
    const events = await parseSSE(
      await chatHandler(
        fakeFlow([
          { type: 'text', delta: 'A' } as StreamChunk,
          { type: 'step-end' } as StreamChunk,
          { type: 'text', delta: 'B' } as StreamChunk,
        ])
      )(makeRequest([userMsg]))
    );
    assert.equal(eventsOfType(events, 'text-start').length, 2);
    assert.equal(eventsOfType(events, 'text-end').length, 2);
  });
});

// ---------------------------------------------------------------------------
// finish-message with usage data
// ---------------------------------------------------------------------------

describe('chatHandler — finish data', () => {
  it('emits finish with finishReason and usage in messageMetadata', async () => {
    const flow = fakeFlow([{ type: 'text', delta: 'hi' } as StreamChunk], {
      finishReason: 'stop',
      usage: { inputTokens: 5, outputTokens: 10 },
    });
    const events = await parseSSE(
      await chatHandler(flow)(makeRequest([userMsg]))
    );
    const f = eventsOfType(events, 'finish')[0] as any;
    assert.equal(f.finishReason, 'stop');
    assert.deepEqual(f.messageMetadata?.usage, {
      inputTokens: 5,
      outputTokens: 10,
    });
  });

  it('emits bare finish event when flow returns plain string (no structured output)', async () => {
    const flow = fakeFlow(
      [{ type: 'text', delta: 'hi' } as StreamChunk],
      'plain string output'
    );
    const events = await parseSSE(
      await chatHandler(flow)(makeRequest([userMsg]))
    );
    const finish = eventsOfType(events, 'finish');
    assert.equal(finish.length, 1);
    // No finishReason or usage — just the type
    assert.equal((finish[0] as any).finishReason, undefined);
    assert.equal((finish[0] as any).messageMetadata, undefined);
  });
});

// ---------------------------------------------------------------------------
// Extra body fields
// ---------------------------------------------------------------------------

describe('chatHandler — body passthrough', () => {
  it('passes extra request fields as input.body to the flow', async () => {
    let capturedInput: any;
    const flow = {
      stream(input: unknown) {
        capturedInput = input;
        return {
          stream: (async function* () {})(),
          output: Promise.resolve(''),
        };
      },
    } as any;

    const res = await chatHandler(flow)(
      makeRequest([userMsg], { sessionId: 'xyz', persona: 'helpful' })
    );
    await res.text(); // drain stream so flow.stream() runs before asserting
    assert.deepEqual(capturedInput.body, {
      sessionId: 'xyz',
      persona: 'helpful',
    });
  });

  it('does not include body in input when no extra fields', async () => {
    let capturedInput: any;
    const flow = {
      stream(input: unknown) {
        capturedInput = input;
        return {
          stream: (async function* () {})(),
          output: Promise.resolve(''),
        };
      },
    } as any;

    const res2 = await chatHandler(flow)(makeRequest([userMsg]));
    await res2.text(); // drain
    assert.ok(!('body' in capturedInput));
  });
});

// ---------------------------------------------------------------------------
// Request validation
// ---------------------------------------------------------------------------

describe('chatHandler — request validation', () => {
  it('returns 400 for malformed JSON', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: 'not json',
    });
    const res = await chatHandler(fakeFlow([]))(req);
    assert.equal(res.status, 400);
  });

  it('returns 400 when messages is missing', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    const res = await chatHandler(fakeFlow([]))(req);
    assert.equal(res.status, 400);
  });

  it('returns 400 when messages is not an array', async () => {
    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({ messages: 'oops' }),
    });
    const res = await chatHandler(fakeFlow([]))(req);
    assert.equal(res.status, 400);
  });
});

// ---------------------------------------------------------------------------
// Context provider (auth)
// ---------------------------------------------------------------------------

describe('chatHandler — contextProvider', () => {
  it('forwards derived context to the flow', async () => {
    let capturedOpts: any;
    const flow = {
      stream(_input: unknown, opts: unknown) {
        capturedOpts = opts;
        return {
          stream: (async function* () {})(),
          output: Promise.resolve(''),
        };
      },
    } as any;

    const res = await chatHandler(flow, {
      contextProvider: async () => ({ userId: 'u1' }),
    })(makeRequest([userMsg]));
    await res.text(); // drain

    assert.deepEqual(capturedOpts.context, { userId: 'u1' });
  });

  it('returns 401 when contextProvider throws', async () => {
    const err = Object.assign(new Error('Unauthorized'), { status: 401 });
    const res = await chatHandler(fakeFlow([]), {
      contextProvider: async () => {
        throw err;
      },
    })(makeRequest([userMsg]));
    assert.equal(res.status, 401);
  });
});

// ---------------------------------------------------------------------------
// Abort signal
// ---------------------------------------------------------------------------

describe('chatHandler — abort signal', () => {
  it('passes req.signal to flow.stream()', async () => {
    let capturedOpts: any;
    const flow = {
      stream(_input: unknown, opts: unknown) {
        capturedOpts = opts;
        return {
          stream: (async function* () {})(),
          output: Promise.resolve(''),
        };
      },
    } as any;

    const req = new Request('http://localhost/api/chat', {
      method: 'POST',
      body: JSON.stringify({ messages: [userMsg] }),
    });

    const res = await chatHandler(flow)(req);
    await res.text(); // drain
    assert.ok(capturedOpts.abortSignal instanceof AbortSignal);
  });
});

// ---------------------------------------------------------------------------
// onError / mid-stream errors
// ---------------------------------------------------------------------------

describe('chatHandler — onError', () => {
  it('surfaces custom onError string in the error SSE event', async () => {
    const throwingFlow = {
      stream(_input: unknown, _opts?: unknown) {
        return {
          stream: (async function* () {
            yield { type: 'text', delta: 'partial' } as StreamChunk;
            throw new Error('boom');
          })(),
          output: Promise.resolve(undefined),
        };
      },
    } as any;

    const events = await parseSSE(
      await chatHandler(throwingFlow, {
        onError: () => 'something went wrong',
      })(makeRequest([userMsg]))
    );
    const errEvent = events.find(
      (e) => typeof e === 'object' && (e as any).type === 'error'
    ) as any;
    assert.ok(errEvent, 'expected an error event');
    assert.equal(errEvent.errorText, 'something went wrong');
  });

  it('uses default message when onError returns void', async () => {
    const throwingFlow = {
      stream(_input: unknown, _opts?: unknown) {
        return {
          stream: (async function* () {
            throw new Error('boom');
          })(),
          output: Promise.resolve(undefined),
        };
      },
    } as any;

    const events = await parseSSE(
      await chatHandler(throwingFlow, { onError: () => {} })(
        makeRequest([userMsg])
      )
    );
    const errEvent = events.find(
      (e) => typeof e === 'object' && (e as any).type === 'error'
    ) as any;
    assert.ok(errEvent);
    assert.equal(errEvent.errorText, 'An error occurred.');
  });
});

// ---------------------------------------------------------------------------
// finish-reason normalisation
// ---------------------------------------------------------------------------

describe('chatHandler — finish-reason normalisation', () => {
  it('omits finishReason from finish event when flow returns unknown reason', async () => {
    const flow = fakeFlow([], {
      finishReason: 'cancelled', // not a valid AI SDK finish reason
      usage: {},
    });
    const events = await parseSSE(
      await chatHandler(flow)(makeRequest([userMsg]))
    );
    const f = eventsOfType(events, 'finish')[0] as any;
    assert.ok(f, 'expected finish event');
    assert.ok(!('finishReason' in f), 'finishReason should be omitted');
  });
});

// ---------------------------------------------------------------------------
// Response format
// ---------------------------------------------------------------------------
