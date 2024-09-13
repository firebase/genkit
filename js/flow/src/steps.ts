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

import { runInNewSpan } from '@genkit-ai/core/tracing';

export function run<T>(name: string, func: () => Promise<T>): Promise<T>;
export function run<T>(
  name: string,
  input: any,
  func: (input?: any) => Promise<T>
): Promise<T>;

/**
 * A flow step that executes the provided function. Each run step is recorded separately in the trace.
 */
export function run<T>(
  name: string,
  funcOrInput: () => Promise<T>,
  fn?: (input?: any) => Promise<T>
): Promise<T> {
  const func = arguments.length === 3 ? fn : funcOrInput;
  const input = arguments.length === 3 ? funcOrInput : undefined;
  if (!func) {
    throw new Error('unable to resolve run function');
  }
  return runInNewSpan({ metadata: { name } }, async (meta) => {
    meta.input = input;
    const output = arguments.length === 3 ? await func(input) : await func();
    meta.output = JSON.stringify(output);
    return output;
  });
}
