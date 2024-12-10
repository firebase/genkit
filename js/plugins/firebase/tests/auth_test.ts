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
import { firebaseAuth } from '../lib/auth.js';

describe('firebaseAuth', () => {
  it('config unset throws', async () => {
    const auth = firebaseAuth((user, input) => {});

    expect(auth.policy(undefined, undefined)).rejects.toThrow(
      'Auth is required'
    );
  });

  it('not required ok', async () => {
    const auth = firebaseAuth((user, input) => {}, { required: false });

    expect(auth.policy(undefined, undefined)).resolves.not.toThrow();
  });

  it('required throws', async () => {
    const auth = firebaseAuth((user, input) => {}, { required: true });

    expect(auth.policy(undefined, undefined)).rejects.toThrow(
      'Auth is required'
    );
  });

  it('config unset present ok', async () => {
    const auth = firebaseAuth((user, input) => {});

    expect(auth.policy({}, undefined)).resolves.not.toThrow();
  });

  it('required present ok', async () => {
    const auth = firebaseAuth((user, input) => {}, { required: true });

    expect(auth.policy({}, undefined)).resolves.not.toThrow();
  });
});
