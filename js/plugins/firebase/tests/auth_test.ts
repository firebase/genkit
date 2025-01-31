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
import {
  fakeToken,
  firebaseAuth,
  setDebugSkipTokenVerification,
} from '../src/auth.js';

describe('firebaseAuth', () => {
  setDebugSkipTokenVerification(true);

  describe('no policy', () => {
    it('handles noop', async () => {
      const context = await firebaseAuth()({ headers: {}, method: 'POST' });
      expect(context).toEqual({});
    });
    it('handles all headers', async () => {
      const context = await firebaseAuth()({
        method: 'POST',
        headers: {
          Authorization: `bearer ${fakeToken({ sub: 'user' })}`,
          'X-Firebase-AppCheck': fakeToken({ sub: 'appId' }),
          'Firebase-Instance-ID-Token': 'token',
        },
      });
      expect(context).toEqual({});
    });
  });
});
