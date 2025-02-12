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

import { z, type Action, type ActionContext } from 'genkit';
import {
  RequestData,
  getCallableJSON,
  getHttpStatus,
  type ContextProvider,
} from 'genkit/context';
import { NextRequest, NextResponse } from 'next/server.js';
export { NextRequest, NextResponse, z, type Action, type ActionContext };

const delimiter = '\n\n';
async function getContext<C extends ActionContext, T>(
  request: NextRequest,
  input: T,
  provider: ContextProvider<C, T> | undefined
): Promise<C> {
  // Type cast is necessary because there is no runtime way to generate a context if C is provided to appRoute
  // but contextProvider is missing. When I'm less sleepy/busy I'll see if I can make this a type error.
  let context = {} as C;
  if (!provider) {
    return context;
  }

  const r: RequestData = {
    method: request.method as RequestData['method'],
    headers: {},
    input,
  };
  request.headers.forEach((val, key) => {
    r.headers[key.toLowerCase()] = val;
  });
  return await provider(r);
}

function appRoute<
  C extends ActionContext = ActionContext,
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  S extends z.ZodTypeAny = z.ZodTypeAny,
>(
  action: Action<I, O, S>,
  opts?: {
    contextProvider?: ContextProvider<C, I>;
  }
) {
  return async (req: NextRequest): Promise<NextResponse> => {
    let context: C = {} as C;
    const { data: input } = await req.json();
    if (req.headers.get('accept') !== 'text/event-stream') {
      try {
        context = await getContext(req, input, opts?.contextProvider);
      } catch (e) {
        console.error('Error gathering context for running action:', e);
        return NextResponse.json(
          { error: getCallableJSON(e) },
          { status: getHttpStatus(e) }
        );
      }
      try {
        const resp = await action.run(input, { context });
        return NextResponse.json({ result: resp.result });
      } catch (e) {
        // For security reasons, log the error rather than responding with it.
        console.error('Error calling action:', e);
        return NextResponse.json(
          { error: getCallableJSON(e) },
          { status: getHttpStatus(e) }
        );
      }
    }

    try {
      context = await getContext(req, input, opts?.contextProvider);
    } catch (e) {
      console.error('Error gathering context for streaming action:', e);
      return new NextResponse(
        `error: ${JSON.stringify(getCallableJSON(e))}${delimiter}END`,
        { status: getHttpStatus(e) }
      );
    }
    const { output, stream } = action.stream(input, { context });
    const encoder = new TextEncoder();
    const { readable, writable } = new TransformStream();

    // Not using a dangling promise causes this closure to block on the stream being drained,
    // which doesn't happen until the NextResponse is consumed later in the cosure.
    // TODO: Add ping comments at regular intervals between streaming responses to mitigate
    // timeouts.
    (async (): Promise<void> => {
      const writer = writable.getWriter();
      try {
        for await (const chunk of stream) {
          await writer.write(
            encoder.encode(
              `data: ${JSON.stringify({ message: chunk })}${delimiter}`
            )
          );
        }
        await writer.write(
          encoder.encode(
            `data: ${JSON.stringify({ result: await output })}${delimiter}`
          )
        );
        await writer.write(encoder.encode('END'));
      } catch (err) {
        console.error('Error streaming action:', err);
        await writer.write(
          encoder.encode(
            `error: ${JSON.stringify(getCallableJSON(err))}` + '\n\n'
          )
        );
        await writer.write(encoder.encode('END'));
      } finally {
        await writer.close();
      }
    })();

    return new NextResponse(readable, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'Transfer-Encoding': 'chunked',
      },
    });
  };
}

export default appRoute;
export { appRoute };
