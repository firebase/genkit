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

import { stringify } from 'yaml';
import { MessageData, Part } from '../types/model';
import { PromptFrontmatter } from '../types/prompt';

export function fromMessages(
  frontmatter: PromptFrontmatter,
  messages: MessageData[]
): string {
  let renderedMessages = '';
  messages.forEach((message) => {
    renderedMessages += `{{role "${message.role}"}}\n`;
    renderedMessages += message.content.map(partToString);
    renderedMessages += '\n\n';
  });

  return `---
${stringify(frontmatter)}
---

${renderedMessages}`;
}

function partToString(part: Part): string {
  if (part.text) {
    return part.text;
  } else if (part.media) {
    return `{{media url:${part.media.url}}}`;
  } else if (part.toolRequest) {
    return '<< tool request omitted >>';
  } else if (part.toolResponse) {
    return '<< tool response omitted >>';
  } else {
    return '';
  }
}
