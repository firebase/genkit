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

import type { PromptMessage } from '@modelcontextprotocol/sdk/types.js' with { 'resolution-mode': 'import' };
import { MessageData, Part } from 'genkit';

const ROLE_MAP = {
  user: 'user',
  assistant: 'model',
} as const;

export function fromMcpPromptMessage(message: PromptMessage): MessageData {
  return {
    role: ROLE_MAP[message.role],
    content: [fromMcpPart(message.content)],
  };
}

export function fromMcpPart(part: PromptMessage['content']): Part {
  switch (part.type) {
    case 'text':
      return { text: part.text };
    case 'image':
      return {
        media: {
          contentType: part.mimeType,
          url: `data:${part.mimeType};base64,${part.data}`,
        },
      };
    case 'resource':
      return {};
  }
}
