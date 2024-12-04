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
  runTestsForApp,
  retriable
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

  const t = yaml.parse(readFileSync('flow_server_tests.yaml', 'utf8'));
  for (const test of t.tests) {
    console.log('path', test.path)
    let fetchopts = {
      method: 'GET',
    } as RequestInit;
    if (test.hasOwnProperty('post')) {
      fetchopts.method = 'POST';
      fetchopts.headers = { 'Content-Type': 'text/event-stream' }
      fetchopts.headers = { 'Access-Control-Allow-Origin': '*' }
      fetchopts.body = JSON.stringify(test.post)
    }
    const res = await fetch(url + test.path)
    if (res.status != 200) {
      throw new Error(`${test.path}: got status ${res.status}`);
    }

  }
  console.log('Flow server tests done! \\o/')
}
