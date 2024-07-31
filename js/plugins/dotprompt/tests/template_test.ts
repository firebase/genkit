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

import { MessageData } from '@genkit-ai/ai/model';
import { DocumentData } from '@genkit-ai/ai/retriever';
import assert from 'node:assert';
import { describe, it } from 'node:test';
import { compile } from '../src/template';

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
    {
      should: 'insert history after other messages before final user message',
      input: {},
      template: `{{role "system"}}You are a robot{{role "user"}}Hello there`,
      options: {
        history: [
          { role: 'user', content: [{ text: 'Ping' }] },
          { role: 'model', content: [{ text: 'Pong' }] },
        ],
      },
      want: [
        { role: 'system', content: [{ text: 'You are a robot' }] },
        { role: 'user', content: [{ text: 'Ping' }] },
        { role: 'model', content: [{ text: 'Pong' }] },
        { role: 'user', content: [{ text: 'Hello there' }] },
      ],
    },
    {
      should: 'insert history in the specified location',
      input: {},
      template: `{{history}}{{role "system"}}You are a robot{{role "user"}}Hello there`,
      options: {
        history: [
          { role: 'user', content: [{ text: 'Ping' }] },
          { role: 'model', content: [{ text: 'Pong' }] },
        ],
      },
      want: [
        {
          role: 'user',
          content: [{ text: 'Ping' }],
          metadata: { purpose: 'history' },
        },
        {
          role: 'model',
          content: [{ text: 'Pong' }],
          metadata: { purpose: 'history' },
        },
        { role: 'system', content: [{ text: 'You are a robot' }] },
        { role: 'user', content: [{ text: 'Hello there' }] },
      ],
    },
    {
      should: 'insert a blank context section when helper provided',
      input: {},
      template: `before{{section "context"}}after`,
      options: {
        context: [{ content: [{ text: 'doc content' }] }],
      },
      want: [
        {
          role: 'user',
          content: [
            { text: 'before' },
            { metadata: { purpose: 'context', pending: true } },
            { text: 'after' },
          ],
        },
      ],
    },
    {
      should: 'insert a blank output section when helper provided',
      input: {},
      template: `before{{section "output"}}after`,
      options: {
        context: [{ content: [{ text: 'doc content' }] }],
      },
      want: [
        {
          role: 'user',
          content: [
            { text: 'before' },
            { metadata: { purpose: 'output', pending: true } },
            { text: 'after' },
          ],
        },
      ],
    },
  ]) {
    it(test.should, () => {
      assert.deepEqual(
        compile(test.template, { model: 'test/example' })(test.input, {
          history: test.options?.history as MessageData[],
          context: test.options?.context as DocumentData[],
        }),
        test.want
      );
    });
  }
});
