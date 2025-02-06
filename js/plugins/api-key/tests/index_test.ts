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

import { RequestData } from '@genkit-ai/core';
import { describe, expect, it } from '@jest/globals';
import { ApiKeyContext, apiKey } from '../src';

function request(key?: string): RequestData {
  let headers: Record<string, string> = {};

  if (key) {
    headers = { authorization: key };
  }
  return {
    method: 'POST',
    headers,
    input: undefined,
  };
}

describe('apiKey', () => {
  it('can merely save api keys', async () => {
    expect(await apiKey()(request())).toEqual({});
    expect(await apiKey()(request('key'))).toEqual({
      auth: {
        apiKey: 'key',
      },
    });
  });

  it('can expect specific keys', async () => {
    expect(await apiKey('key')(request('key'))).toEqual({
      auth: {
        apiKey: 'key',
      },
    });
    expect(() => apiKey('key')(request('wrong-key'))).rejects.toThrow();
    expect(() => apiKey('key')(request())).rejects.toThrow();
  });

  it('can use a policy function', async () => {
    await apiKey((context: ApiKeyContext) => {
      expect(context).toEqual({
        auth: {
          apiKey: 'key',
        },
      });
    })(request('key'));
    await apiKey((context: ApiKeyContext) => {
      expect(context).toEqual({});
    })(request());
  });
});
