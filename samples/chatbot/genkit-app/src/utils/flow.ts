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

const __flowStreamDelimiter = '\n';

export async function runFlow({
  url,
  payload,
  headers,
}: {
  url: string;
  payload?: any;
  headers?: Record<string, string>;
}) {
  const response = await fetch(url, {
    method: 'POST',
    body: JSON.stringify({
      data: payload,
    }),
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  });
  const wrappedDesult = await response.json();
  return wrappedDesult.result;
}

export function streamFlow({
  url,
  payload,
  headers,
}: {
  url: string;
  payload?: any;
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
    payload,
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
      return operationPromise.then((op) => {
        if (!op.done) {
          throw new Error(`flow ${op.name} did not finish execution`);
        }
        if (op.result?.error) {
          throw new Error(op.result?.error + op.result?.stacktrace);
        }
        return op.result?.response;
      });
    },
    async *stream() {
      const reader = chunkStream.getReader();
      while (true) {
        const chunk = await reader.read();
        if (chunk.value) {
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
  payload,
  streamingCallback,
  headers,
}: {
  url: string;
  payload?: any;
  streamingCallback: (chunk: any) => void;
  headers?: Record<string, string>;
}) {
  let response;
  response = await fetch(url + '?stream=true', {
    method: 'POST',
    body: JSON.stringify({
      data: payload,
    }),
    headers: {
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
      streamingCallback(
        JSON.parse(buffer.substring(0, buffer.indexOf(__flowStreamDelimiter)))
      );
      buffer = buffer.substring(
        buffer.indexOf(__flowStreamDelimiter) + __flowStreamDelimiter.length
      );
    }
    if (result.done) {
      return JSON.parse(buffer);
    }
  }
}
