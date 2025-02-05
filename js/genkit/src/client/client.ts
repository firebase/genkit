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

import { Channel } from '@genkit-ai/core/async';
import { z } from '@genkit-ai/core/zod';

interface RunOptions {
  headers?: Record<string, string>;
}

export type RemoteAction<I = any, O = any, S = any> = ((
  input?: I,
  options?: RunOptions
) => Promise<O>) & {
  stream(input?: I, opts?: RunOptions): StreamingResponse<O, S>;
};

/**
 * Streaming response from an action.
 */
export interface StreamingResponse<O = any, S = any> {
  /** Iterator over the streaming chunks. */
  stream: AsyncIterable<S>;
  /** Final output of the action. */
  output: Promise<O>;
}

/**
 * Defines a remote action which can be invoked as a function or streamed.
 */
export function defineRemoteAction<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(actionOptions: {
  url: string;
  headers?: Record<string, string>;
  inputSchema?: I;
  outputSchema?: O;
  streamSchema?: S;
}): RemoteAction<z.infer<I>, z.infer<O>, z.infer<S>> {
  const action = (
    input?: z.infer<I>,
    runOptions?: RunOptions
  ): Promise<z.infer<O>> => {
    return runFlow({
      url: actionOptions.url,
      headers: runOptions?.headers ?? actionOptions.headers,
      input,
    });
  };
  (action as RemoteAction<z.infer<I>, z.infer<O>, z.infer<S>>).stream = (
    input?: I,
    runOptions?: RunOptions
  ): StreamingResponse<z.infer<O>, z.infer<S>> => {
    return streamFlow({
      url: actionOptions.url,
      headers: runOptions?.headers ?? actionOptions.headers,
      input,
    });
  };

  return action as RemoteAction<z.infer<I>, z.infer<O>, z.infer<S>>;
}

const __flowStreamDelimiter = '\n\n';

/**
 * Invoke and stream response from a deployed flow.
 *
 * For example:
 *
 * ```js
 * import { streamFlow } from 'genkit/beta/client';
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
export function streamFlow<O = any, S = any>({
  url,
  input,
  headers,
}: {
  url: string;
  input?: any;
  headers?: Record<string, string>;
}): {
  readonly output: Promise<O>;
  readonly stream: AsyncIterable<S>;
} {
  const channel = new Channel<S>();

  const operationPromise = __flowRunEnvelope({
    url,
    input,
    sendChunk: (c) => channel.send(c),
    headers,
  });
  operationPromise.then(
    () => channel.close(),
    (err) => channel.error(err)
  );

  return {
    output: operationPromise,
    stream: channel,
  };
}

async function __flowRunEnvelope({
  url,
  input,
  sendChunk,
  headers,
}: {
  url: string;
  input: any;
  sendChunk: (chunk: any) => void;
  headers?: Record<string, string>;
}) {
  const response = await fetch(url, {
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
  if (response.status !== 200) {
    throw new Error(
      `Server returned: ${response.status}: ${await response.text()}`
    );
  }
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
        sendChunk(chunk.message);
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
export async function runFlow<O = any>({
  url,
  input,
  headers,
}: {
  url: string;
  input?: any;
  headers?: Record<string, string>;
}): Promise<O> {
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
  if (response.status !== 200) {
    throw new Error(
      `Server returned: ${response.status}: ${await response.text()}`
    );
  }
  const wrappedResult = (await response.json()) as
    | { result: O }
    | { error: unknown };
  if ('error' in wrappedResult) {
    if (typeof wrappedResult.error === 'string') {
      throw new Error(wrappedResult.error);
    }
    // TODO: The callable protocol defines an HttpError that has a JSON format of
    // details?: string
    // httpErrorCode: { canonicalName: string }
    // message: string
    // Should we create a new error class that parses this and exposes it as fields?
    throw new Error(JSON.stringify(wrappedResult.error));
  }
  return wrappedResult.result;
}
