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

import * as assert from 'assert';
import { describe, it } from 'node:test';
import { LazyPromise } from '../src/async';

describe('LazyPromise', () => {
  it('call its function lazily', async () => {
    let called = false;
    const lazy = new LazyPromise((resolver) => {
      called = true;
      resolver('foo');
    });

    assert.ok(!called);

    const result = await lazy;

    assert.ok(called);
    assert.equal(result, 'foo');
  });
});
