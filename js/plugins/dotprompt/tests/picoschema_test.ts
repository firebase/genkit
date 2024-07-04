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

import { readFileSync } from 'fs';
import assert from 'node:assert';
import { describe, it } from 'node:test';
import { parse } from 'yaml';
import { picoschema } from '../src/picoschema';

describe('picoschema()', () => {
  const tests = parse(readFileSync('tests/picoschema_tests.yaml', 'utf8'));
  for (const test of tests) {
    it(test.description, () => {
      const got = picoschema(parse(test.yaml).schema);
      assert.deepEqual(got, test.want);
    });
  }
});
