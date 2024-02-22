import { beforeEach, describe, it } from 'node:test';
import { validateSupport } from '../../src/model/middleware';
import assert from 'node:assert';
import { GenerationRequest, GenerationResponseData } from '../../src/model';

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
        content: [{ tools: { url: 'https://example.com/image.png' } }],
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

describe('validateSupport', () => {
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
