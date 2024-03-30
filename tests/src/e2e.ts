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

import { runDevUiTest } from './utils.js';

runDevUiTest('test_js_app', async (page, url) => {
  await page.goto(url);
  await page.setViewport({ width: 1080, height: 1024 });

  const basicFlowElemement = await page.waitForSelector('text/testFlow');
  basicFlowElemement?.click();

  const editor = await page.waitForSelector('#input-editor .monaco-editor');
  editor?.click();
  // it takes a sec for monaco to "focus"
  await new Promise((r) => setTimeout(r, 1000));

  await editor!.type('"hello world"');

  const runFlowButton = await page.waitForSelector('text/Run Flow');
  runFlowButton?.click();

  await page.waitForSelector('text/Test flow passed');

  const inspectFlowButton = await page.waitForSelector(
    'text/Inspect flow state'
  );
  inspectFlowButton?.click();

  await page.waitForSelector('text/testFlow');
});
