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
import { compare, runDevUiTest } from './utils.js';

runDevUiTest('test_js_app', async (page, url) => {
  await page.goto(url);
  await page.setViewport({ width: 1080, height: 1024 });

  const basicFlowElemement = await page.waitForSelector('text/testFlow');
  basicFlowElemement?.click();

  const editor = await page.waitForSelector('#input-editor .monaco-editor');
  editor?.click();
  // it takes a sec for monaco to "focus"
  await new Promise((r) => setTimeout(r, 1000));

  await editor!.press('Backspace');
  await editor!.press('Backspace');
  await editor!.type('"hello world"');

  const runFlowButton = await page.waitForSelector('button ::-p-text(Run)');
  runFlowButton?.click();

  await page.waitForSelector('text/Test flow passed');

  const inspectFlowButton = await page.waitForSelector('text/View trace');
  inspectFlowButton?.click();

  await page.waitForSelector('text/testFlow');

  await testReflectionApi();
});

async function testReflectionApi() {
  const url = 'http://localhost:3100';
  const t = yaml.parse(readFileSync('test_js_app.yaml', 'utf8'));
  for (const test of t.tests) {
    console.log('path', test.path);
    let fetchopts = {
      method: 'GET',
    };
    if (test.hasOwnProperty('post')) {
      fetchopts.method = 'POST';
      fetchopts.headers = { 'Content-Type': 'application/json' };
      fetchopts.body = JSON.stringify(test.post);
    }
    const res = await fetch(url + test.path, fetchopts);
    if (res.status != 200) {
      throw new Error(`${test.path}: got status ${res.status}`);
    }
    const gotBody = await res.json();
    const msgs = compare(gotBody, test.body);
    if (msgs.length > 0) {
      console.log(`FAIL: ${test.path}: bodies do not match:`);
      for (const msg of msgs) {
        console.log(msg);
      }
      throw new Error(`${test.path}: see messages above`);
    }
  }
}
