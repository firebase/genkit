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

import { extractJson } from '../extract';
import type { Formatter } from './types';

export const jsonFormatter: Formatter<unknown, unknown> = {
  name: 'json',
  config: {
    contentType: 'application/json',
    constrained: true,
  },
  handler: (request) => {
    let instructions: string | undefined;

    if (request.output?.schema) {
      instructions = `Output should be in JSON format and conform to the following schema:

\`\`\`
${JSON.stringify(request.output!.schema!)}
\`\`\`
`;
    }

    return {
      parseChunk: (chunk) => {
        return extractJson(chunk.accumulatedText);
      },

      parseResponse: (response) => {
        return extractJson(response.text);
      },

      instructions,
    };
  },
};
