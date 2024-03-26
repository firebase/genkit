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

import { execSync, spawn } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';
import puppeteer, { Page } from 'puppeteer';
import { PuppeteerScreenRecorder } from 'puppeteer-screen-recorder';
import terminate from 'terminate';

export async function runDevUiTest(
  testAppName: string,
  testFn: (page: Page, devUiUrl: string) => Promise<void>
) {
  const url = await startDevUi(testAppName);
  try {
    const browser = await puppeteer.launch({
      slowMo: 50,
    });
    const page = await browser.newPage();
    const recorder = new PuppeteerScreenRecorder(page);
    const savePath = './last_recording.mp4';
    await recorder.start(savePath);

    try {
      await testFn(page, url);
      console.log('Test passed');
    } finally {
      await recorder.stop();
    }
  } finally {
    terminate(process.pid);
  }
}

export async function startDevUi(testAppName: string): Promise<string> {
  const testRoot = path.resolve(os.tmpdir(), `./e2e-run-${Date.now()}`);
  console.log(`testRoot=${testRoot} pwd=${process.cwd()}`);
  fs.mkdirSync(testRoot, { recursive: true });
  fs.cpSync(testAppName, testRoot, { recursive: true });
  const distDir = path.resolve(process.cwd(), '../dist');
  execSync(`npm i --save ${distDir}/*.tgz`, {
    stdio: 'inherit',
    cwd: testRoot,
  });
  execSync(`npm run build`, { stdio: 'inherit', cwd: testRoot });
  return new Promise((urlResolver) => {
    const appProcess = spawn('npx', ['genkit', 'start'], {
      cwd: testRoot,
    });

    appProcess.stdout?.on('data', (data) => {
      console.log('stdout: ' + data.toString());
      const match = data.toString().match(/Genkit Tools UI: ([^ ]*)/);
      if (match && match.length > 1) {
        console.log('Dev UI ready, launching test ' + match[1]);

        urlResolver(match[1]);
      }
    });
    appProcess.stderr?.on('data', (data) => {
      console.log(data.toString());
    });
    appProcess.on('error', (error): void => {
      console.log(`Error in app process: ${error}`);
      process.exitCode = 22;
      terminate(process.pid);
    });
    appProcess.on('exit', (code) => {
      console.log(`Dev UI exited with code ${code}`);
      process.exitCode = 23;
      terminate(process.pid);
    });
  });
}
