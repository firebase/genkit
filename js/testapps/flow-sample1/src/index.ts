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

import { genkit, run, z } from 'genkit';

const ai = genkit({});

ai.startFlowServer(); // Start the server early
console.log('Flow server initialized.');

/**
 * @flow Basic
 * @description A simple flow that processes a string input.
 * @param {string} subject - The subject string to process.
 * @returns {Promise<string>} - A processed string output.
 *
 * @example
 * Input: "hello"
 * Output: "foo: subject: hello"
 */
export const basic = ai.defineFlow({ name: 'basic' }, async (subject) => {
  const foo = await run('call-llm', async () => `subject: ${subject}`);
  return await run('call-llm1', async () => `foo: ${foo}`);
});

console.log('Basic flow registered.');

/**
 * @flow Parent
 * @description Runs the basic flow and returns its output as a JSON string.
 * @returns {Promise<string>} - JSON string of the basic flow's result.
 *
 * @example
 * Input: (none)
 * Output: '{"foo":"subject: foo"}'
 */
export const parent = ai.defineFlow(
  { name: 'parent', outputSchema: z.string() },
  async () => {
    return JSON.stringify(await basic('foo'));
  }
);

/**
 * @flow Streamy
 * @description Streams numbers up to a given count.
 * @param {number} count - The number of iterations to stream.
 * @param {function} streamingCallback - Callback function to handle each streamed value.
 * @returns {Promise<string>} - A summary string after streaming.
 *
 * @example
 * Input: 3
 * Stream: {count: 0}, {count: 1}, {count: 2}
 * Output: "done: 3, streamed: 3 times"
 */
export const streamy = ai.defineStreamingFlow(
  {
    name: 'streamy',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: z.object({ count: z.number() }),
  },
  async (count, streamingCallback) => {
    for (let i = 0; i < count; i++) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      streamingCallback?.({ count: i });
    }
    return `done: ${count}, streamed: ${count} times`;
  }
);

/**
 * @flow StreamyThrowy
 * @description Streams numbers and throws an error at iteration 3.
 * @param {number} count - The number of iterations to stream.
 * @param {function} streamingCallback - Callback function to handle each streamed value.
 * @returns {Promise<string>} - A summary string after streaming.
 *
 * @example
 * Input: 5
 * Stream: {count: 0}, {count: 1}, {count: 2}, Error: "whoops"
 */
export const streamyThrowy = ai.defineStreamingFlow(
  {
    name: 'streamyThrowy',
    inputSchema: z.number(),
    outputSchema: z.string(),
    streamSchema: z.object({ count: z.number() }),
  },
  async (count, streamingCallback) => {
    for (let i = 0; i < count; i++) {
      if (i === 3) throw new Error('whoops');
      await new Promise((resolve) => setTimeout(resolve, 1000));
      streamingCallback?.({ count: i });
    }
    return `done: ${count}, streamed: ${count} times`;
  }
);

/**
 * @flow Throwy
 * @description Demonstrates error handling by throwing an error based on input.
 * @param {string} subject - The subject to process.
 * @returns {Promise<string>} - Processed output unless an error is thrown.
 *
 * @example
 * Input: "error"
 * Output: Error: "error"
 */
export const throwy = ai.defineFlow(
  { name: 'throwy', inputSchema: z.string(), outputSchema: z.string() },
  async (subject) => {
    const foo = await run('call-llm', async () => `subject: ${subject}`);
    if (subject) throw new Error(subject);
    return foo;
  }
);

/**
 * @flow MultiSteps
 * @description Demonstrates a flow with multiple steps.
 * @param {string} input - Input string for processing.
 * @returns {Promise<number>} - Always returns 42 after multiple processing steps.
 *
 * @example
 * Input: "world"
 * Output: Logs intermediate steps, final return value 42.
 */
export const multiSteps = ai.defineFlow(
  { name: 'multiSteps', inputSchema: z.string(), outputSchema: z.number() },
  async (input) => {
    const out1 = await run('step1', async () => `Hello, ${input}!`);
    const out2 = await run('step2', async () => `${out1} Step 2`);
    const out3 = await run('step3-array', async () => [out2, out2]);
    const out4 = await run('step4-num', async () => out3.join('-'));
    console.log(out4);
    return 42;
  }
);

/**
 * Utility function to generate a long string.
 * @param {number} length - Length of the string to generate.
 * @returns {string} - Generated string.
 */
function generateString(length: number) {
  const loremIpsum = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur'];
  let str = '';
  while (str.length < length) {
    str += loremIpsum[Math.floor(Math.random() * loremIpsum.length)] + ' ';
  }
  return str.substring(0, length);
}

console.log('Flow server state:', ai);
