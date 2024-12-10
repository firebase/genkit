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
import * as yaml from 'yaml';
import {
  retriable,
  runTestsForApp,
} from './utils.js';

(async () => {
  // TODO: Add NodeJS tests
  // Run the tests for go test app
  await runTestsForApp('../go/tests/test_app', 'go run main.go', async () => {
    await testFlowServer();
  });
})();


async function testFlowServer() {
  const url = 'http://localhost:3400';
  await retriable(
    async () => {
      const res = await fetch(`${url}/streamy`,
        {
          method: 'POST',
          body: JSON.stringify({
            data: 1
          },),
        });
      if (res.status != 200) {
        throw new Error(`timed out waiting for flow server to become healthy`)
      }
    },
    {
      maxRetries: 30,
      delayMs: 1000,
    }
  );


  const t = yaml.parse(readFileSync('flow_server_tests.yaml', 'utf8'));
  for (const test of t.tests) {
    console.log('path', test.path)
    let fetchopts = {
      method: 'POST',
    } as RequestInit;
    if (test.hasOwnProperty('post')) {
      fetchopts.method = 'POST';
      fetchopts.headers = { 'Content-Type': 'text/event-stream', 'Connection': 'keep-alive' }
      fetchopts.body = JSON.stringify(test.post)
    }

    await fetchData(`${url}${test.path}`, fetchopts)
  }
  console.log('Flow server tests done! \\o/')
}

// helper function that validates stream flow responses
async function fetchData(url: string, fetchopts: RequestInit) {
  const response = await fetch(`${url}`, fetchopts);

  if (!response.ok) {
    throw new Error(`${url}: error detected, code: ${response.status}`)
  }
  const contentHeader = response.headers.get('Content-Type')
  if (contentHeader && !contentHeader.includes("text/plain")) {
    throw new Error(`wrong header, got: ${contentHeader}`)
  }
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error(`unable to get response reader`);
  }

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      console.log("connection closed")
      break;
    }

    const decoder = new TextDecoder('utf-8');
    const text = decoder.decode(value);
    console.log('data:', text)
  }
}
