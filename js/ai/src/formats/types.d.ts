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

import { GenerateResponse, GenerateResponseChunk } from '../generate';
import { GenerateRequest, Part } from '../model';

export interface ParsedChunk<CO = unknown, CC = unknown> {
  output: CO;
  /**
   * The cursor of a parsed chunk response holds context that is relevant to continue parsing.
   * The returned cursor will be passed into the next iteration of the chunk parser. Cursors
   * are not exposed to external consumers of the formatter.
   */
  cursor?: CC;
}

type OutputContentTypes =
  | 'application/json'
  | 'text/plain'
  | 'application/jsonl';

export interface Formatter<O = unknown, CO = unknown, CC = unknown> {
  (req: GenerateRequest): {
    parseResponse(response: GenerateResponse): O;
    parseChunk?: (
      chunk: GenerateResponseChunk,
      cursor?: CC
    ) => ParsedChunk<CO, CC>;
    instructions?: string | Part[];
    contentType?: OutputContentTypes | Omit<string, OutputContentTypes>;
  };
}
