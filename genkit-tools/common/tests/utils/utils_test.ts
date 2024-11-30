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

import { describe, expect, it } from '@jest/globals';
import { projectNameFromGenkitFilePath } from '../../src/utils';

describe('utils', () => {
  describe('projectNameFromGenkitFilePath', () => {
    it('returns unknown for empty string', () => {
      expect(projectNameFromGenkitFilePath('')).toEqual('unknown');
    });

    it('returns unknown for an invalid path', () => {
      expect(projectNameFromGenkitFilePath('/path/to/nowhere')).toEqual(
        'unknown'
      );
    });

    it('returns project name from a typical runtime file path', () => {
      expect(
        projectNameFromGenkitFilePath(
          '/path/to/test-project/.genkit/runtimes/123.json'
        )
      ).toEqual('test-project');
    });

    it('returns project name from any path that contains a .genkit dir', () => {
      expect(
        projectNameFromGenkitFilePath(
          '/path/to/test-project/.genkit/unexpected/but/valid/location'
        )
      ).toEqual('test-project');
    });
  });
});
