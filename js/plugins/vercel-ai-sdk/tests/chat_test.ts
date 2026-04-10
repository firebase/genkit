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
  it('ends with [DONE]', async () => {
    const events = await parseSSE(
      await chatHandler(fakeFlow(['hi']))(makeRequest([userMsg]))
    );
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
  it('handles plain string chunks (backward-compat)', async () => {
    const events = await parseSSE(
      await chatHandler(fakeFlow(['Hello', ', ', 'world!']))(
        makeRequest([userMsg])
      )
    );
    assert.equal(eventsOfType(events, 'text-start').length, 1);
    assert.deepEqual(
      (eventsOfType(events, 'text-delta') as any[]).map((d) => d.delta),
      ['Hello', ', ', 'world!']
    );
    assert.equal(eventsOfType(events, 'text-end').length, 1);
  });

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

  it('skips empty string chunks', async () => {
    const events = await parseSSE(
      await chatHandler(fakeFlow(['', 'hi', '']))(makeRequest([userMsg]))
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

  it('emits no finish event when flow returns plain string (no structured output)', async () => {
    const flow = fakeFlow(
      [{ type: 'text', delta: 'hi' } as StreamChunk],
      'plain string output'
    );
    const events = await parseSSE(
      await chatHandler(flow)(makeRequest([userMsg]))
    );
    // No finish chunk — createUIMessageStream only emits what we write
    assert.equal(eventsOfType(events, 'finish').length, 0);
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
// Response format
// ---------------------------------------------------------------------------
