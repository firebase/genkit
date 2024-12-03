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
import axios from 'axios';
import { readFileSync } from 'fs';

describe('Firebase Functions', () => {
  const functionUri = 'http://127.0.0.1:5001/demo-test/us-central1/simpleFlow';

  function delay(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function expectMessage(message: string) {
    await delay(1000);

    // Wait for emulator logs to contain the user feedback message. We do this
    // by explicitly setting the Genkit env to "dev" (by using .env.local
    // config), which forces logs to be written to console, and by redirecting
    // emulator output to a tmp file (see package.json).
    let tries = 20;
    let foundLog = false;
    while (tries > 0) {
      const testLogs = readFileSync('/tmp/firebase_integration_test', 'utf8');
      if (testLogs.indexOf(message) > 0) {
        foundLog = true;
        break;
      } else {
        console.log('.');
      }
      await delay(1000); // wait 1s
      tries--;
    }

    if (!foundLog) {
      console.error(`Failed to find message after 20s: ${message}`);
    }

    return expect(foundLog).toBeTruthy();
  }

  it('logs trace output', async () => {
    const res = await axios.post(functionUri, '');
    expect(res.data.result).toEqual('hello world!');
    await expectMessage('[info] Output[simpleFlow, simpleFlow]');
  }, 25000 /* 25s timeout */);
});
