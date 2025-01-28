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

import type { Action } from '@genkit-ai/core';
import { NextRequest, NextResponse } from 'next/server';

const appRoute =
  <A extends Action>(action: A) =>
  async (req: NextRequest): Promise<NextResponse> => {
    const { data } = await req.json();
    if (req.headers.get('accept') !== 'text/event-stream') {
      try {
        const resp = await action.run(data);
        return NextResponse.json({ result: resp.result });
      } catch (e) {
        // For security reasons, log the error rather than responding with it.
        console.error(e);
        return NextResponse.json({ error: 'INTERNAL' }, { status: 500 });
      }
    }

    const { output, stream } = action.stream(data);
    const encoder = new TextEncoder();
    const { readable, writable } = new TransformStream();

    // Not using a dangling Promise causes NextResponse to deadlock.
    // TODO: Add ping comments at regular intervals between streaming responses to mitigate
    // timeouts.
    (async (): Promise<void> => {
      const writer = writable.getWriter();
      try {
        for await (const chunk of stream) {
          console.debug('Writing chunk ' + chunk + '\n');
          await writer.write(
            encoder.encode(
              'data: ' + JSON.stringify({ message: chunk }) + '\n\n'
            )
          );
        }
        await writer.write(
          encoder.encode(
            'data: ' + JSON.stringify({ result: await output }) + '\n\n'
          )
        );
        await writer.write('END');
      } catch (err) {
        console.error('Error in streaming output:', err);
        await writer.write(
          encoder.encode(`error: {"error": {"message":"INTERNAL"}}` + '\n\n')
        );
        await writer.write(encoder.encode('END'));
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

export default appRoute;
