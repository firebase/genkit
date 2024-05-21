const __flowStreamDelimiter = '\n';

export function streamFlow({
  url,
  payload,
  headers,
}: {
  url: string;
  payload: any;
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
          throw new Error(op.name, op.result?.error + op.result?.stacktrace);
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
  payload: any;
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
