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

import { Genkit } from '../src/genkit';

export function defineEchoModel(ai: Genkit) {
  ai.defineModel(
    {
      name: 'echoModel',
    },
    async (request, streamingCallback) => {
      if (streamingCallback) {
        await runAsync(() => {
          streamingCallback({
            content: [
              {
                text: '3',
              },
            ],
          });
        });
        await runAsync(() => {
          streamingCallback({
            content: [
              {
                text: '2',
              },
            ],
          });
        });
        await runAsync(() => {
          streamingCallback({
            content: [
              {
                text: '1',
              },
            ],
          });
        });
      }
      return await runAsync(() => ({
        message: {
          role: 'model',
          content: [
            {
              text:
                'Echo: ' +
                request.messages
                  .map((m) => m.content.map((c) => c.text).join())
                  .join(),
            },
            {
              text: '; config: ' + JSON.stringify(request.config),
            },
          ],
        },
        finishReason: 'stop',
      }));
    }
  );
}

async function runAsync<O>(fn: () => O): Promise<O> {
  return Promise.resolve(fn());
}
