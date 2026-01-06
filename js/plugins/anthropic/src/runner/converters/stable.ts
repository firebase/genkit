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

import type { Part } from 'genkit';

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
    custom: {
      anthropicServerToolUse: {
        id: block.id,
        name: block.name,
        input: block.input,
      },
    },
  };
}
