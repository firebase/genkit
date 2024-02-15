import { describe, it } from 'node:test';
import { compile } from '../src/template';
import assert from 'node:assert';

describe('compile', () => {
  for (const test of [
    {
      should: 'inject variables',
      template: 'Hello {{name}}',
      input: { name: 'World' },
      want: [{ role: 'user', content: [{ text: 'Hello World' }] }],
    },
    {
      should: 'allow multipart with url',
      template: '{{media url=image}} Describe the image above.',
      input: { image: 'https://some.image.url/image.jpg' },
      want: [
        {
          role: 'user',
          content: [
            { media: { url: 'https://some.image.url/image.jpg' } },
            { text: ' Describe the image above.' },
          ],
        },
      ],
    },
    {
      should: 'allow multiple media parts, adjacent or separated by text',
      template:
        'Look at these images: {{#each images}}{{media url=.}} {{/each}} Do you like them? Here ' +
        'is another: {{media url=anotherImage}}',
      input: {
        images: [
          'http://1.png',
          'https://2.png',
          'data:image/jpeg;base64,abc123',
        ],
        anotherImage: 'http://anotherImage.png',
      },
      want: [
        {
          role: 'user',
          content: [
            {
              text: 'Look at these images: ',
            },
            {
              media: { url: 'http://1.png' },
            },
            {
              media: { url: 'https://2.png' },
            },
            {
              media: { url: 'data:image/jpeg;base64,abc123' },
            },
            {
              text: '  Do you like them? Here is another: ',
            },
            {
              media: { url: 'http://anotherImage.png' },
            },
          ],
        },
      ],
    },
    {
      should: 'allow changing the role at the beginning',
      template: `  {{role "system"}}You are super helpful.
      {{~role "user"}}Do something!`,
      want: [
        {
          role: 'system',
          content: [{ text: 'You are super helpful.' }],
        },
        {
          role: 'user',
          content: [{ text: 'Do something!' }],
        },
      ],
    },
    {
      should: 'allow rendering JSON',
      input: { test: true },
      template: '{{json .}}',
      want: [{ role: 'user', content: [{ text: '{"test":true}' }] }],
    },
    {
      should: 'allow indenting JSON',
      input: { test: true },
      template: '{{json . indent=2}}',
      want: [{ role: 'user', content: [{ text: '{\n  "test": true\n}' }] }],
    },
  ]) {
    it(test.should, () => {
      assert.deepEqual(
        compile(test.template, { model: 'test/example' })(test.input),
        test.want
      );
    });
  }
});
