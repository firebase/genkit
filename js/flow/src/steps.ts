import { Action } from '@google-genkit/common';
import * as z from 'zod';
import { getActiveContext } from './utils';

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
