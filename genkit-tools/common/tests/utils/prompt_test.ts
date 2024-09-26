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

import { describe, expect, it } from '@jest/globals';
import { MessageData } from '../../src/types/model';
import { PromptFrontmatter } from '../../src/types/prompt';
import { fromMessages } from '../../src/utils/prompt';

describe('fromMessages', () => {
  it('builds a template from messages', () => {
    const frontmatter: PromptFrontmatter = {
      name: 'my-prompt',
      model: 'googleai/gemini-pro',
      config: {
        temperature: 0.5,
      },
    };
    const messages: MessageData[] = [
      { role: 'user', content: [{ text: 'Who are you?' }] },
      {
        role: 'model',
        content: [
          { text: 'I am Oz -- the Great and Powerful.' },
          { media: { url: 'https://example.com/image.jpg' } },
        ],
      },
    ];
    const expected =
      '---\n' +
      'name: my-prompt\n' +
      'model: googleai/gemini-pro\n' +
      'config:\n' +
      '  temperature: 0.5\n' +
      '\n' +
      '---\n' +
      '\n' +
      '{{role "user"}}\n' +
      'Who are you?\n' +
      '\n' +
      '{{role "model"}}\n' +
      'I am Oz -- the Great and Powerful.,' +
      '{{media url:https://example.com/image.jpg}}\n' +
      '\n';
    expect(fromMessages(frontmatter, messages)).toStrictEqual(expected);
  });
});
