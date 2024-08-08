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

import { Document } from '../document.js';
import {
  MediaPart,
  MessageData,
  ModelInfo,
  ModelMiddleware,
  Part,
} from '../model.js';

/**
 * Preprocess a GenerateRequest to download referenced http(s) media URLs and
 * inline them as data URIs.
 */
export function downloadRequestMedia(options?: {
  maxBytes?: number;
  filter?: (part: MediaPart) => boolean;
}): ModelMiddleware {
  return async (req, next) => {
    const { default: fetch } = await import('node-fetch');

    const newReq = {
      ...req,
      messages: await Promise.all(
        req.messages.map(async (message) => {
          const content: Part[] = await Promise.all(
            message.content.map(async (part) => {
              // skip non-media parts and non-http urls, or parts that have been
              // filtered out by user config
              if (
                !part.media ||
                !part.media.url.startsWith('http') ||
                (options?.filter && !options?.filter(part))
              ) {
                return part;
              }

              const response = await fetch(part.media.url, {
                size: options?.maxBytes,
              });
              if (response.status !== 200)
                throw new Error(
                  `HTTP error downloading media '${
                    part.media.url
                  }': ${await response.text()}`
                );

              // use provided contentType or sniff from response
              const contentType =
                part.media.contentType ||
                response.headers.get('content-type') ||
                '';

              return {
                media: {
                  contentType,
                  url: `data:${contentType};base64,${Buffer.from(
                    await response.arrayBuffer()
                  ).toString('base64')}`,
                },
              };
            })
          );

          return {
            ...message,
            content,
          };
        })
      ),
    };

    return next(newReq);
  };
}

/**
 * Validates that a GenerateRequest does not include unsupported features.
 */
export function validateSupport(options: {
  name: string;
  supports?: ModelInfo['supports'];
}): ModelMiddleware {
  const supports = options.supports || {};
  return async (req, next) => {
    function invalid(message: string): never {
      throw new Error(
        `Model '${
          options.name
        }' does not support ${message}. Request: ${JSON.stringify(
          req,
          null,
          2
        )}`
      );
    }

    if (
      supports.media === false &&
      req.messages.some((message) => message.content.some((part) => part.media))
    )
      invalid('media, but media was provided');
    if (supports.tools === false && req.tools?.length)
      invalid('tool use, but tools were provided');
    if (supports.multiturn === false && req.messages.length > 1)
      invalid(`multiple messages, but ${req.messages.length} were provided`);
    if (
      typeof supports.output !== 'undefined' &&
      req.output?.format &&
      !supports.output.includes(req.output?.format)
    )
      invalid(`requested output format '${req.output?.format}'`);
    return next();
  };
}

function lastUserMessage(messages: MessageData[]) {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'user') {
      return messages[i];
    }
  }
}

export function conformOutput(): ModelMiddleware {
  return async (req, next) => {
    const lastMessage = lastUserMessage(req.messages);
    if (!lastMessage) return next(req);
    const outputPartIndex = lastMessage.content.findIndex(
      (p) => p.metadata?.purpose === 'output'
    );
    const outputPart =
      outputPartIndex >= 0 ? lastMessage.content[outputPartIndex] : undefined;

    if (!req.output?.schema || (outputPart && !outputPart?.metadata?.pending)) {
      return next(req);
    }

    const instructions = `

Output should be in JSON format and conform to the following schema:

\`\`\`
${JSON.stringify(req.output!.schema!)}
\`\`\`
`;

    if (outputPart) {
      lastMessage.content[outputPartIndex] = {
        ...outputPart,
        metadata: {
          purpose: 'output',
          source: 'default',
        },
        text: instructions,
      } as Part;
    } else {
      lastMessage?.content.push({
        text: instructions,
        metadata: { purpose: 'output', source: 'default' },
      });
    }

    return next(req);
  };
}

/**
 * Provide a simulated system prompt for models that don't support it natively.
 */
export function simulateSystemPrompt(options?: {
  preface: string;
  acknowledgement: string;
}): ModelMiddleware {
  const preface = options?.preface || 'SYSTEM INSTRUCTIONS:\n';
  const acknowledgement = options?.acknowledgement || 'Understood.';

  return (req, next) => {
    const messages = [...req.messages];
    for (let i = 0; i < messages.length; i++) {
      if (req.messages[i].role === 'system') {
        const systemPrompt = messages[i].content;
        messages.splice(
          i,
          1,
          { role: 'user', content: [{ text: preface }, ...systemPrompt] },
          { role: 'model', content: [{ text: acknowledgement }] }
        );
        break;
      }
    }
    return next({ ...req, messages });
  };
}

export interface AugmentWithContextOptions {
  /** Preceding text to place before the rendered context documents. */
  preface?: string | null;
  /** A function to render a document into a text part to be included in the message. */
  itemTemplate?: (d: Document, options?: AugmentWithContextOptions) => string;
  /** The metadata key to use for citation reference. Pass `null` to provide no citations. */
  citationKey?: string | null;
}

export const CONTEXT_PREFACE =
  '\n\nUse the following information to complete your task:\n\n';
const CONTEXT_ITEM_TEMPLATE = (
  d: Document,
  index: number,
  options?: AugmentWithContextOptions
) => {
  let out = '- ';
  if (options?.citationKey) {
    out += `[${d.metadata![options.citationKey]}]: `;
  } else if (options?.citationKey === undefined) {
    out += `[${d.metadata?.['ref'] || d.metadata?.['id'] || index}]: `;
  }
  out += d.text() + '\n';
  return out;
};

export function augmentWithContext(
  options?: AugmentWithContextOptions
): ModelMiddleware {
  const preface =
    typeof options?.preface === 'undefined' ? CONTEXT_PREFACE : options.preface;
  const itemTemplate = options?.itemTemplate || CONTEXT_ITEM_TEMPLATE;
  return (req, next) => {
    // if there is no context in the request, no-op
    if (!req.context?.length) return next(req);
    const userMessage = lastUserMessage(req.messages);
    // if there are no messages, no-op
    if (!userMessage) return next(req);
    // if there is already a context part, no-op
    const contextPartIndex = userMessage?.content.findIndex(
      (p) => p.metadata?.purpose === 'context'
    );
    const contextPart =
      contextPartIndex >= 0 && userMessage.content[contextPartIndex];

    if (contextPart && !contextPart.metadata?.pending) {
      return next(req);
    }
    let out = `${preface || ''}`;
    req.context?.forEach((d, i) => {
      out += itemTemplate(new Document(d), i, options);
    });
    out += '\n';
    if (contextPartIndex >= 0) {
      userMessage.content[contextPartIndex] = {
        ...contextPart,
        text: out,
        metadata: { purpose: 'context' },
      } as Part;
    } else {
      userMessage.content.push({ text: out, metadata: { purpose: 'context' } });
    }

    return next(req);
  };
}
