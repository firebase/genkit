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
 * Pure utility functions for converting Anthropic content blocks to Genkit Parts.
 *
 * Uses structural typing so both stable and beta API types work with these functions.
 */

import type { Part } from 'genkit';

/**
 * Key used to store Anthropic-specific thinking metadata in Genkit Part custom field.
 */
export const ANTHROPIC_THINKING_CUSTOM_KEY = 'anthropicThinking';

/**
 * Converts a text block to a Genkit Part.
 */
export function textBlockToPart(block: { text: string }): Part {
  return { text: block.text };
}

/**
 * Converts a thinking block to a Genkit Part, optionally including signature metadata.
 */
export function thinkingBlockToPart(
  block: { thinking: string; signature?: string },
  signature?: string
): Part {
  const sig = signature ?? block.signature;
  const custom =
    sig !== undefined
      ? {
          [ANTHROPIC_THINKING_CUSTOM_KEY]: { signature: sig },
        }
      : undefined;
  return custom
    ? {
        reasoning: block.thinking,
        custom,
      }
    : {
        reasoning: block.thinking,
      };
}

/**
 * Converts a redacted thinking block to a Genkit Part.
 */
export function redactedThinkingBlockToPart(block: { data: string }): Part {
  return { custom: { redactedThinking: block.data } };
}

/**
 * Converts a tool_use block to a Genkit Part.
 */
export function toolUseBlockToPart(block: {
  id: string;
  name: string;
  input: unknown;
}): Part {
  return {
    toolRequest: {
      ref: block.id,
      name: block.name,
      input: block.input,
    },
  };
}

/**
 * Converts a server_tool_use block to a Genkit Part.
 */
export function serverToolUseBlockToPart(block: {
  id: string;
  name: string;
  input: unknown;
}): Part {
  return {
    text: `[Anthropic server tool ${block.name}] input: ${JSON.stringify(block.input)}`,
    custom: {
      anthropicServerToolUse: {
        id: block.id,
        name: block.name,
        input: block.input,
      },
    },
  };
}

/**
 * Converts a web_search_tool_result block to a Genkit Part.
 */
export function webSearchToolResultBlockToPart(block: {
  tool_use_id: string;
  content: unknown;
}): Part {
  return {
    text: `[Anthropic server tool result ${block.tool_use_id}] ${JSON.stringify(block.content)}`,
    custom: {
      anthropicServerToolResult: {
        type: 'web_search_tool_result',
        toolUseId: block.tool_use_id,
        content: block.content,
      },
    },
  };
}
