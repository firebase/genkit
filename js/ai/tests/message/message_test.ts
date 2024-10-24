import assert from 'node:assert';
import { describe, it } from 'node:test';
import { Message } from '../../src/message';

describe('Message', () => {
  describe('.parseData()', () => {
    const testCases = [
      {
        desc: 'convert string to user message',
        input: 'i am a user message',
        want: { role: 'user', content: [{ text: 'i am a user message' }] },
      },
      {
        desc: 'convert string content to Part[] content',
        input: {
          role: 'system',
          content: 'i am a system message',
          metadata: { extra: true },
        },
        want: {
          role: 'system',
          content: [{ text: 'i am a system message' }],
          metadata: { extra: true },
        },
      },
      {
        desc: 'leave valid MessageData alone',
        input: { role: 'model', content: [{ text: 'i am a model message' }] },
        want: { role: 'model', content: [{ text: 'i am a model message' }] },
      },
    ];

    for (const t of testCases) {
      it(t.desc, () => {
        assert.deepStrictEqual(Message.parseData(t.input as any), t.want);
      });
    }
  });
});
