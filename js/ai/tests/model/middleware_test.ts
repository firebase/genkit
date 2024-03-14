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

import { beforeEach, describe, it } from 'node:test';
import { conformOutput, validateSupport } from '../../src/model/middleware';
import assert from 'node:assert';
import {
  GenerationRequest,
  GenerationResponseData,
  Part,
  modelAction,
} from '../../src/model';

describe('validateSupport', () => {
  const examples: Record<string, GenerationRequest> = {
    multiturn: {
      messages: [
        { role: 'user', content: [{ text: 'hello' }] },
        { role: 'model', content: [{ text: 'hi' }] },
        { role: 'user', content: [{ text: 'how are you' }] },
      ],
    },
    media: {
      messages: [
        {
          role: 'user',
          content: [{ media: { url: 'https://example.com/image.png' } }],
        },
      ],
    },
    tools: {
      messages: [
        {
          role: 'user',
          content: [{ media: { url: 'https://example.com/image.png' } }],
        },
      ],
      tools: [
        {
          name: 'someTool',
          description: 'hello world',
          inputSchema: { type: 'object' },
        },
      ],
    },
    json: {
      messages: [
        {
          role: 'user',
          content: [{ text: 'hello world' }],
        },
      ],
      output: { format: 'json' },
    },
  };

  let nextCalled = false;
  const noopNext: (
    req?: GenerationRequest
  ) => Promise<GenerationResponseData> = async () => {
    nextCalled = true;
    return {
      candidates: [],
    };
  };
  beforeEach(() => (nextCalled = false));

  it('accepts anything when no supports is present', () => {
    const runner = validateSupport({ name: 'test-model' });
    for (const example of Object.values(examples)) {
      runner(example, noopNext);
    }
    assert(nextCalled, "next() wasn't called");
  });

  it('throws when media is supplied but not supported', async () => {
    const runner = validateSupport({
      name: 'test-model',
      supports: {
        media: false,
      },
    });
    await assert.rejects(
      runner(examples.media, noopNext),
      /does not support media/
    );
  });

  it('throws when tools are supplied but not supported', async () => {
    const runner = validateSupport({
      name: 'test-model',
      supports: {
        tools: false,
      },
    });
    await assert.rejects(
      runner(examples.tools, noopNext),
      /does not support tool use/
    );
  });

  it('throws when multiturn messages are supplied but not supported', async () => {
    const runner = validateSupport({
      name: 'test-model',
      supports: {
        multiturn: false,
      },
    });
    await assert.rejects(
      runner(examples.multiturn, noopNext),
      /does not support multiple messages/
    );
  });

  it('throws on unsupported output format', async () => {
    const runner = validateSupport({
      name: 'test-model',
      supports: {
        output: ['text', 'media'],
      },
    });
    await assert.rejects(
      runner(examples.json, noopNext),
      /does not support requested output format/
    );
  });
});

const echoModel = modelAction({ name: 'echo' }, async (req) => {
  return {
    candidates: [
      {
        index: 0,
        finishReason: 'stop',
        message: {
          role: 'model',
          content: [{ data: req }],
        },
      },
    ],
  };
});

describe('conformOutput (default middleware)', () => {
  const schema = { type: 'object', properties: { test: { type: 'boolean' } } };

  // return the output tagged part from the request
  async function testRequest(req: GenerationRequest): Promise<Part> {
    const response = await echoModel(req);
    const treq = response.candidates[0].message.content[0]
      .data as GenerationRequest;
    if (
      treq.messages
        .at(-1)!
        ?.content.filter((p) => p.metadata?.purpose === 'output').length > 1
    ) {
      throw new Error('too many output parts');
    }
    return treq.messages
      .at(-1)
      ?.content.find((p) => p.metadata?.purpose === 'output')!;
  }

  it('adds output instructions to the last message', async () => {
    const part = await testRequest({
      messages: [
        { role: 'user', content: [{ text: 'hello' }] },
        { role: 'model', content: [{ text: 'hi' }] },
        { role: 'user', content: [{ text: 'hello again' }] },
      ],
      output: { format: 'json', schema },
    });
    assert(
      part.text?.includes(JSON.stringify(schema)),
      "schema wasn't found in output part"
    );
  });

  it('does not add output instructions if already provided', async () => {
    const part = await testRequest({
      messages: [
        {
          role: 'user',
          content: [{ text: 'hello again', metadata: { purpose: 'output' } }],
        },
      ],
      output: { format: 'json', schema },
    });
    assert.equal(part.text, 'hello again');
  });

  it('does not add output instructions if no output schema is provided', async () => {
    const part = await testRequest({
      messages: [{ role: 'user', content: [{ text: 'hello' }] }],
    });
    assert(!part, 'output part added to non-schema request');
  });
});
