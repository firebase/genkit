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
import { objectHandler } from '../src/object.js';

function fakeFlow(chunks: string[]) {
  return {
    stream(_input: unknown, _opts?: unknown) {
      return {
        stream: (async function* () {
          for (const c of chunks) yield c;
        })(),
        output: Promise.resolve(chunks.join('')),
      };
    },
  } as any;
}

describe('objectHandler — streaming', () => {
  it('returns text/plain response', async () => {
    const res = await objectHandler(fakeFlow(['{}']))(
      new Request('http://localhost/api/object', {
        method: 'POST',
        body: JSON.stringify({}),
      })
    );
    assert.equal(res.status, 200);
    assert.ok(res.headers.get('Content-Type')?.includes('text/plain'));
  });

  it('pipes partial JSON verbatim', async () => {
    const res = await objectHandler(fakeFlow(['{"items":[', '"a","b"', ']}']))(
      new Request('http://localhost/api/object', {
        method: 'POST',
        body: JSON.stringify({ topic: 'fruit' }),
      })
    );
    assert.equal(await res.text(), '{"items":["a","b"]}');
  });

  it('skips empty chunks', async () => {
    const res = await objectHandler(fakeFlow(['', '{"ok":true}', '']))(
      new Request('http://localhost/api/object', {
        method: 'POST',
        body: JSON.stringify({}),
      })
    );
    assert.equal(await res.text(), '{"ok":true}');
  });
});

describe('objectHandler — request validation', () => {
  it('returns 400 for malformed JSON', async () => {
    const res = await objectHandler(fakeFlow([]))(
      new Request('http://localhost/api/object', {
        method: 'POST',
        body: 'not json',
      })
    );
    assert.equal(res.status, 400);
  });
});

describe('objectHandler — contextProvider', () => {
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

    const res = await objectHandler(flow, {
      contextProvider: async () => ({ userId: 'u1' }),
    })(
      new Request('http://localhost/api/object', {
        method: 'POST',
        body: JSON.stringify({}),
      })
    );
    await res.text(); // drain
    assert.deepEqual(capturedOpts.context, { userId: 'u1' });
  });

  it('returns error status when contextProvider throws before stream opens', async () => {
    const err = Object.assign(new Error('Unauthorized'), { status: 401 });
    const res = await objectHandler(fakeFlow([]), {
      contextProvider: async () => {
        throw err;
      },
    })(
      new Request('http://localhost/api/object', {
        method: 'POST',
        body: JSON.stringify({}),
      })
    );
    assert.equal(res.status, 401);
  });
});

describe('objectHandler — mid-stream errors', () => {
  it('closes the stream without appending text so partial JSON is not corrupted', async () => {
    let onErrorCalled = false;
    const flow = {
      stream(_: unknown, __: unknown) {
        return {
          stream: (async function* () {
            yield '{"item":';
            throw new Error('mid-stream failure');
          })(),
          output: Promise.resolve(''),
        };
      },
    } as any;

    const res = await objectHandler(flow, {
      onError: () => {
        onErrorCalled = true;
      },
    })(
      new Request('http://localhost/api/object', {
        method: 'POST',
        body: JSON.stringify({}),
      })
    );

    const text = await res.text();
    // Should not have appended any error JSON — the partial JSON stands alone
    assert.equal(text, '{"item":');
    assert.ok(onErrorCalled);
  });
});

describe('objectHandler — abort signal', () => {
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

    const res = await objectHandler(flow)(
      new Request('http://localhost/api/object', {
        method: 'POST',
        body: JSON.stringify({}),
      })
    );
    await res.text(); // drain
    assert.ok(capturedOpts.abortSignal instanceof AbortSignal);
  });
});
