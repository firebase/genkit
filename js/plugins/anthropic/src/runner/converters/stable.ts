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

/**
 * Converters for stable API content blocks.
 */

import type { DocumentBlockParam } from '@anthropic-ai/sdk/resources/messages';
import type { Part } from 'genkit';
import type { AnthropicDocumentOptions } from '../../types.js';

/**
 * Converts a server_tool_use block to a Genkit Part.
 * In the stable API, name is always present.
 */
export function serverToolUseBlockToPart(block: {
  id: string;
  name: string;
  input: unknown;
}): Part {
  return {
    text: `[Anthropic server tool ${block.name}] input: ${JSON.stringify(block.input)}`,
    metadata: {
      anthropicServerToolUse: {
        id: block.id,
        name: block.name,
        input: block.input,
      },
    },
  };
}

/**
 * Converts AnthropicDocumentOptions to Anthropic's stable API document block format.
 */
export function toDocumentBlock(
  options: AnthropicDocumentOptions
): DocumentBlockParam {
  const block: DocumentBlockParam = {
    type: 'document',
    source: toDocumentSource(options.source),
  };

  if (options.title) {
    block.title = options.title;
  }
  if (options.context) {
    block.context = options.context;
  }
  if (options.citations) {
    block.citations = options.citations;
  }

  return block;
}

/**
 * Converts document source options to Anthropic's stable API source format.
 * Note: The stable API does not support file-based sources (Files API).
 */
function toDocumentSource(
  source: AnthropicDocumentOptions['source']
): DocumentBlockParam['source'] {
  switch (source.type) {
    case 'text':
      return {
        type: 'text',
        media_type: (source.mediaType ?? 'text/plain') as 'text/plain',
        data: source.data,
      };
    case 'base64':
      return {
        type: 'base64',
        media_type: source.mediaType as 'application/pdf',
        data: source.data,
      };
    case 'file':
      throw new Error(
        'File-based document sources require the beta API. Set apiVersion: "beta" in your plugin config or request config.'
      );
    case 'content':
      return {
        type: 'content',
        content: source.content.map((item) => {
          if (item.type === 'text') {
            return item;
          }
          return {
            type: 'image' as const,
            source: {
              type: 'base64' as const,
              media_type: item.source.mediaType as
                | 'image/jpeg'
                | 'image/png'
                | 'image/gif'
                | 'image/webp',
              data: item.source.data,
            },
          };
        }),
      };
    case 'url':
      return {
        type: 'url',
        url: source.url,
      };
    default:
      throw new Error(
        `Unsupported document source type: ${(source as { type: string }).type}`
      );
  }
}
