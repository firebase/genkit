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

// ---------------------------------------------------------------------------
// Vercel AI SDK UIMessage types (vendored — no runtime dep on `ai`)
// ---------------------------------------------------------------------------

/** A single content part inside a UIMessage (AI SDK v4+). */
export interface UIMessagePart {
  type: string;
  text?: string;
  [key: string]: unknown;
}

/** A tool-invocation part inside an assistant UIMessage. */
interface ToolInvocationPart {
  type: 'tool-invocation';
  toolInvocation: {
    toolCallId: string;
    toolName: string;
    state: 'call' | 'partial-call' | 'result';
    args?: unknown;
    result?: unknown;
  };
}

/** A file/image attachment part inside a user UIMessage. */
interface FilePart {
  type: 'file';
  url: string;          // data: URI or https: URL
  mediaType?: string;   // MIME type
  filename?: string;
}

/**
 * A message in the Vercel AI SDK UIMessage format, as sent by `useChat()`.
 * https://ai-sdk.dev/docs/reference/ai-sdk-ui/use-chat
 */
export interface UIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  parts: UIMessagePart[];
  /** @deprecated Legacy flat content field — prefer `parts`. */
  content?: string;
}

// ---------------------------------------------------------------------------
// Genkit MessageData types (mirrored here to avoid importing genkit at runtime)
// ---------------------------------------------------------------------------

export interface GenkitTextPart       { text: string }
export interface GenkitMediaPart      { media: { url: string; contentType?: string } }
export interface GenkitToolReqPart    { toolRequest: { ref?: string; name: string; input?: unknown } }
export interface GenkitToolResPart    { toolResponse: { ref?: string; name: string; output?: unknown } }

export type GenkitPart =
  | GenkitTextPart
  | GenkitMediaPart
  | GenkitToolReqPart
  | GenkitToolResPart;

export interface GenkitMessageData {
  role: 'user' | 'model' | 'system' | 'tool';
  content: GenkitPart[];
}

// ---------------------------------------------------------------------------
// Conversion
// ---------------------------------------------------------------------------

/**
 * Convert a Vercel AI SDK `UIMessage[]` (as sent by `useChat()`) to Genkit
 * `MessageData[]` for use as the `messages` parameter of `generateStream()`.
 *
 * Handles:
 * - `text` parts → `GenkitTextPart`
 * - `file` / image attachment parts → `GenkitMediaPart`
 * - `tool-invocation` parts in assistant messages:
 *   - state `call` / `partial-call` → appended as `toolRequest` to the model message
 *   - state `result` → model message with `toolRequest` + separate `tool` message with `toolResponse`
 * - `system` role → passed through as-is
 * - Legacy flat `content` string → treated as a single text part
 */
export function toGenkitMessages(messages: UIMessage[]): GenkitMessageData[] {
  const result: GenkitMessageData[] = [];

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
        // tool-invocation parts with state=result also generate a separate tool message.
        const modelParts: GenkitPart[] = [];
        const toolMessages: GenkitMessageData[] = [];

        for (const part of msg.parts ?? []) {
          if (part.type === 'text' && typeof part.text === 'string') {
            modelParts.push({ text: part.text });
          } else if (part.type === 'tool-invocation') {
            const ti = (part as unknown as ToolInvocationPart).toolInvocation;
            modelParts.push({
              toolRequest: {
                ref: ti.toolCallId,
                name: ti.toolName,
                input: ti.args,
              },
            });
            if (ti.state === 'result') {
              toolMessages.push({
                role: 'tool',
                content: [
                  {
                    toolResponse: {
                      ref: ti.toolCallId,
                      name: ti.toolName,
                      output: ti.result,
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
        if (modelParts.length === 0 && msg.content) {
          modelParts.push({ text: msg.content });
        }

        if (modelParts.length > 0) {
          result.push({ role: 'model', content: modelParts });
        }
        result.push(...toolMessages);
        break;
      }

      case 'tool':
        // Legacy tool role — pass through as-is with a best-effort toolResponse.
        result.push({
          role: 'tool',
          content: msg.content
            ? [{ toolResponse: { name: 'unknown', output: msg.content } }]
            : [],
        });
        break;
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extract Genkit parts from the text and file parts of a UIMessage. */
function extractParts(msg: UIMessage): GenkitPart[] {
  const parts: GenkitPart[] = [];

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
  if (parts.length === 0 && msg.content) {
    parts.push({ text: msg.content });
  }

  return parts;
}
