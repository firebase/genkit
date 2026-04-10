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
 * Conversion utilities: Vercel AI SDK UIMessage[] → Genkit MessageData[].
 */

import type { MessageData, Part } from 'genkit';

// ---------------------------------------------------------------------------
// Vercel AI SDK UIMessage types (vendored — no runtime dep on `ai`)
// Based on AI SDK v6.0 UIMessage format.  Audit for drift when upgrading.
//
// In v6, tool parts use `dynamic-tool` (or `tool-${name}` for statically
// typed tools) with states: input-streaming, input-available,
// output-available, output-error, output-denied.  Fields: `input` / `output`.
// This replaced the v4/v5 `tool-invocation` with `call`/`result` states and
// `args`/`result` fields.
// ---------------------------------------------------------------------------

/** A single content part inside a UIMessage (AI SDK v6). */
export interface UIMessagePart {
  type: string;
  text?: string;
  [key: string]: unknown;
}

/**
 * A tool part inside an assistant UIMessage (AI SDK v6).
 * Covers both `dynamic-tool` and `tool-${name}` part types.
 */
interface ToolPart {
  type: string; // 'dynamic-tool' or 'tool-${name}'
  toolCallId: string;
  toolName?: string; // present on dynamic-tool; derived from type on static
  state:
    | 'input-streaming'
    | 'input-available'
    | 'output-available'
    | 'output-error'
    | 'output-denied';
  input?: unknown;
  output?: unknown;
}

/** A file/image attachment part inside a user UIMessage. */
interface FilePart {
  type: 'file';
  url: string; // data: URI or https: URL
  mediaType?: string; // MIME type
  filename?: string;
}

/**
 * A message in the Vercel AI SDK UIMessage format, as sent by `useChat()`.
 * https://ai-sdk.dev/docs/reference/ai-sdk-ui/use-chat
 */
export interface UIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  parts: UIMessagePart[];
  /** @deprecated Legacy flat content field — prefer `parts`. */
  content?: string;
}

// ---------------------------------------------------------------------------
// Conversion
// ---------------------------------------------------------------------------

/**
 * Convert a Vercel AI SDK `UIMessage[]` (as sent by `useChat()`) to Genkit
 * `MessageData[]` for use as the `messages` parameter of `generateStream()`.
 *
 * Handles:
 * - `text` parts → text part
 * - `file` / image attachment parts → media part
 * - `dynamic-tool` / `tool-${name}` parts in assistant messages:
 *   - state `input-available` / `input-streaming` → appended as `toolRequest` to the model message
 *   - state `output-available` → model message with `toolRequest` + separate `tool` message with `toolResponse`
 * - `system` role → passed through as-is
 * - Legacy flat `content` string → treated as a single text part
 */
export function toGenkitMessages(messages: UIMessage[]): MessageData[] {
  const result: MessageData[] = [];

  for (const msg of messages) {
    switch (msg.role) {
      case 'system':
        result.push({ role: 'system', content: extractParts(msg) });
        break;

      case 'user':
        result.push({ role: 'user', content: extractParts(msg) });
        break;

      case 'assistant': {
        // Collect all content parts for the model message.
        // Tool parts with state=output-available also generate a separate tool message.
        const modelParts: Part[] = [];
        const toolMessages: MessageData[] = [];

        for (const part of msg.parts ?? []) {
          if (part.type === 'text' && typeof part.text === 'string') {
            modelParts.push({ text: part.text });
          } else if (isToolPart(part)) {
            const tp = part as unknown as ToolPart;
            const toolName = tp.toolName ?? tp.type.replace(/^tool-/, '');
            modelParts.push({
              toolRequest: {
                ref: tp.toolCallId,
                name: toolName,
                input: tp.input,
              },
            });
            if (tp.state === 'output-available') {
              toolMessages.push({
                role: 'tool',
                content: [
                  {
                    toolResponse: {
                      ref: tp.toolCallId,
                      name: toolName,
                      output: tp.output,
                    },
                  },
                ],
              });
            }
          }
          // Other part types (reasoning, step-start, etc.) are not forwarded
          // to the model — they're output-only artifacts.
        }

        // Fall back to legacy flat content string if parts is empty.
        const legacyContent = (msg as { content?: string }).content;
        if (modelParts.length === 0 && legacyContent) {
          modelParts.push({ text: legacyContent });
        }

        if (modelParts.length > 0) {
          result.push({ role: 'model', content: modelParts });
        }
        result.push(...toolMessages);
        break;
      }
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns true for AI SDK v6 tool parts: `dynamic-tool` or `tool-${name}`.
 * Static tool parts have the format `tool-${toolName}` (never just `tool`).
 */
function isToolPart(part: UIMessagePart): boolean {
  return (
    part.type === 'dynamic-tool' ||
    (part.type.startsWith('tool-') && 'toolCallId' in part)
  );
}

/** Extract Genkit parts from the text and file parts of a UIMessage. */
function extractParts(msg: UIMessage): Part[] {
  const parts: Part[] = [];

  if (msg.parts?.length) {
    for (const part of msg.parts) {
      if (part.type === 'text' && typeof part.text === 'string') {
        parts.push({ text: part.text });
      } else if (part.type === 'file') {
        const fp = part as unknown as FilePart;
        parts.push({
          media: { url: fp.url, contentType: fp.mediaType },
        });
      }
    }
  }

  // Fall back to legacy flat content string.
  const legacyContent = (msg as { content?: string }).content;
  if (parts.length === 0 && legacyContent) {
    parts.push({ text: legacyContent });
  }

  return parts;
}
