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

import assert from 'node:assert';
import { describe, it } from 'node:test';
import { firebaseAuth } from '../src/auth';

describe('firebaseAuth', () => {
  it('config unset throws', async () => {
    const auth = firebaseAuth((user, input) => {});

    await assert.rejects(async () => {
      await auth.policy(undefined, undefined);
    }, new Error('Auth is required'));
  });

  it('not required ok', async () => {
    const auth = firebaseAuth((user, input) => {}, { required: false });

    await assert.doesNotReject(async () => {
      await auth.policy(undefined, undefined);
    });
  });

  it('required throws', async () => {
    const auth = firebaseAuth((user, input) => {}, { required: true });

    await assert.rejects(async () => {
      await auth.policy(undefined, undefined);
    }, new Error('Auth is required'));
  });

  it('config unset present ok', async () => {
    const auth = firebaseAuth((user, input) => {});

    await assert.doesNotReject(async () => {
      await auth.policy({}, undefined);
    });
  });

  it('required present ok', async () => {
    const auth = firebaseAuth((user, input) => {}, { required: true });

    await assert.doesNotReject(async () => {
      await auth.policy({}, undefined);
    });
  });
});
