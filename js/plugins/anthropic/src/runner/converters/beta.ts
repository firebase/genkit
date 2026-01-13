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
 * Converters for beta API content blocks.
 */

import type { BetaRequestDocumentBlock } from '@anthropic-ai/sdk/resources/beta/messages';
import type { Part } from 'genkit';
import type { AnthropicDocumentOptions } from '../../types.js';

/**
 * Converts a server_tool_use block to a Genkit Part.
 * In the beta API, name may be undefined and server_name prefix is supported.
 */
export function betaServerToolUseBlockToPart(block: {
  id: string;
  name?: string;
  input: unknown;
  server_name?: string;
}): Part {
  const baseName = block.name ?? 'unknown_tool';
  const serverToolName = block.server_name
    ? `${block.server_name}/${baseName}`
    : baseName;
  return {
    text: `[Anthropic server tool ${serverToolName}] input: ${JSON.stringify(block.input)}`,
    metadata: {
      anthropicServerToolUse: {
        id: block.id,
        name: serverToolName,
        input: block.input,
      },
    },
  };
}

/**
 * Error message for unsupported server tool block types in the beta API.
 */
export function unsupportedServerToolError(blockType: string): string {
  return `Anthropic beta runner does not yet support server-managed tool block '${blockType}'. Please retry against the stable API or wait for dedicated support.`;
}

/**
 * Converts AnthropicDocumentOptions to Anthropic's beta API document block format.
 */
export function toBetaDocumentBlock(
  options: AnthropicDocumentOptions
): BetaRequestDocumentBlock {
  const block: BetaRequestDocumentBlock = {
    type: 'document',
    source: toBetaDocumentSource(options.source),
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
 * Converts document source options to Anthropic's beta API source format.
 * The beta API supports file-based sources via the Files API.
 */
function toBetaDocumentSource(
  source: AnthropicDocumentOptions['source']
): BetaRequestDocumentBlock['source'] {
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
      return {
        type: 'file',
        file_id: source.fileId,
      };
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
