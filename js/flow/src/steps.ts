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

import { Action } from '@genkit-ai/core';
import * as z from 'zod';
import { getActiveContext } from './utils.js';

/**
 * A flow steap that executes an action with provided input and memoizes the output.
 */
export function runAction<I extends z.ZodTypeAny, O extends z.ZodTypeAny>(
  action: Action<I, O>,
  input: z.infer<I>
): Promise<z.infer<O>> {
  return run(action.__action.name, input, () => action(input));
}

export function run<T>(name: string, func: () => Promise<T>): Promise<T>;
export function run<T>(
  name: string,
  input: any,
  func: () => Promise<T>
): Promise<T>;

/**
 * A flow steap that executes the provided function and memoizes the output.
 */
export function run<T>(
  name: string,
  funcOrInput: () => Promise<T>,
  fn?: () => Promise<T>
): Promise<T> {
  const func = arguments.length === 3 ? fn : funcOrInput;
  const input = arguments.length === 3 ? funcOrInput : undefined;
  if (!func) {
    throw new Error('unable to resolve run function');
  }
  const ctx = getActiveContext();
  if (!ctx) throw new Error('can only be run from a flow');
  return ctx.run({ name }, input, func);
}

/**
 * A helper that takes an array of inputs and maps each input to a run step.
 */
export function runMap<I, O>(
  stepName: string,
  input: I[],
  fn: (i: I) => Promise<O>
): Promise<O[]> {
  return Promise.all(input.map((f) => run(stepName, () => fn(f))));
}
