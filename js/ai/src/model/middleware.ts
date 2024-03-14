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

import { ModelInfo, ModelMiddleware, Part } from '../model';

/**
 * Preprocess a GenerationRequest to download referenced http(s) media URLs and
 * inline them as data URIs.
 */
export function downloadRequestMedia(options?: {
  maxBytes?: number;
}): ModelMiddleware {
  return async (req, next) => {
    const { default: fetch } = await import('node-fetch');

    const newReq = {
      ...req,
      messages: await Promise.all(
        req.messages.map(async (message) => {
          const content: Part[] = await Promise.all(
            message.content.map(async (part) => {
              // skip non-media parts and non-http urls
              if (!part.media || !part.media.url.startsWith('http')) {
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
 * Validates that a GenerationRequest does not include unsupported features.
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

export function conformOutput(): ModelMiddleware {
  return async (req, next) => {
    const lastMessage = req.messages[req.messages.length - 1];
    if (
      !req.output?.schema ||
      req.messages
        .at(-1)
        ?.content.some((part) => part.metadata?.purpose === 'output')
    ) {
      return next(req);
    }

    lastMessage?.content.push({
      text: `

Output should be in JSON format and conform to the following schema:

\`\`\`
${JSON.stringify(req.output!.schema!)}
\`\`\`
`,
      metadata: { purpose: 'output', source: 'default' },
    });

    return next(req);
  };
}
