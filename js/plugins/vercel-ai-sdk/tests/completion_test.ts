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
import { completionHandler } from '../src/completion.js';
import { type AiSdkChunk } from '../src/schema.js';

function fakeFlow(chunks: (string | AiSdkChunk)[], finalOutput?: unknown) {
  return {
    stream(_input: unknown, _opts?: unknown) {
      return {
        stream: (async function* () {
          for (const c of chunks) yield c;
        })(),
        output: Promise.resolve(
          finalOutput ?? chunks.filter((c) => typeof c === 'string').join('')
        ),
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

function makeReq(prompt: string) {
  return new Request('http://localhost/api/completion', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  });
}

describe('completionHandler — lifecycle', () => {
  it('emits text events and [DONE]', async () => {
    const events = await parseSSE(
      await completionHandler(fakeFlow(['Once', ' upon']))(
        makeReq('tell me a story')
      )
    );
    assert.equal(eventsOfType(events, 'text-start').length, 1);
    assert.equal(eventsOfType(events, 'text-delta').length, 2);
    assert.equal(eventsOfType(events, 'text-end').length, 1);
    assert.equal(events[events.length - 1], '[DONE]');
  });

  it('skips empty chunks', async () => {
    const events = await parseSSE(
      await completionHandler(fakeFlow(['', 'hello', '']))(makeReq('hi'))
    );
    assert.equal((eventsOfType(events, 'text-delta') as any[]).length, 1);
  });
});

describe('completionHandler — rich chunks (AiSdkChunkSchema)', () => {
  it('handles reasoning chunks', async () => {
    const events = await parseSSE(
      await completionHandler(
        fakeFlow([
          { type: 'reasoning', delta: 'thinking...' } as AiSdkChunk,
          { type: 'text', delta: 'answer' } as AiSdkChunk,
        ])
      )(makeReq('prompt'))
    );
    assert.equal(eventsOfType(events, 'reasoning-start').length, 1);
    assert.equal(eventsOfType(events, 'reasoning-delta').length, 1);
    assert.equal(eventsOfType(events, 'text-start').length, 1);
  });

  it('handles file chunks', async () => {
    const events = await parseSSE(
      await completionHandler(
        fakeFlow([
          {
            type: 'file',
            url: 'data:image/png;base64,abc',
            mediaType: 'image/png',
          } as AiSdkChunk,
        ])
      )(makeReq('prompt'))
    );
    assert.equal(eventsOfType(events, 'file').length, 1);
  });

  it('handles source-url chunks', async () => {
    const events = await parseSSE(
      await completionHandler(
        fakeFlow([
          {
            type: 'source-url',
            sourceId: 's1',
            url: 'https://genkit.dev',
          } as AiSdkChunk,
        ])
      )(makeReq('prompt'))
    );
    assert.equal(eventsOfType(events, 'source-url').length, 1);
  });
});

describe('completionHandler — finish data', () => {
  it('populates finish with finishReason from ChatFlowOutputSchema output', async () => {
    const flow = fakeFlow([], {
      finishReason: 'stop',
      usage: { inputTokens: 3 },
    });
    const events = await parseSSE(await completionHandler(flow)(makeReq('hi')));
    const f = eventsOfType(events, 'finish')[0] as any;
    assert.equal(f.finishReason, 'stop');
    assert.deepEqual(f.messageMetadata?.usage, { inputTokens: 3 });
  });
});

describe('completionHandler — request validation', () => {
  it('returns 400 for malformed JSON', async () => {
    const req = new Request('http://localhost/api/completion', {
      method: 'POST',
      body: 'bad',
    });
    const res = await completionHandler(fakeFlow([]))(req);
    assert.equal(res.status, 400);
  });

  it('returns 400 when prompt is missing', async () => {
    const req = new Request('http://localhost/api/completion', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    const res = await completionHandler(fakeFlow([]))(req);
    assert.equal(res.status, 400);
  });

  it('returns 400 when prompt is not a string', async () => {
    const req = new Request('http://localhost/api/completion', {
      method: 'POST',
      body: JSON.stringify({ prompt: 42 }),
    });
    const res = await completionHandler(fakeFlow([]))(req);
    assert.equal(res.status, 400);
  });
});

describe('completionHandler — contextProvider', () => {
  it('forwards context to the flow', async () => {
    let capturedOpts: any;
    const flow = {
      stream(_: unknown, opts: unknown) {
        capturedOpts = opts;
        return {
          stream: (async function* () {})(),
          output: Promise.resolve(''),
        };
      },
    } as any;
    const res = await completionHandler(flow, {
      contextProvider: async () => ({ userId: 'u1' }),
    })(makeReq('hi'));
    await res.text(); // drain
    assert.deepEqual(capturedOpts.context, { userId: 'u1' });
  });

  it('returns error status when contextProvider throws', async () => {
    const err = Object.assign(new Error('Forbidden'), { status: 403 });
    const res = await completionHandler(fakeFlow([]), {
      contextProvider: async () => {
        throw err;
      },
    })(makeReq('hi'));
    assert.equal(res.status, 403);
  });
});

describe('completionHandler — abort signal', () => {
  it('passes req.signal to flow.stream()', async () => {
    let capturedOpts: any;
    const flow = {
      stream(_: unknown, opts: unknown) {
        capturedOpts = opts;
        return {
          stream: (async function* () {})(),
          output: Promise.resolve(''),
        };
      },
    } as any;
    const res = await completionHandler(flow)(makeReq('hi'));
    await res.text(); // drain
    assert.ok(capturedOpts.abortSignal instanceof AbortSignal);
  });
});

describe('completionHandler — response format', () => {
  it('returns 200 with correct AI SDK headers', async () => {
    const res = await completionHandler(fakeFlow([]))(makeReq('hi'));
    assert.equal(res.status, 200);
    assert.equal(res.headers.get('Content-Type'), 'text/event-stream');
    assert.equal(res.headers.get('X-Vercel-AI-UI-Message-Stream'), 'v1');
    assert.equal(res.headers.get('X-Accel-Buffering'), 'no');
    await res.text(); // drain
  });
});

describe('completionHandler — streamProtocol: text', () => {
  it('returns text/plain with raw text chunks', async () => {
    const res = await completionHandler(fakeFlow(['Hello', ', ', 'world!']), {
      streamProtocol: 'text',
    })(makeReq('hi'));
    assert.equal(res.status, 200);
    assert.ok(res.headers.get('Content-Type')?.includes('text/plain'));
    assert.equal(await res.text(), 'Hello, world!');
  });

  it('extracts delta from typed text chunks', async () => {
    const res = await completionHandler(
      fakeFlow([
        { type: 'text', delta: 'Hi' } as AiSdkChunk,
        { type: 'text', delta: '!' } as AiSdkChunk,
      ]),
      { streamProtocol: 'text' }
    )(makeReq('hi'));
    assert.equal(await res.text(), 'Hi!');
  });

  it('ignores non-text typed chunks', async () => {
    const res = await completionHandler(
      fakeFlow([
        { type: 'reasoning', delta: 'thinking...' } as AiSdkChunk,
        { type: 'text', delta: 'answer' } as AiSdkChunk,
      ]),
      { streamProtocol: 'text' }
    )(makeReq('hi'));
    assert.equal(await res.text(), 'answer');
  });

  it('skips empty string chunks', async () => {
    const res = await completionHandler(fakeFlow(['', 'ok', '']), {
      streamProtocol: 'text',
    })(makeReq('hi'));
    assert.equal(await res.text(), 'ok');
  });
});
