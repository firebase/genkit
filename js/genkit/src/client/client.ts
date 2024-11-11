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

const __flowStreamDelimiter = '\n\n';

/**
 * Invoke and stream response from a deployed flow.
 *
 * For example:
 *
 * ```js
 * import { streamFlow } from '@genkit-ai/core/flow-client';
 *
 * const response = streamFlow({
 *   url: 'https://my-flow-deployed-url',
 *   input: 'foo',
 * });
 * for await (const chunk of response.stream) {
 *   console.log(chunk);
 * }
 * console.log(await response.output);
 * ```
 */
export function streamFlow({
  url,
  input,
  headers,
}: {
  url: string;
  input?: any;
  headers?: Record<string, string>;
}) {
  let chunkStreamController: ReadableStreamDefaultController | undefined =
    undefined;
  const chunkStream = new ReadableStream({
    start(controller) {
      chunkStreamController = controller;
    },
    pull() {},
    cancel() {},
  });

  const operationPromise = __flowRunEnvelope({
    url,
    input,
    streamingCallback: (c) => {
      chunkStreamController?.enqueue(c);
    },
    headers,
  });
  operationPromise.then((o) => {
    chunkStreamController?.close();
    return o;
  });

  return {
    output() {
      return operationPromise;
    },
    async *stream() {
      const reader = chunkStream.getReader();
      while (true) {
        const chunk = await reader.read();
        if (chunk?.value !== undefined) {
          yield chunk.value;
        }
        if (chunk.done) {
          break;
        }
      }
      return await operationPromise;
    },
  };
}

async function __flowRunEnvelope({
  url,
  input,
  streamingCallback,
  headers,
}: {
  url: string;
  input: any;
  streamingCallback: (chunk: any) => void;
  headers?: Record<string, string>;
}) {
  let response;
  response = await fetch(url, {
    method: 'POST',
    body: JSON.stringify({
      data: input,
    }),
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      ...headers,
    },
  });
  if (!response.body) {
    throw new Error('Response body is empty');
  }
  var reader = response.body.getReader();
  var decoder = new TextDecoder();

  let buffer = '';
  while (true) {
    const result = await reader.read();
    const decodedValue = decoder.decode(result.value);
    if (decodedValue) {
      buffer += decodedValue;
    }
    // If buffer includes the delimiter that means we are still recieving chunks.
    while (buffer.includes(__flowStreamDelimiter)) {
      const chunk = JSON.parse(
        buffer
          .substring(0, buffer.indexOf(__flowStreamDelimiter))
          .substring('data: '.length)
      );
      if (chunk.hasOwnProperty('message')) {
        streamingCallback(chunk.message);
      } else if (chunk.hasOwnProperty('result')) {
        return chunk.result;
      } else if (chunk.hasOwnProperty('error')) {
        throw new Error(
          `${chunk.error.status}: ${chunk.error.message}\n${chunk.error.details}`
        );
      } else {
        throw new Error('unkown chunk format: ' + JSON.stringify(chunk));
      }
      buffer = buffer.substring(
        buffer.indexOf(__flowStreamDelimiter) + __flowStreamDelimiter.length
      );
    }
  }
  throw new Error('stream did not terminate correctly');
}

/**
 * Invoke a deployed flow over HTTP(s).
 *
 * For example:
 *
 * ```js
 * import { runFlow } from '@genkit-ai/core/flow-client';
 *
 * const response = await runFlow({
 *   url: 'https://my-flow-deployed-url',
 *   input: 'foo',
 * });
 * console.log(await response);
 * ```
 */
export async function runFlow({
  url,
  input,
  headers,
}: {
  url: string;
  input?: any;
  headers?: Record<string, string>;
}) {
  const response = await fetch(url, {
    method: 'POST',
    body: JSON.stringify({
      data: input,
    }),
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  });
  const wrappedDesult = await response.json();
  return wrappedDesult.result;
}
